import json
import time
from typing import List, Dict
from app.components.base.component import BaseComponent
from app.components.base.config import get_settings
from app.rag.hybrid_search import HybridSearchService
from app.utils.audit import AuditTrailManager
from .models import HistoricalMatchRequest, HistoricalMatchResponse, MatchResult, MatchSelectionRequest, MatchSelectionResponse


class HistoricalMatchService(BaseComponent[HistoricalMatchRequest, HistoricalMatchResponse]):
    """Historical match service as a component."""

    def __init__(self):
        self.hybrid_search = HybridSearchService.get_instance()
        self.config = get_settings()

    @property
    def component_name(self) -> str:
        return "historical_match"

    async def process(self, request: HistoricalMatchRequest) -> HistoricalMatchResponse:
        """Execute hybrid search for historical matches using project_index."""
        start = time.time()

        # Use new search_projects method that searches project_index collection
        project_matches = await self.hybrid_search.search_projects(
            query=request.query,
            top_k=request.max_results,
        )

        # Convert ProjectMatch objects to MatchResult for backward compatibility
        matches = [self._convert_project_match_to_result(pm) for pm in project_matches]
        elapsed_ms = int((time.time() - start) * 1000)

        # Save to audit trail
        audit = AuditTrailManager(request.session_id)
        audit.save_json(
            "historical_match_request.json",
            request.model_dump(),
            subfolder="step2_historical_match",
        )
        audit.save_json(
            "all_matches.json",
            [m.model_dump() for m in matches],
            subfolder="step2_historical_match",
        )
        audit.record_timing("historical_match", elapsed_ms)

        return HistoricalMatchResponse(
            session_id=request.session_id,
            total_matches=len(matches),
            matches=matches,
            search_time_ms=elapsed_ms,
        )

    async def select_matches(self, request: MatchSelectionRequest) -> MatchSelectionResponse:
        """Select matches for impact analysis."""
        audit = AuditTrailManager(request.session_id)
        audit.save_json(
            "selected_matches.json",
            {"selected_ids": request.selected_match_ids},
            subfolder="step2_historical_match",
        )
        audit.add_step_completed("matches_selected")

        return MatchSelectionResponse(
            session_id=request.session_id,
            selected_count=len(request.selected_match_ids),
            status="matches_selected",
        )

    def _convert_project_match_to_result(self, project_match) -> MatchResult:
        """Convert ProjectMatch to MatchResult for backward compatibility.

        Args:
            project_match: ProjectMatch object from search_projects()

        Returns:
            MatchResult compatible with existing agents
        """
        return MatchResult(
            match_id=project_match.project_id,
            epic_id=project_match.project_id,  # Use project_id as epic_id
            epic_name=project_match.project_name,
            description=project_match.summary[:500],
            match_score=project_match.match_score,
            score_breakdown={
                "semantic_score": project_match.score_breakdown.semantic_score,
                "keyword_score": project_match.score_breakdown.keyword_score,
            },
            technologies=[],  # Not available in project index metadata
            actual_hours=None,  # Will be loaded from full documents
            estimated_hours=None,  # Will be loaded from full documents
        )

    def _convert_to_match_result(self, result: Dict) -> MatchResult:
        """Convert raw search result to MatchResult (legacy method)."""
        metadata = result.get("metadata", {})
        technologies = self._parse_list_field(metadata.get("technologies", []))
        return MatchResult(
            match_id=result.get("id", ""),
            epic_id=metadata.get("epic_id", ""),
            epic_name=metadata.get("epic_name", result.get("text", "")[:100]),
            description=result.get("text", "")[:500],
            match_score=result.get("final_score", 0.0),
            score_breakdown=result.get("score_breakdown", {}),
            technologies=technologies,
            actual_hours=metadata.get("actual_hours"),
            estimated_hours=metadata.get("estimated_hours"),
        )

    def _parse_list_field(self, value) -> List[str]:
        """Parse a list field that may be stored as a string."""
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return []
        # Try JSON parsing (handles double-quoted strings)
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            pass
        # Handle Python-style single quotes by replacing with double quotes
        try:
            normalized = value.replace("'", '"')
            parsed = json.loads(normalized)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
