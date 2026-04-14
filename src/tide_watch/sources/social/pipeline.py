"""Social：discovery -> enrichment -> RawFetchBatch；平台细节在 connector。"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.config_loader import load_social_registry
from tide_watch.sources.social.health import record_attempt
from tide_watch.sources.social.models import SocialCheckpoint, SocialCandidateItem, SocialSourceHealth
from tide_watch.sources.social.normalizers import metadata_fallback_batch
from tide_watch.sources.social.registry import get_connector_for_source

logger = logging.getLogger(__name__)


def _get_checkpoint(scope: dict[str, Any], source_id: str) -> SocialCheckpoint | None:
    raw = (scope.get("social_checkpoints") or {}).get(source_id)
    if isinstance(raw, dict):
        try:
            return SocialCheckpoint.from_blob(raw)
        except Exception:  # noqa: BLE001
            return None
    return None


def _set_checkpoint(scope: dict[str, Any], cp: SocialCheckpoint) -> None:
    scope.setdefault("social_checkpoints", {})
    if isinstance(scope["social_checkpoints"], dict):
        scope["social_checkpoints"][cp.source_id] = cp.to_blob()


def collect_social_batches(
    *,
    config_path: str | None = None,
    scope: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> tuple[list[RawFetchBatch], list[str], dict[str, Any]]:
    """
    对每个启用的 social source 跑 discover + enrich。

    返回 (batches, errors, health_by_source_id) — health 可写回 LangGraph state。

    注意：会在传入的 ``scope`` 上原地写入 ``social_checkpoints`` / ``social_health``；
    若需隔离副本，请调用方自行 ``dict(scope)`` 再传入。
    """
    if scope is None:
        scope = {}
    reg = load_social_registry(config_path)
    batches: list[RawFetchBatch] = []
    errors: list[str] = []
    health: dict[str, SocialSourceHealth] = dict(scope.get("social_health") or {})

    rid = run_id or uuid.uuid4().hex[:12]

    for src in sorted((s for s in reg.social_sources if s.enabled), key=lambda s: -s.priority):
        h = health.get(src.source_id) or SocialSourceHealth(source_id=src.source_id, platform=src.platform)
        connector = get_connector_for_source(src)
        cp = _get_checkpoint(scope, src.source_id)
        candidates: list[SocialCandidateItem] = []
        try:
            candidates, new_cp = connector.discover(src, cp)
            if new_cp:
                _set_checkpoint(scope, new_cp)
            if not candidates:
                if src.platform == "x":
                    pending = connector.enrich([], src, new_cp or cp)
                    errors.extend(pending.errors)
                else:
                    record_attempt(
                        h,
                        source_id=src.source_id,
                        platform=src.platform,
                        success=True,
                        error=None,
                    )
                health[src.source_id] = h
                continue

            record_attempt(h, source_id=src.source_id, platform=src.platform, success=True, error=None)
            batch = connector.enrich(candidates, src, new_cp or cp)
            if not batch.records and batch.errors and src.metadata_fallback:
                fb = metadata_fallback_batch(
                    candidates,
                    src,
                    batch_id=f"social-fallback-{src.source_id}-{rid}",
                )
                batches.append(fb)
                errors.extend(batch.errors)
                errors.extend(fb.errors)
            else:
                if batch.records or batch.errors:
                    batches.append(batch)
                errors.extend(batch.errors)
        except Exception as exc:  # noqa: BLE001
            err = f"{src.source_id}:{exc!s}"
            logger.warning("social_pipeline_failed %s", err)
            errors.append(err)
            record_attempt(h, source_id=src.source_id, platform=src.platform, success=False, error=str(exc))
            if src.metadata_fallback and candidates:
                batches.append(
                    metadata_fallback_batch(
                        candidates,
                        src,
                        batch_id=f"social-fallback-{src.source_id}-{rid}",
                    )
                )
        health[src.source_id] = h

    scope["social_health"] = health
    return batches, errors, health
