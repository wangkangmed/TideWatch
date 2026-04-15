# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

TideWatch is a LangGraph-based AI competitive intelligence platform. The repo is a monorepo with three components:

| Component | Path | Tech |
|---|---|---|
| Core library | `src/tide_watch/` | Python 3.12, LangGraph, httpx, feedparser |
| Read-only API | `apps/api/` | FastAPI, Uvicorn, Pydantic |
| Analyst dashboard | `apps/web/` | Next.js 14, React 18, TypeScript |

Data is stored in SQLite files under `data/` (pre-populated, no external DB needed).

### Running services

**FastAPI backend** (port 8000):
```bash
cd /workspace && PYTHONPATH=/workspace/src .venv/bin/uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Next.js frontend** (port 3000):
```bash
cd /workspace/apps/web && NEXT_PUBLIC_API_URL=http://localhost:8000 npx next dev --port 3000
```

The frontend proxies `/api/*` to the backend via `next.config.js` rewrites.

### Linting

- **Python**: `.venv/bin/ruff check .` (run from repo root)
- **Frontend**: `cd apps/web && npx next lint`

### Testing

Run all tests from the repo root:
```bash
PYTHONPATH=/workspace/src:/workspace/apps/api .venv/bin/pytest -q --import-mode=importlib
```

Key notes:
- `PYTHONPATH` must include both `/workspace/src` (for `tide_watch`) and `/workspace/apps/api` (for API tests that import `from app.main`).
- `--import-mode=importlib` is required because `tests/__init__.py` exists; without it, pytest fails to collect.

### Gotchas

- The `.venv` shipped in the repo has broken shebangs pointing to `/root/project/TideWatch/...`. The update script recreates it with correct paths.
- `apps/web/package.json` doesn't list `eslint` or `eslint-config-next` as devDependencies; the update script installs them so `next lint` works.
- `python3.12-venv` system package is required to recreate the venv (installed by apt).
- The LangGraph pipeline and search connectors require optional API keys (`OPENAI_API_KEY`, `NEWSAPI_API_KEY`, `BRAVE_SEARCH_API_KEY`, etc.) that are NOT needed for the dashboard or tests.
