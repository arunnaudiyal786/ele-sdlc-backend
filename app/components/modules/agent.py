from typing import Dict, Any
from .service import ModulesService
from .models import ModulesRequest

_service: ModulesService | None = None


def get_service() -> ModulesService:
    global _service
    if _service is None:
        _service = ModulesService()
    return _service


async def modules_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for modules identification."""
    try:
        service = get_service()

        request = ModulesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
        )

        response = await service.process(request)

        return {
            "modules_output": response.model_dump(),
            "status": "modules_generated",
            "current_agent": "effort",
            "messages": [
                {
                    "role": "modules",
                    "content": f"Identified {response.total_modules} impacted modules",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
