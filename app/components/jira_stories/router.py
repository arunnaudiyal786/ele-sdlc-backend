from fastapi import APIRouter, HTTPException
from .service import JiraStoriesService
from .models import JiraStoriesRequest, JiraStoriesResponse
from app.components.base.exceptions import ComponentError

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


@router.post("/generate/jira-stories", response_model=JiraStoriesResponse)
async def generate_jira_stories(request: JiraStoriesRequest) -> JiraStoriesResponse:
    """Generate Jira stories."""
    try:
        service = JiraStoriesService()
        return await service.process(request)
    except ComponentError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
