from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


@router.post("/run-pipeline/stream")
async def run_pipeline_stream(request: PipelineRequest) -> StreamingResponse:
    """Run impact assessment pipeline with real-time SSE progress updates.

    Returns Server-Sent Events (SSE) stream with events:
    - pipeline_start: Pipeline execution begins
    - agent_complete: An agent finishes (includes output)
    - pipeline_complete: All agents finished successfully
    - pipeline_error: Error occurred during execution
    """
    try:
        service = get_service()
        return StreamingResponse(
            service.process_streaming(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
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
