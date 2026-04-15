"""Alert endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import alerts_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/alerts")
def list_alerts(
    run_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = alerts_repo.list_alerts(run_id=run_id, page=page, page_size=page_size)
    return paginate(items, total, page, page_size)
