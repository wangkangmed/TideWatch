"""Build search queries from monitor/topic templates."""

from __future__ import annotations

import hashlib

from tide_watch.sources.search.models import SearchMonitorConfig, SearchQuery
from tide_watch.sources.search.query.expansion import expand_queries
from tide_watch.sources.search.query.templates import apply_template


def build_queries_for_monitor(monitor: SearchMonitorConfig, *, expand: bool = False) -> list[SearchQuery]:
    out: list[SearchQuery] = []
    templates = monitor.query_templates or ["brand_updates"]
    for tpl in templates:
        for text, intent in apply_template(tpl, monitor):
            if not text.strip():
                continue
            digest = hashlib.sha256(f"{monitor.monitor_id}|{intent}|{text}".encode("utf-8")).hexdigest()[:16]
            out.append(
                SearchQuery(
                    query_id=f"{monitor.monitor_id}:{digest}",
                    monitor_id=monitor.monitor_id,
                    topic_id=monitor.topic,
                    text=text.strip(),
                    language=monitor.language,
                    region=monitor.region,
                    time_window=monitor.time_window,
                    intent=intent,
                    priority=monitor.priority,
                    metadata={"monitor_topic": monitor.topic, "template": tpl},
                )
            )
    return expand_queries(out, enabled=expand)
