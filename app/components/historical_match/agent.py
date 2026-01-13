from typing import Dict, Any
from .service import HistoricalMatchService
from .models import HistoricalMatchRequest

_service: HistoricalMatchService | None = None


def get_service() -> HistoricalMatchService:
    global _service
    if _service is None:
        _service = HistoricalMatchService()
    return _service


async def historical_match_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for historical match search.

    Returns PARTIAL state update.
    """
    try:
        service = get_service()

        request = HistoricalMatchRequest(
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
                    "role": "historical_match",
                    "content": f"Found {response.total_matches} similar historical projects",
                }
            ],
            "timing": {"historical_match_ms": response.search_time_ms},
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
