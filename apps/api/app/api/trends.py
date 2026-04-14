"""Trend endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import trends_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/trends")
def list_trends(
    run_id: str | None = Query(None),
    subject: str | None = Query(None),
    theme: str | None = Query(None),
    trend_type: str | None = Query(None),
    sort: str = Query("strength"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = trends_repo.list_trends(
        run_id=run_id, subject=subject, theme=theme,
        trend_type=trend_type, sort=sort, page=page, page_size=page_size,
    )
    return paginate(items, total, page, page_size)


@router.get("/trends/{trend_id}")
def get_trend(trend_id: str, run_id: str | None = Query(None)):
    result = trends_repo.get_trend(trend_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trend not found")
    return result
