from fastapi import APIRouter, Depends, HTTPException
from .service import HistoricalMatchService
from .models import HistoricalMatchRequest, HistoricalMatchResponse, MatchSelectionRequest, MatchSelectionResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/historical-match", tags=["Historical Match"])

_service: HistoricalMatchService | None = None


def get_service() -> HistoricalMatchService:
    global _service
    if _service is None:
        _service = HistoricalMatchService()
    return _service


@router.post("/find-matches", response_model=HistoricalMatchResponse)
async def find_matches(
    request: HistoricalMatchRequest,
    service: HistoricalMatchService = Depends(get_service),
) -> HistoricalMatchResponse:
    """Search for similar historical projects."""
    try:
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())


@router.post("/select-matches", response_model=MatchSelectionResponse)
async def select_matches(
    request: MatchSelectionRequest,
    service: HistoricalMatchService = Depends(get_service),
) -> MatchSelectionResponse:
    """Select matches for impact analysis."""
    try:
        return await service.select_matches(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
