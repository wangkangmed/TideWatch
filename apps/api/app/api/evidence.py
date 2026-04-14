"""Evidence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..repositories import evidence_repo

router = APIRouter()


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str, run_id: str | None = Query(None)):
    result = evidence_repo.get_evidence(evidence_id, run_id=run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return result
