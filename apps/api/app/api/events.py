"""Event endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import events_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/events")
def list_events(
    run_id: str | None = Query(None),
    event_type: str | None = Query(None),
    sort: str = Query("significance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = events_repo.list_events(
        run_id=run_id, event_type=event_type,
        sort=sort, page=page, page_size=page_size,
    )
    return paginate(items, total, page, page_size)


@router.get("/events/{event_id}")
def get_event(event_id: str, run_id: str | None = Query(None)):
    result = events_repo.get_event(event_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    return result
