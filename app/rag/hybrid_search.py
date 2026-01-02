import re
from typing import List, Dict, Optional, Set
from collections import Counter
from app.components.base.config import get_settings
from .vector_store import ChromaVectorStore
from .embeddings import OllamaEmbeddingService

_instance: Optional["HybridSearchService"] = None


class HybridSearchService:
    """Hybrid search combining semantic + keyword matching."""

    STOPWORDS: Set[str] = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "this", "that", "these", "those", "it", "its", "they", "them", "their",
    }

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_service: OllamaEmbeddingService,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        # Return top frequent words
        counter = Counter(filtered)
        return [word for word, _ in counter.most_common(20)]

    def calculate_keyword_score(self, query_keywords: List[str], doc_text: str) -> float:
        """Calculate keyword overlap score."""
        if not query_keywords:
            return 0.0
        doc_lower = doc_text.lower()
        matches = sum(1 for kw in query_keywords if kw in doc_lower)
        return matches / len(query_keywords)

    async def search(
        self,
        query: str,
        collections: List[str],
        top_k: int = 10,
        semantic_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
    ) -> List[Dict]:
        """
        Hybrid search across collections.
        1. Run semantic search
        2. Calculate keyword scores
        3. Fuse scores: final = (W1 * semantic) + (W2 * keyword)
        4. Deduplicate and rank
        """
        sw = semantic_weight if semantic_weight is not None else self.semantic_weight
        kw = keyword_weight if keyword_weight is not None else self.keyword_weight

        # Get query embedding
        query_embedding = await self.embedding_service.embed(query)
        query_keywords = self.extract_keywords(query)

        all_results = []

        # Search each collection
        for collection in collections:
            try:
                semantic_results = await self.vector_store.search(
                    collection_name=collection,
                    query_embedding=query_embedding,
                    top_k=top_k * 2,  # Get more for fusion
                )

                for result in semantic_results:
                    keyword_score = self.calculate_keyword_score(
                        query_keywords, result.get("text", "")
                    )
                    semantic_score = result.get("score", 0)
                    final_score = (sw * semantic_score) + (kw * keyword_score)

                    all_results.append({
                        **result,
                        "collection": collection,
                        "semantic_score": semantic_score,
                        "keyword_score": keyword_score,
                        "final_score": final_score,
                        "score_breakdown": {
                            "semantic": round(semantic_score, 4),
                            "keyword": round(keyword_score, 4),
                        },
                    })
            except Exception:
                continue  # Skip failed collections

        # Sort by final score and deduplicate
        all_results.sort(key=lambda x: x["final_score"], reverse=True)

        seen_ids = set()
        unique_results = []
        for r in all_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)
                if len(unique_results) >= top_k:
                    break

        return unique_results

    @classmethod
    def get_instance(cls) -> "HybridSearchService":
        """Get singleton instance."""
        global _instance
        if _instance is None:
            settings = get_settings()
            vector_store = ChromaVectorStore.get_instance()
            embedding_service = OllamaEmbeddingService()
            _instance = cls(
                vector_store=vector_store,
                embedding_service=embedding_service,
                semantic_weight=settings.search_semantic_weight,
                keyword_weight=settings.search_keyword_weight,
            )
        return _instance
