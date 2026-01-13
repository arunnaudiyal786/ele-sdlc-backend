from typing import Dict, Any
from .service import JiraStoriesService
from .models import JiraStoriesRequest

_service: JiraStoriesService | None = None


def get_service() -> JiraStoriesService:
    global _service
    if _service is None:
        _service = JiraStoriesService()
    return _service


async def jira_stories_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for Jira stories generation."""
    try:
        service = get_service()

        request = JiraStoriesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules_output=state.get("impacted_modules_output", {}),
            estimation_effort_output=state.get("estimation_effort_output", {}),
            tdd_output=state.get("tdd_output", {}),
        )

        response = await service.process(request)

        return {
            "jira_stories_output": response.model_dump(),
            "status": "jira_stories_generated",
            "current_agent": "code_impact",
            "messages": [
                {
                    "role": "jira_stories",
                    "content": f"Generated {response.total_stories} Jira stories ({response.total_story_points} points)",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
