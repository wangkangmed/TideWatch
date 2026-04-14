"""Watchlist endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import watchlists_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/watchlists")
def list_watchlists(
    run_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = watchlists_repo.list_watchlists(run_id=run_id, page=page, page_size=page_size)
    return paginate(items, total, page, page_size)


@router.get("/watchlists/{watchlist_id}")
def get_watchlist(watchlist_id: str, run_id: str | None = Query(None)):
    result = watchlists_repo.get_watchlist(watchlist_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return result
