from langchain_core.tools import tool
from typing import List, Dict
import asyncio


@tool
def search_similar_projects(
    query: str,
    top_k: int = 10,
    semantic_weight: float = 0.7,
) -> List[Dict]:
    """Search for similar historical projects.

    Args:
        query: Search query (requirement text)
        top_k: Number of results to return
        semantic_weight: Weight for semantic vs keyword search

    Returns:
        List of matching projects with scores
    """
    from .service import SearchService
    from .models import SearchRequest

    service = SearchService()
    request = SearchRequest(
        session_id="tool_call",
        query=query,
        semantic_weight=semantic_weight,
        keyword_weight=1.0 - semantic_weight,
        max_results=top_k,
    )

    response = asyncio.get_event_loop().run_until_complete(service.process(request))
    return [m.model_dump() for m in response.matches]
