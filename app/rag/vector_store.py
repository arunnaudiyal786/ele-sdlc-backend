import chromadb
from typing import List, Dict, Optional, Any
from chromadb.config import Settings as ChromaSettings
from app.components.base.config import get_settings
from app.components.base.exceptions import VectorDBError

_instance: Optional["ChromaVectorStore"] = None


class ChromaVectorStore:
    """ChromaDB operations for all collections."""

    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Get or create a collection."""
        settings = get_settings()
        full_name = f"{settings.chroma_collection_prefix}_{name}"
        return self.client.get_or_create_collection(
            name=full_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Add documents with embeddings and metadata."""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                ids=[d["id"] for d in documents],
                embeddings=embeddings,
                documents=[d["text"] for d in documents],
                metadatas=[d.get("metadata", {}) for d in documents],
            )
        except Exception as e:
            raise VectorDBError(f"Failed to add documents: {e}", component="vector_store")

    async def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Semantic search with optional metadata filtering."""
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            matches = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    matches.append({
                        "id": doc_id,
                        "text": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                    })
            return matches
        except Exception as e:
            raise VectorDBError(f"Search failed: {e}", component="vector_store")

    async def delete_collection(self, name: str) -> None:
        """Delete a collection for reindexing."""
        settings = get_settings()
        full_name = f"{settings.chroma_collection_prefix}_{name}"
        try:
            self.client.delete_collection(full_name)
        except Exception:
            pass  # Collection may not exist

    def list_collections(self) -> List[str]:
        """List all collections."""
        return [c.name for c in self.client.list_collections()]

    @classmethod
    def initialize(cls, persist_dir: str) -> "ChromaVectorStore":
        """Initialize singleton instance."""
        global _instance
        if _instance is None:
            _instance = cls(persist_dir)
        return _instance

    @classmethod
    def get_instance(cls) -> "ChromaVectorStore":
        """Get singleton instance."""
        global _instance
        if _instance is None:
            settings = get_settings()
            _instance = cls(settings.chroma_persist_dir)
        return _instance
