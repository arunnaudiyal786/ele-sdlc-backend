from fastapi import APIRouter, Depends, HTTPException
from .service import SessionService
from .models import SessionCreateRequest, SessionResponse, SessionAuditResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/session", tags=["Session"])

_service: SessionService | None = None


def get_service() -> SessionService:
    global _service
    if _service is None:
        _service = SessionService()
    return _service


@router.post("/create", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_service),
) -> SessionResponse:
    """Create a new assessment session."""
    return await service.process(request)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_service),
) -> SessionResponse:
    """Get session details."""
    try:
        return await service.get_session(session_id)
    except ComponentError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())


@router.get("/{session_id}/audit", response_model=SessionAuditResponse)
async def get_session_audit(
    session_id: str,
    service: SessionService = Depends(get_service),
) -> SessionAuditResponse:
    """Get full audit trail for a session."""
    try:
        return await service.get_audit(session_id)
    except ComponentError as e:
        raise HTTPException(status_code=404, detail=e.to_dict())
