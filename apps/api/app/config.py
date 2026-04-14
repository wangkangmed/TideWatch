"""API configuration – reads from environment with sensible defaults."""

from __future__ import annotations

import os
from pathlib import Path

_BASE = Path(__file__).resolve().parents[3]

DB_PATH: str = os.getenv(
    "TIDEWATCH_DB_PATH",
    str(_BASE / "data" / "real_network_run.sqlite"),
)

API_PREFIX: str = "/api/v1"
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
