"""Recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import recommendations_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/recommendations")
def list_recommendations(
    run_id: str | None = Query(None),
    recommended_action: str | None = Query(None),
    sort: str = Query("priority"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = recommendations_repo.list_recommendations(
        run_id=run_id, recommended_action=recommended_action,
        sort=sort, page=page, page_size=page_size,
    )
    return paginate(items, total, page, page_size)


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str, run_id: str | None = Query(None)):
    result = recommendations_repo.get_recommendation(recommendation_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result
