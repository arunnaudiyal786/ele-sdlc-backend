from fastapi import APIRouter, HTTPException
from .service import EffortService
from .models import EffortRequest, EffortResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/effort", response_model=EffortResponse)
async def generate_effort(request: EffortRequest) -> EffortResponse:
    """Generate effort estimation."""
    try:
        service = EffortService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
