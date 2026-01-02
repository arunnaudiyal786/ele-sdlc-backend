from typing import Dict, Any
from .service import RisksService
from .models import RisksRequest

_service: RisksService | None = None


def get_service() -> RisksService:
    global _service
    if _service is None:
        _service = RisksService()
    return _service


async def risks_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for risk identification."""
    try:
        service = get_service()

        request = RisksRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            modules_output=state.get("modules_output", {}),
            effort_output=state.get("effort_output", {}),
            code_impact_output=state.get("code_impact_output", {}),
        )

        response = await service.process(request)

        return {
            "risks_output": response.model_dump(),
            "status": "completed",
            "current_agent": "done",
            "messages": [
                {
                    "role": "risks",
                    "content": f"Identified {response.total_risks} risks ({response.high_severity_count} high severity)",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
