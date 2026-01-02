from fastapi import APIRouter, HTTPException
from .service import CodeImpactService
from .models import CodeImpactRequest, CodeImpactResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/code", response_model=CodeImpactResponse)
async def generate_code_impact(request: CodeImpactRequest) -> CodeImpactResponse:
    """Generate code impact analysis."""
    try:
        service = CodeImpactService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
