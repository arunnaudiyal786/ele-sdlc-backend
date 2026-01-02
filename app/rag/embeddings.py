import re
from typing import List
from app.utils.ollama_client import get_ollama_client


class OllamaEmbeddingService:
    """Generate embeddings using Ollama all-minilm model."""

    def __init__(self):
        self.client = get_ollama_client()

    def preprocess(self, text: str) -> str:
        """Lowercase, normalize whitespace, truncate to ~512 tokens."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        words = text.split()[:400]  # Rough token limit
        return " ".join(words)

    async def embed(self, text: str) -> List[float]:
        """Generate 384-dim embedding vector."""
        processed = self.preprocess(text)
        return await self.client.embed(processed)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding for efficiency."""
        processed = [self.preprocess(t) for t in texts]
        return await self.client.embed_batch(processed)
