# TideWatch

TideWatch is a LangGraph-based information acquisition layer.

## Content ingestion subgraph

This repository now includes a configurable, degradation-aware ingestion subgraph:

- package: `tide_watch.focused`
- graph builder: `tide_watch.focused.graph.build_ingestion_subgraph`
- default source config: `configs/sources/ai_sources.yaml`

### Why degradation instead of bypass

When anti-bot / challenge pages are detected (e.g. Cloudflare challenge):

- TideWatch does **not** implement bypass logic
- it degrades to `metadata_only` / `feed_only` / `listing_only`

This keeps ingestion compliant and robust for long-running workflows.

## Run demo

```bash
python -m tide_watch.focused.cli --config configs/sources/ai_sources.yaml
```

## Tests

```bash
pytest -q
```
