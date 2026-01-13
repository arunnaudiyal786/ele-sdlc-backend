from fastapi import APIRouter, HTTPException
from .service import TDDService
from .models import TDDRequest, TDDResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/tdd", response_model=TDDResponse)
async def generate_tdd(request: TDDRequest) -> TDDResponse:
    """Generate Technical Design Document."""
    try:
        service = TDDService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
