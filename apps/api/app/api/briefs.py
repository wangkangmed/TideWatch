"""Brief / Briefing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import briefs_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/briefs")
def list_briefs(
    run_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = briefs_repo.list_briefs(run_id=run_id, page=page, page_size=page_size)
    return paginate(items, total, page, page_size)


@router.get("/briefs/{brief_id}")
def get_brief(brief_id: str, run_id: str | None = Query(None)):
    result = briefs_repo.get_brief(brief_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Brief not found")
    return result


@router.get("/briefing-items")
def list_briefing_items(
    run_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = briefs_repo.list_briefing_items(run_id=run_id, page=page, page_size=page_size)
    return paginate(items, total, page, page_size)
