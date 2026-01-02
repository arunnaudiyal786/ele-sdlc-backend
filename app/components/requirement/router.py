from fastapi import APIRouter, Depends, HTTPException
from .service import RequirementService
from .models import RequirementSubmitRequest, RequirementResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/requirement", tags=["Requirement"])

_service: RequirementService | None = None


def get_service() -> RequirementService:
    global _service
    if _service is None:
        _service = RequirementService()
    return _service


@router.post("/submit", response_model=RequirementResponse)
async def submit_requirement(
    request: RequirementSubmitRequest,
    service: RequirementService = Depends(get_service),
) -> RequirementResponse:
    """Submit a requirement for analysis."""
    try:
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
