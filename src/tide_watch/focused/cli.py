"""CLI entry for focused ingestion subgraph."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from tide_watch.focused.graph import build_ingestion_subgraph


def main() -> None:
    parser = argparse.ArgumentParser(description="Run focused content ingestion subgraph.")
    parser.add_argument("--config", default=None, help="Path to source YAML config")
    parser.add_argument("--max-candidates", type=int, default=80)
    parser.add_argument("--listing-max-child-links", type=int, default=12)
    args = parser.parse_args()

    app = build_ingestion_subgraph().compile()
    out = app.invoke(
        {
            "run_id": f"focused-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "source_config_path": args.config,
            "max_candidates": args.max_candidates,
            "listing_max_child_links": args.listing_max_child_links,
            "source_health": {},
        }
    )
    print(
        json.dumps(
            {
                "persisted_docs": len(out.get("persisted_docs") or []),
                "fetch_results": len(out.get("fetch_results") or []),
                "errors": out.get("errors") or [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
