"""Finding endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import findings_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/findings")
def list_findings(
    run_id: str | None = Query(None),
    finding_type: str | None = Query(None),
    min_importance: float | None = Query(None),
    min_decision_relevance: float | None = Query(None),
    sort: str = Query("importance"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = findings_repo.list_findings(
        run_id=run_id, finding_type=finding_type,
        min_importance=min_importance, min_decision_relevance=min_decision_relevance,
        sort=sort, page=page, page_size=page_size,
    )
    return paginate(items, total, page, page_size)


@router.get("/findings/{finding_id}")
def get_finding(finding_id: str, run_id: str | None = Query(None)):
    result = findings_repo.get_finding(finding_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Finding not found")
    return result
