from typing import Dict, Any
from .service import EstimationEffortService
from .models import EstimationEffortRequest

_service: EstimationEffortService | None = None


def get_service() -> EstimationEffortService:
    global _service
    if _service is None:
        _service = EstimationEffortService()
    return _service


async def estimation_effort_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for estimation effort."""
    try:
        service = get_service()

        request = EstimationEffortRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules_output=state.get("impacted_modules_output", {}),
            loaded_projects=state.get("loaded_projects", {}),
        )

        response = await service.process(request)

        return {
            "estimation_effort_output": response.model_dump(),
            "status": "estimation_effort_completed",
            "current_agent": "tdd",
            "messages": [
                {
                    "role": "estimation_effort",
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
