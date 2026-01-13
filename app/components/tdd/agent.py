from typing import Dict, Any
from .service import TDDService
from .models import TDDRequest

_service: TDDService | None = None


def get_service() -> TDDService:
    global _service
    if _service is None:
        _service = TDDService()
    return _service


async def tdd_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for TDD generation."""
    try:
        service = get_service()

        request = TDDRequest(
            session_id=state["session_id"],
            requirement_text=state["requirement_text"],
            selected_matches=state.get("selected_matches", []),
            impacted_modules_output=state.get("impacted_modules_output", {}),
            estimation_effort_output=state.get("estimation_effort_output", {}),
        )

        response = await service.process(request)

        return {
            "tdd_output": response.model_dump(),
            "status": "tdd_generated",
            "current_agent": "jira_stories",
            "messages": [
                {
                    "role": "tdd",
                    "content": f"Generated TDD: {response.tdd_name} (saved to {response.markdown_file_path})",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
