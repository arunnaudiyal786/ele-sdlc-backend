from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Centralized configuration for all components."""

    # Application
    app_name: str = "AI Impact Assessment System"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_gen_model: str = "phi3:mini"
    ollama_embed_model: str = "all-minilm"
    ollama_timeout_seconds: int = 120
    ollama_temperature: float = 0.3
    ollama_max_tokens: int = 2048

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_prefix: str = "impact_assessment"

    # Search
    search_semantic_weight: float = 0.70
    search_keyword_weight: float = 0.30
    search_max_results: int = 10
    search_min_score_threshold: float = 0.3

    # Paths
    data_raw_path: str = "./data/raw"
    data_uploads_path: str = "./data/uploads"
    data_sessions_path: str = "./sessions"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance."""
    return Settings()
