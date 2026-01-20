"""
Pipeline configuration using Pydantic settings.

Follows the same pattern as app/components/base/config.py.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class PipelineSettings(BaseSettings):
    """Configuration for the data engineering pipeline."""

    # Pipeline identification
    pipeline_name: str = "Data Engineering Pipeline"
    pipeline_version: str = "1.0.0"
    pipeline_port: int = 8001

    # Extractors
    docx_max_size_mb: int = 50
    excel_max_size_mb: int = 100
    llm_confidence_threshold: float = 0.7
    llm_model: str = "phi3:mini"
    llm_timeout: int = 120
    llm_max_retries: int = 2

    # Ollama (reuse from main app settings)
    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "all-minilm"

    # Paths
    jobs_path: str = "data/pipeline/jobs"
    inbox_path: str = "data/pipeline/inbox"
    processing_path: str = "data/pipeline/processing"
    completed_path: str = "data/pipeline/completed"
    failed_path: str = "data/pipeline/failed"
    output_path: str = "data/raw"
    backup_path: str = "data/raw/backups"

    # ID Generation
    epic_id_prefix: str = "EPIC"
    estimation_id_prefix: str = "EST"
    tdd_id_prefix: str = "TDD"
    story_id_prefix: str = "STORY"
    module_id_prefix: str = "MOD"
    id_padding: int = 3  # Number of digits: EPIC-001

    # Validation
    required_files: List[str] = ["estimation"]  # At minimum, estimation sheet required
    strict_mode: bool = False  # If True, fail on any validation warning

    # Batch Processing
    batch_enabled: bool = True
    batch_poll_interval: int = 10  # seconds
    batch_auto_map_threshold: float = 0.8  # Auto-accept mappings above this confidence

    # Export
    sync_vector_db: bool = True
    backup_existing: bool = True
    assessment_api_url: str = "http://localhost:8000"
    vector_db_reindex_endpoint: str = "/api/v1/admin/reindex"

    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    class Config:
        env_file = ".env"
        env_prefix = "PIPELINE_"
        extra = "ignore"

    def get_jobs_path(self) -> Path:
        """Get jobs directory as Path, creating if needed."""
        path = Path(self.jobs_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_inbox_path(self) -> Path:
        """Get inbox directory as Path, creating if needed."""
        path = Path(self.inbox_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_processing_path(self) -> Path:
        """Get processing directory as Path, creating if needed."""
        path = Path(self.processing_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_completed_path(self) -> Path:
        """Get completed directory as Path, creating if needed."""
        path = Path(self.completed_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_failed_path(self) -> Path:
        """Get failed directory as Path, creating if needed."""
        path = Path(self.failed_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_output_path(self) -> Path:
        """Get output (data/raw) directory as Path, creating if needed."""
        path = Path(self.output_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_backup_path(self) -> Path:
        """Get backup directory as Path, creating if needed."""
        path = Path(self.backup_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_pipeline_settings() -> PipelineSettings:
    """
    Get cached pipeline settings instance.

    Uses @lru_cache for singleton pattern consistent with main app.
    """
    return PipelineSettings()
