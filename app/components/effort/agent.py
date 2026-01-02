from typing import Dict, Any
from .service import EffortService
from .models import EffortRequest

_service: EffortService | None = None


def get_service() -> EffortService:
    global _service
    if _service is None:
        _service = EffortService()
    return _service


async def effort_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for effort estimation."""
    try:
        service = get_service()

        request = EffortRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            modules_output=state.get("modules_output", {}),
        )

        response = await service.process(request)

        return {
            "effort_output": response.model_dump(),
            "status": "effort_estimated",
            "current_agent": "stories",
            "messages": [
                {
                    "role": "effort",
                    "content": f"Estimated {response.total_hours} total hours ({response.confidence} confidence)",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
