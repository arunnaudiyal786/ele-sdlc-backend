from fastapi import APIRouter, HTTPException
from .service import EstimationEffortService
from .models import EstimationEffortRequest, EstimationEffortResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/estimation-effort", response_model=EstimationEffortResponse)
async def generate_estimation_effort(request: EstimationEffortRequest) -> EstimationEffortResponse:
    """Generate estimation effort."""
    try:
        service = EstimationEffortService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
