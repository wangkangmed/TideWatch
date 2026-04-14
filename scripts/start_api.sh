#!/usr/bin/env bash
# Start the TideWatch read-only API server.
# Usage: bash scripts/start_api.sh [--port 8000] [--db path/to/db.sqlite]
set -euo pipefail
cd "$(dirname "$0")/.."

PORT="${1:-8000}"
export TIDEWATCH_DB_PATH="${TIDEWATCH_DB_PATH:-$(pwd)/data/real_network_run.sqlite}"

echo "Starting TideWatch API on port $PORT (DB: $TIDEWATCH_DB_PATH)"
exec python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port "$PORT" --reload
