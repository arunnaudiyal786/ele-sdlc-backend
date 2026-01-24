import httpx
from typing import Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from app.components.base.config import get_settings
from app.components.base.exceptions import OllamaUnavailableError, OllamaTimeoutError

_client: Optional["OllamaClient"] = None


@dataclass
class LLMRequestMetadata:
    """Complete metadata for an LLM request to Ollama."""
    model: str
    system_prompt: Optional[str]
    user_prompt: str
    temperature: float
    max_tokens: int
    format: Optional[str]
    timeout: int
    base_url: str
    stream: bool
    timestamp: str  # ISO 8601 format

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class OllamaClient:
    """Async client for Ollama API (generation + embedding)."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.gen_model = settings.ollama_gen_model
        self.embed_model = settings.ollama_embed_model
        self.timeout = settings.ollama_timeout_seconds
        self.temperature = settings.ollama_temperature
        self.max_tokens = settings.ollama_max_tokens

    async def generate(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        format: Optional[str] = None,
    ) -> Tuple[str, LLMRequestMetadata]:
        """Generate text using Ollama and return response with request metadata."""
        # Create metadata before request
        metadata = LLMRequestMetadata(
            model=self.gen_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            format=format,
            timeout=self.timeout,
            base_url=self.base_url,
            stream=False,
            timestamp=datetime.now().isoformat(),
        )

        payload = {
            "model": self.gen_model,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if format == "json":
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate", json=payload
                )
                response.raise_for_status()
                return response.json().get("response", ""), metadata
        except httpx.TimeoutException:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout}s", component="ollama"
            )
        except httpx.HTTPError as e:
            raise OllamaUnavailableError(f"Ollama unavailable: {e}", component="ollama")

    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        payload = {"model": self.embed_model, "prompt": text}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings", json=payload
                )
                response.raise_for_status()
                return response.json().get("embedding", [])
        except httpx.HTTPError as e:
            raise OllamaUnavailableError(
                f"Embedding failed: {e}", component="ollama"
            )

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embedding for multiple texts."""
        return [await self.embed(text) for text in texts]

    @classmethod
    async def verify_connection(cls) -> bool:
        """Verify Ollama is accessible."""
        settings = get_settings()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


def get_ollama_client() -> OllamaClient:
    """Get singleton OllamaClient instance."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
