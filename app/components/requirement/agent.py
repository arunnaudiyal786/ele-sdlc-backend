from typing import Dict, Any
from .service import RequirementService
from .models import RequirementSubmitRequest

_service: RequirementService | None = None


def get_service() -> RequirementService:
    global _service
    if _service is None:
        _service = RequirementService()
    return _service


async def requirement_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node for requirement processing.

    Returns PARTIAL state update - only changed fields.
    """
    try:
        service = get_service()

        request = RequirementSubmitRequest(
            session_id=state["session_id"],
            requirement_description=state["requirement_text"],
            jira_epic_id=state.get("jira_epic_id"),
        )

        response = await service.process(request)

        return {
            "extracted_keywords": response.extracted_keywords,
            "status": "requirement_submitted",
            "current_agent": "search",
            "messages": [
                {
                    "role": "requirement",
                    "content": f"Extracted {len(response.extracted_keywords)} keywords",
                }
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "current_agent": "error_handler",
        }
