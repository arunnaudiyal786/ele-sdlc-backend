from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from .service import OrchestratorService, PipelineRequest, PipelineResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])

_service: OrchestratorService | None = None


def get_service() -> OrchestratorService:
    global _service
    if _service is None:
        _service = OrchestratorService()
    return _service


@router.post("/run-pipeline", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest) -> PipelineResponse:
    """Run full impact assessment pipeline."""
    try:
        service = get_service()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())


@router.get("/{session_id}/summary")
async def get_summary(session_id: str) -> Dict[str, Any]:
    """Get impact assessment summary for a session."""
    try:
        service = get_service()
        return await service.get_summary(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
