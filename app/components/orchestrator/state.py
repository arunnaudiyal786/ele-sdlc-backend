from typing import TypedDict, Annotated, List, Dict, Optional, Literal
import operator


class ImpactAssessmentState(TypedDict, total=False):
    """Workflow state for impact assessment pipeline.

    Using total=False allows nodes to return PARTIAL updates.
    LangGraph automatically merges partial returns into full state.
    """

    # SESSION CONTEXT - Set at workflow start
    session_id: str
    requirement_text: str
    jira_epic_id: Optional[str]
    extracted_keywords: List[str]

    # SEARCH RESULTS - Set by search component
    all_matches: List[Dict]
    selected_matches: List[Dict]

    # AGENT OUTPUTS - Set by each agent component
    modules_output: Dict
    effort_output: Dict
    stories_output: Dict
    code_impact_output: Dict
    risks_output: Dict

    # CONTROL FIELDS - Updated throughout workflow
    status: Literal[
        "created",
        "requirement_submitted",
        "matches_found",
        "matches_selected",
        "generating_impact",
        "completed",
        "error",
    ]
    current_agent: str
    error_message: Optional[str]

    # TIMING & AUDIT
    timing: Dict[str, int]

    # Accumulated messages (uses operator.add reducer)
    messages: Annotated[List[Dict], operator.add]
