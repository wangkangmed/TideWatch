#!/usr/bin/env python3
"""一次性打印 social 各阶段 I/O，便于核对是否符合预期。"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tide_watch.nodes.normalize import node_normalize_batch
from tide_watch.sources.social.config_loader import load_social_registry
from tide_watch.sources.social.pipeline import collect_social_batches
from tide_watch.sources.social.registry import get_connector_for_source

DEMO_YAML = """
social_sources:
  - source_id: demo_reddit
    platform: reddit
    source_type: subreddit_feed
    handle_or_community: python
    enabled: true
    priority: 100
    include_comments: false
    max_items: 2
    metadata_fallback: true
    trust_tier: 2

  - source_id: demo_hn
    platform: hackernews
    source_type: top_feed
    enabled: true
    priority: 90
    max_items: 2
    include_comments: false
    metadata_fallback: true
    trust_tier: 2

  - source_id: demo_x
    platform: x
    source_type: account_feed
    handle_or_community: OpenAI
    enabled: true
    priority: 50
    metadata_fallback: true
    trust_tier: 2
"""


def main() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(DEMO_YAML.strip() + "\n")
        p = Path(f.name)

    try:
        reg = load_social_registry(p)
        print("=== 1) 配置加载 load_social_registry ===")
        print(f"路径: {p}")
        for s in reg.social_sources:
            print(json.dumps(s.model_dump(), ensure_ascii=False, indent=2))
            print("---")

        scope: dict = {}
        print("\n=== 2) 分源 Discovery 输出 (SocialCandidateItem 摘要) ===")
        for s in reg.social_sources:
            if not s.enabled:
                continue
            conn = get_connector_for_source(s)
            cands, cp = conn.discover(s, None)
            print(f"\n[{s.source_id}] platform={s.platform} type={s.source_type}")
            print(f"  -> candidates 条数: {len(cands)}")
            print(f"  -> checkpoint 更新: {cp.model_dump() if cp else None}")
            for i, c in enumerate(cands[:5]):
                title_preview = (c.title or "")[:56]
                print(
                    f"  [{i}] external_id={c.external_id!r} "
                    f"author={c.author_handle!r} published_at={c.published_at}"
                )
                print(f"      title={title_preview!r} url={c.url[:72]}...")
                print(f"      engagement={c.engagement}")

        print("\n=== 3) collect_social_batches (discover + enrich -> RawFetchBatch) ===")
        batches, errors, health = collect_social_batches(config_path=str(p), scope=scope, run_id="io-demo")
        print(f"errors 列表: {errors}")
        print(f"health: {json.dumps({k: v.model_dump() for k, v in health.items()}, ensure_ascii=False, indent=2)}")
        print(f"scope['social_checkpoints']: {json.dumps(scope.get('social_checkpoints'), ensure_ascii=False, indent=2)}")
        print(f"批次数: {len(batches)}")
        for b in batches:
            print(f"\n  batch_id={b.batch_id}")
            print(f"  batch.errors: {b.errors}")
            print(f"  records: {len(b.records)}")
            for j, r in enumerate(b.records[:3]):
                meta = dict(r.metadata or {})
                slim = {
                    k: meta.get(k)
                    for k in (
                        "title",
                        "url",
                        "published_at",
                        "platform",
                        "engagement_score",
                        "quality_score",
                        "trust_tier",
                        "metadata_fallback",
                    )
                }
                print(f"    [{j}] source_ref={r.source_ref.model_dump()}")
                print(f"        idempotency_key={r.idempotency_key!r}")
                print(f"        text 长度={len(r.text or '')} fetched_at={r.fetched_at}")
                print(f"        metadata(核心字段)={json.dumps(slim, ensure_ascii=False)[:500]}")

        print("\n=== 4) node_normalize_batch (RawFetchBatch -> NormalizedDocument) ===")
        state = {"raw_batches": batches}
        out = node_normalize_batch(state)
        docs = out.get("normalized_docs") or []
        print(f"文档数: {len(docs)}")
        for d in docs[:5]:
            sf = d.structured_fields or {}
            print(
                f"  doc_id={d.doc_id} language={d.language} published_at={d.published_at} "
                f"canonical_url={d.canonical_url!r}"
            )
            print(f"    title={d.title!r} body_len={len(d.body_text or '')}")
            print(f"    structured_fields 含 engagement_score={sf.get('engagement_score')} quality_score={sf.get('quality_score')}")

        print("\n=== 5) 仓库默认 ai_sources.yaml（social 全 false 时 CLI 行为）===")
        repo_cfg = Path(__file__).resolve().parents[1] / "configs" / "sources" / "ai_sources.yaml"
        reg2 = load_social_registry(repo_cfg)
        enabled2 = [x.source_id for x in reg2.social_sources if x.enabled]
        print(f"默认配置中 enabled 的 social 源: {enabled2 or '(无) — CLI 将不产生 RawRecord'}")
    finally:
        p.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
