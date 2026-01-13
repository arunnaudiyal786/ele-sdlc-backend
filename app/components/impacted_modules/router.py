from fastapi import APIRouter, HTTPException
from .service import ImpactedModulesService
from .models import ImpactedModulesRequest, ImpactedModulesResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/impacted-modules", response_model=ImpactedModulesResponse)
async def generate_impacted_modules(request: ImpactedModulesRequest) -> ImpactedModulesResponse:
    """Generate impacted modules analysis."""
    try:
        service = ImpactedModulesService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
