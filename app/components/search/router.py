from fastapi import APIRouter, Depends, HTTPException
from .service import SearchService
from .models import SearchRequest, SearchResponse, MatchSelectionRequest, MatchSelectionResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/search", tags=["Search"])

_service: SearchService | None = None


def get_service() -> SearchService:
    global _service
    if _service is None:
        _service = SearchService()
    return _service


@router.post("/find-matches", response_model=SearchResponse)
async def find_matches(
    request: SearchRequest,
    service: SearchService = Depends(get_service),
) -> SearchResponse:
    """Search for similar historical projects."""
    try:
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())


@router.post("/select-matches", response_model=MatchSelectionResponse)
async def select_matches(
    request: MatchSelectionRequest,
    service: SearchService = Depends(get_service),
) -> MatchSelectionResponse:
    """Select matches for impact analysis."""
    try:
        return await service.select_matches(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
