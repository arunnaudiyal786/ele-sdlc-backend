from fastapi import APIRouter, HTTPException
from .service import StoriesService
from .models import StoriesRequest, StoriesResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/stories", response_model=StoriesResponse)
async def generate_stories(request: StoriesRequest) -> StoriesResponse:
    """Generate Jira stories."""
    try:
        service = StoriesService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
