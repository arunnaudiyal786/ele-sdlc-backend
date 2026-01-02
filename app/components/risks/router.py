from fastapi import APIRouter, HTTPException
from .service import RisksService
from .models import RisksRequest, RisksResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/risks", response_model=RisksResponse)
async def generate_risks(request: RisksRequest) -> RisksResponse:
    """Generate risk analysis."""
    try:
        service = RisksService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
