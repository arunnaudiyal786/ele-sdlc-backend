from typing import Dict, Any
from .service import StoriesService
from .models import StoriesRequest

_service: StoriesService | None = None


def get_service() -> StoriesService:
    global _service
    if _service is None:
        _service = StoriesService()
    return _service


async def stories_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for stories generation."""
    try:
        service = get_service()

        request = StoriesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            modules_output=state.get("modules_output", {}),
            effort_output=state.get("effort_output", {}),
        )

        response = await service.process(request)

        return {
            "stories_output": response.model_dump(),
            "status": "stories_generated",
            "current_agent": "code_impact",
            "messages": [
                {
                    "role": "stories",
                    "content": f"Generated {response.total_stories} stories ({response.total_story_points} points)",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
