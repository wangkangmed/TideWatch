"""单独运行 social ingestion；可选打印每条拉取内容。"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tide_watch.sources.official.config_loader import default_sources_path
from tide_watch.sources.social.pipeline import collect_social_batches


def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    t = s.replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 3] + "..."


def _prepare_enabled_all_yaml(
    base: Path,
    *,
    max_items: int | None,
) -> Path:
    with base.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    for s in data.get("social_sources") or []:
        if not isinstance(s, dict):
            continue
        s["enabled"] = True
        if max_items is not None:
            s["max_items"] = min(int(s.get("max_items") or max_items), max_items)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_social_cli.yaml",
        delete=False,
        encoding="utf-8",
    )
    yaml.safe_dump(data, tmp, allow_unicode=True, sort_keys=False)
    tmp.close()
    return Path(tmp.name)


def _print_records(batches: list[Any], *, text_preview: int) -> None:
    print("\n--- 拉取到的内容（按 batch）---")
    for b in batches:
        print(f"\n[batch] {b.batch_id}  records={len(b.records)}  errors={b.errors or []}")
        for i, r in enumerate(b.records, 1):
            m = dict(r.metadata or {})
            print(f"  #{i} provider={r.source_ref.provider_id}  external_id={r.source_ref.external_id}")
            print(f"      title: {_truncate(str(m.get('title')), 100)}")
            print(f"      url:   {_truncate(str(m.get('url')), 90)}")
            print(
                f"      scores: engagement={m.get('engagement_score')}  quality={m.get('quality_score')}  "
                f"trust_tier={m.get('trust_tier')}  metadata_fallback={m.get('metadata_fallback')}"
            )
            print(f"      platform={m.get('platform')}  published_at={m.get('published_at')}")
            print(f"      text ({len(r.text or '')} chars): {_truncate(r.text, text_preview)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="只跑 TideWatch social 管线并展示拉取结果。")
    parser.add_argument("--config", default=None, help="含 social_sources 的 YAML（默认仓库 ai_sources.yaml）")
    parser.add_argument(
        "--enable-all",
        action="store_true",
        help="临时启用 YAML 中全部 social_sources（写临时文件，不改原文件）",
    )
    parser.add_argument("--max-items", type=int, default=None, help="与 --enable-all 联用：统一 cap 每条源 max_items")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="打印每条 RawRecord 的标题、URL、分数与正文预览",
    )
    parser.add_argument("--text-preview", type=int, default=320, help="verbose 时正文预览最大字符")
    args = parser.parse_args()

    if args.config:
        base = Path(args.config)
        if not base.is_absolute():
            base = (Path.cwd() / base).resolve()
    else:
        base = default_sources_path()

    cfg_path: str | None = str(base)
    tmp: Path | None = None
    if args.enable_all:
        tmp = _prepare_enabled_all_yaml(base, max_items=args.max_items)
        cfg_path = str(tmp)

    scope: dict = {}
    rid = f"cli-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    batches, errors, health = collect_social_batches(config_path=cfg_path, scope=scope, run_id=rid)
    n_recs = sum(len(b.records) for b in batches)

    print("=== Social 模块运行结果 ===")
    print(f"配置: {cfg_path}")
    print(f"batches={len(batches)}  records={n_recs}  collect级 errors={len(errors)}")
    if args.verbose or n_recs > 0:
        _print_records(batches, text_preview=args.text_preview)
    if errors:
        print("\n--- errors ---")
        for e in errors:
            print(f"  - {e}")
    if scope.get("social_checkpoints"):
        print("\n--- social_checkpoints ---")
        print(json.dumps(scope["social_checkpoints"], ensure_ascii=False, indent=2))
    print("\n--- health (JSON) ---")
    print(json.dumps({k: v.model_dump() for k, v in health.items()}, ensure_ascii=False, indent=2))

    if tmp:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
