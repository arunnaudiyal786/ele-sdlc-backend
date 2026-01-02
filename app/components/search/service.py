import time
from typing import List, Dict
from app.components.base.component import BaseComponent
from app.components.base.config import get_settings
from app.rag.hybrid_search import HybridSearchService
from app.utils.audit import AuditTrailManager
from .models import SearchRequest, SearchResponse, MatchResult, MatchSelectionRequest, MatchSelectionResponse


class SearchService(BaseComponent[SearchRequest, SearchResponse]):
    """Hybrid search service as a component."""

    def __init__(self):
        self.hybrid_search = HybridSearchService.get_instance()
        self.config = get_settings()

    @property
    def component_name(self) -> str:
        return "search"

    async def process(self, request: SearchRequest) -> SearchResponse:
        """Execute hybrid search."""
        start = time.time()

        results = await self.hybrid_search.search(
            query=request.query,
            collections=["epics", "estimations", "tdds"],
            top_k=request.max_results,
            semantic_weight=request.semantic_weight,
            keyword_weight=request.keyword_weight,
        )

        matches = [self._convert_to_match_result(r) for r in results]
        elapsed_ms = int((time.time() - start) * 1000)

        # Save to audit trail
        audit = AuditTrailManager(request.session_id)
        audit.save_json(
            "search_request.json",
            request.model_dump(),
            subfolder="step2_search",
        )
        audit.save_json(
            "all_matches.json",
            [m.model_dump() for m in matches],
            subfolder="step2_search",
        )
        audit.record_timing("search", elapsed_ms)

        return SearchResponse(
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
            subfolder="step2_search",
        )
        audit.add_step_completed("matches_selected")

        return MatchSelectionResponse(
            session_id=request.session_id,
            selected_count=len(request.selected_match_ids),
            status="matches_selected",
        )

    def _convert_to_match_result(self, result: Dict) -> MatchResult:
        """Convert raw search result to MatchResult."""
        metadata = result.get("metadata", {})
        return MatchResult(
            match_id=result.get("id", ""),
            epic_id=metadata.get("epic_id", ""),
            epic_name=metadata.get("epic_name", result.get("text", "")[:100]),
            description=result.get("text", "")[:500],
            match_score=result.get("final_score", 0.0),
            score_breakdown=result.get("score_breakdown", {}),
            technologies=metadata.get("technologies", []),
            actual_hours=metadata.get("actual_hours"),
            estimated_hours=metadata.get("estimated_hours"),
        )
