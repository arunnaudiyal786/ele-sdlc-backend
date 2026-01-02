from langgraph.graph import StateGraph, END
from .state import ImpactAssessmentState
from ..requirement.agent import requirement_agent
from ..search.agent import search_agent
from ..modules.agent import modules_agent
from ..effort.agent import effort_agent
from ..stories.agent import stories_agent
from ..code_impact.agent import code_impact_agent
from ..risks.agent import risks_agent


async def error_handler_node(state: ImpactAssessmentState) -> dict:
    """Handle errors in workflow."""
    return {
        "status": "error",
        "messages": [
            {
                "role": "error_handler",
                "content": f"Error: {state.get('error_message', 'Unknown error')}",
            }
        ],
    }


async def auto_select_node(state: ImpactAssessmentState) -> dict:
    """Auto-select top matches if none are pre-selected.

    This enables file-based pipeline execution without manual selection.
    If selected_matches is empty, auto-selects top 5 matches by score.
    """
    # If matches are already selected, pass through
    if state.get("selected_matches"):
        return {
            "status": "matches_selected",
            "current_agent": "modules",
            "messages": [
                {
                    "role": "auto_select",
                    "content": f"Using {len(state['selected_matches'])} pre-selected matches",
                }
            ],
        }

    # Auto-select top 5 matches from all_matches
    all_matches = state.get("all_matches", [])
    if not all_matches:
        return {
            "status": "error",
            "error_message": "No matches found for auto-selection",
            "current_agent": "error_handler",
        }

    # Sort by score (descending) and take top 5
    sorted_matches = sorted(all_matches, key=lambda m: m.get("score", 0), reverse=True)
    top_matches = sorted_matches[:5]

    return {
        "selected_matches": top_matches,
        "status": "matches_selected",
        "current_agent": "modules",
        "messages": [
            {
                "role": "auto_select",
                "content": f"Auto-selected top {len(top_matches)} matches from {len(all_matches)} results",
            }
        ],
    }


def route_after_search(state: ImpactAssessmentState) -> str:
    """Route based on search results."""
    if state.get("status") == "error":
        return "error_handler"
    # Always go to auto_select after search
    # auto_select will handle both pre-selected and auto-selection cases
    return "auto_select"


def route_after_auto_select(state: ImpactAssessmentState) -> str:
    """Route based on auto-selection results."""
    if state.get("status") == "error":
        return "error_handler"
    if not state.get("selected_matches"):
        return END
    return "modules"


def route_after_agent(state: ImpactAssessmentState) -> str:
    """Generic routing after agent execution."""
    if state.get("status") == "error":
        return "error_handler"
    next_agent = state.get("current_agent", "done")
    if next_agent == "done":
        return END
    return next_agent


def create_impact_workflow() -> StateGraph:
    """Create the LangGraph workflow for impact assessment."""
    workflow = StateGraph(ImpactAssessmentState)

    # Add nodes
    workflow.add_node("requirement", requirement_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("auto_select", auto_select_node)
    workflow.add_node("modules", modules_agent)
    workflow.add_node("effort", effort_agent)
    workflow.add_node("stories", stories_agent)
    workflow.add_node("code_impact", code_impact_agent)
    workflow.add_node("risks", risks_agent)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("requirement")

    # Wire edges
    workflow.add_edge("requirement", "search")
    workflow.add_conditional_edges(
        "search",
        route_after_search,
        {"auto_select": "auto_select", "error_handler": "error_handler"},
    )
    workflow.add_conditional_edges(
        "auto_select",
        route_after_auto_select,
        {"modules": "modules", "error_handler": "error_handler", END: END},
    )
    workflow.add_edge("modules", "effort")
    workflow.add_edge("effort", "stories")
    workflow.add_edge("stories", "code_impact")
    workflow.add_edge("code_impact", "risks")
    workflow.add_edge("risks", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()
