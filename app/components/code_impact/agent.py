from typing import Dict, Any
from .service import CodeImpactService
from .models import CodeImpactRequest

_service: CodeImpactService | None = None


def get_service() -> CodeImpactService:
    global _service
    if _service is None:
        _service = CodeImpactService()
    return _service


async def code_impact_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for code impact analysis."""
    try:
        service = get_service()

        request = CodeImpactRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules_output=state.get("impacted_modules_output", {}),
            jira_stories_output=state.get("jira_stories_output", {}),
        )

        response = await service.process(request)

        return {
            "code_impact_output": response.model_dump(),
            "status": "code_impact_analyzed",
            "current_agent": "risks",
            "messages": [
                {
                    "role": "code_impact",
                    "content": f"Identified {response.total_files} impacted files across {len(response.repositories_affected)} repos",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
