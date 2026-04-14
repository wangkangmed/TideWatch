#!/usr/bin/env bash
# Start the TideWatch Web frontend dev server.
# Usage: bash scripts/start_web.sh [--port 3000]
set -euo pipefail
cd "$(dirname "$0")/../apps/web"

PORT="${1:-3000}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

echo "Starting TideWatch Web on port $PORT (API: $NEXT_PUBLIC_API_URL)"
exec npx next dev --port "$PORT"
