"""Run endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..repositories import runs_repo
from ..schemas.common import paginate

router = APIRouter()


@router.get("/runs")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
):
    items, total = runs_repo.list_runs(page=page, page_size=page_size)
    return paginate(items, total, page, page_size)


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    result = runs_repo.get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result
