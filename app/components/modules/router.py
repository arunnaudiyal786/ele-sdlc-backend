from fastapi import APIRouter, HTTPException
from .service import ModulesService
from .models import ModulesRequest, ModulesResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/modules", response_model=ModulesResponse)
async def generate_modules(request: ModulesRequest) -> ModulesResponse:
    """Generate impacted modules analysis."""
    try:
        service = ModulesService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
