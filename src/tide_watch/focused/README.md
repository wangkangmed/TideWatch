# Focused Content Ingestion Subgraph

This module implements a configuration-driven ingestion subgraph for AI company sources.

## Pipeline

1. `discover_candidates`
2. `canonicalize_candidates`
3. `expand_listing_two_level`（列表种子页 → GET HTML → 抽取同域文章链接，二级候选）
4. `decide_access_strategy`
5. `fetch_content`
6. `extract_document`
7. `normalize_document`
8. `dedup_document`
9. `persist_document`
10. `update_source_health`

## Config

Default source registry lives at:

- `configs/sources/ai_sources.yaml`

Each source supports:

- `id`, `type`, `url`, `access`, `priority`, `enabled`

## 403 / Challenge policy

- 403 is classified into `origin_forbidden`, `unknown_403`, `cloudflare_challenge`, `cloudflare_block`.
- For Cloudflare challenge/block, the system **does not attempt bypass**.
- It degrades to metadata/listing/feed modes.
- 429 applies bounded retry with backoff in `run_fetch_plan`.

## Persistence

SQLite DB path:

- `data/ingestion.sqlite3`

Tables:

- `normalized_documents`
- `fetch_attempts`
- `source_health`

## Run

```bash
python -m tide_watch.focused.cli --config configs/sources/ai_sources.yaml
```

## Tests

```bash
pytest -q tests/test_focused_*.py
```

## Add a new source

1. Add source item under target company in `configs/sources/ai_sources.yaml`.
2. Choose suitable access mode (`listing_only`, `feed_only`, `metadata_only`, etc.).
3. Run tests and ingestion demo.
