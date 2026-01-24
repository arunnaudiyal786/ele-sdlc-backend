from typing import Dict, Any
from .service import ImpactedModulesService
from .models import ImpactedModulesRequest

_service: ImpactedModulesService | None = None


def get_service() -> ImpactedModulesService:
    global _service
    if _service is None:
        _service = ImpactedModulesService()
    return _service


async def impacted_modules_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for impacted modules identification."""
    try:
        service = get_service()

        request = ImpactedModulesRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            loaded_projects=state.get("loaded_projects", {}),
        )

        response = await service.process(request)

        return {
            "impacted_modules_output": response.model_dump(),
            "status": "impacted_modules_generated",
            "current_agent": "estimation_effort",
            "messages": [
                {
                    "role": "impacted_modules",
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
