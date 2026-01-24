from langgraph.graph import StateGraph, END
from .state import ImpactAssessmentState
from ..requirement.agent import requirement_agent
from ..historical_match.agent import historical_match_agent
from ..impacted_modules.agent import impacted_modules_agent
from ..estimation_effort.agent import estimation_effort_agent
from ..tdd.agent import tdd_agent
from ..jira_stories.agent import jira_stories_agent
# Temporarily disabled agents
# from ..code_impact.agent import code_impact_agent
# from ..risks.agent import risks_agent


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
    """Auto-select top matches and load full documents.

    This node:
    1. Auto-selects top 3 matches by score (if not pre-selected)
    2. Loads full documents (TDD, estimation, jira_stories) for selected projects
    3. Stores loaded_projects in state for agents to use
    """
    from app.services.context_assembler import ContextAssembler
    from app.services.project_indexer import ProjectMetadata
    from app.rag.hybrid_search import HybridSearchService

    # If matches are already selected, use them; otherwise auto-select top 3
    selected_matches = state.get("selected_matches")
    if not selected_matches:
        all_matches = state.get("all_matches", [])
        if not all_matches:
            return {
                "status": "error",
                "error_message": "No matches found for auto-selection",
                "current_agent": "error_handler",
            }
        # Sort by match_score (descending) and take top 3
        sorted_matches = sorted(all_matches, key=lambda m: m.get("match_score", 0), reverse=True)
        selected_matches = sorted_matches[:3]

    # Extract project IDs from selected matches
    project_ids = [m.get("epic_id") for m in selected_matches]

    # Get project metadata from hybrid search service (contains file paths)
    search_service = HybridSearchService.get_instance()
    project_matches = await search_service.search_projects(
        query=state["requirement_text"],
        top_k=20,  # Get more to find all selected IDs
    )

    # Filter to only selected projects
    metadata_list = []
    for pm in project_matches:
        if pm.project_id in project_ids:
            metadata = ProjectMetadata(
                project_id=pm.project_id,
                project_name=pm.project_name,
                summary=pm.summary,
                folder_path=pm.folder_path,
                tdd_path=pm.tdd_path,
                estimation_path=pm.estimation_path,
                jira_stories_path=pm.jira_stories_path,
            )
            metadata_list.append(metadata)

    # Load full documents
    assembler = ContextAssembler()
    loaded_projects = await assembler.load_full_documents(
        project_ids=project_ids,
        project_metadata=metadata_list,
    )

    # Convert to dict for state storage
    loaded_projects_dict = {
        project_id: docs.model_dump()
        for project_id, docs in loaded_projects.items()
    }

    return {
        "selected_matches": selected_matches,
        "loaded_projects": loaded_projects_dict,
        "status": "matches_selected",
        "current_agent": "impacted_modules",
        "messages": [
            {
                "role": "auto_select",
                "content": f"Selected {len(selected_matches)} projects and loaded full documents",
            }
        ],
    }


def route_after_historical_match(state: ImpactAssessmentState) -> str:
    """Route based on historical match results."""
    if state.get("status") == "error":
        return "error_handler"
    # Always go to auto_select after historical_match
    # auto_select will handle both pre-selected and auto-selection cases
    return "auto_select"


def route_after_auto_select(state: ImpactAssessmentState) -> str:
    """Route based on auto-selection results."""
    if state.get("status") == "error":
        return "error_handler"
    if not state.get("selected_matches"):
        return END
    return "impacted_modules"


def route_after_agent(state: ImpactAssessmentState) -> str:
    """Generic routing after agent execution."""
    if state.get("status") == "error":
        return "error_handler"
    next_agent = state.get("current_agent", "done")
    if next_agent == "done":
        return END
    return next_agent


def create_impact_workflow() -> StateGraph:
    """Create the LangGraph workflow for impact assessment.

    Workflow:
    requirement -> historical_match -> auto_select -> impacted_modules
    -> estimation_effort -> tdd -> jira_stories -> END

    Note: code_impact and risks agents are temporarily disabled.
    """
    workflow = StateGraph(ImpactAssessmentState)

    # Add nodes
    workflow.add_node("requirement", requirement_agent)
    workflow.add_node("historical_match", historical_match_agent)
    workflow.add_node("auto_select", auto_select_node)
    workflow.add_node("impacted_modules", impacted_modules_agent)
    workflow.add_node("estimation_effort", estimation_effort_agent)
    workflow.add_node("tdd", tdd_agent)
    workflow.add_node("jira_stories", jira_stories_agent)
    # Temporarily disabled nodes
    # workflow.add_node("code_impact", code_impact_agent)
    # workflow.add_node("risks", risks_agent)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("requirement")

    # Wire edges
    workflow.add_edge("requirement", "historical_match")
    workflow.add_conditional_edges(
        "historical_match",
        route_after_historical_match,
        {"auto_select": "auto_select", "error_handler": "error_handler"},
    )
    workflow.add_conditional_edges(
        "auto_select",
        route_after_auto_select,
        {"impacted_modules": "impacted_modules", "error_handler": "error_handler", END: END},
    )
    workflow.add_edge("impacted_modules", "estimation_effort")
    workflow.add_edge("estimation_effort", "tdd")
    workflow.add_edge("tdd", "jira_stories")
    workflow.add_edge("jira_stories", END)  # End after jira stories generation
    # Temporarily disabled edges
    # workflow.add_edge("jira_stories", "code_impact")
    # workflow.add_edge("code_impact", "risks")
    # workflow.add_edge("risks", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()
