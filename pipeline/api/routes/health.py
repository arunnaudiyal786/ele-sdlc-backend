"""
Health check endpoint for the pipeline API.
"""

import shutil
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from pipeline import __version__
from pipeline.core.config import get_pipeline_settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Check pipeline health status.

    Returns:
        Health status including Ollama availability and disk space
    """
    settings = get_pipeline_settings()

    # Check Ollama status
    ollama_status = "unavailable"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            if response.status_code == 200:
                ollama_status = "available"
    except Exception:
        pass

    # Check disk space
    disk_space_mb = None
    try:
        total, used, free = shutil.disk_usage(settings.jobs_path)
        disk_space_mb = round(free / (1024 * 1024), 2)
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": __version__,
        "ollama_status": ollama_status,
        "disk_space_mb": disk_space_mb,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
