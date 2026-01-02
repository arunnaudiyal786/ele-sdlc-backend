from typing import Dict, Any
from .service import SearchService
from .models import SearchRequest

_service: SearchService | None = None


def get_service() -> SearchService:
    global _service
    if _service is None:
        _service = SearchService()
    return _service


async def search_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for historical search.

    Returns PARTIAL state update.
    """
    try:
        service = get_service()

        request = SearchRequest(
            session_id=state["session_id"],
            query=state["requirement_text"],
        )

        response = await service.process(request)
        matches = [m.model_dump() for m in response.matches]

        return {
            "all_matches": matches,
            "status": "matches_found",
            "current_agent": "await_selection",
            "messages": [
                {
                    "role": "search",
                    "content": f"Found {response.total_matches} similar projects",
                }
            ],
            "timing": {"search_ms": response.search_time_ms},
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
