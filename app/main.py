from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.components.base.config import get_settings
from app.components.base.logging import configure_logging, get_logger
from app.components.session.router import router as session_router
from app.components.requirement.router import router as requirement_router
from app.components.historical_match.router import router as historical_match_router
from app.components.impacted_modules.router import router as impacted_modules_router
from app.components.estimation_effort.router import router as estimation_effort_router
from app.components.tdd.router import router as tdd_router
from app.components.jira_stories.router import router as jira_stories_router
from app.components.code_impact.router import router as code_router
from app.components.risks.router import router as risks_router
from app.components.orchestrator.router import router as orchestrator_router
from app.components.file_input.router import router as file_input_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    configure_logging(settings.environment)
    logger = get_logger("main")

    logger.info("Starting AI Impact Assessment API", version=settings.app_version)

    # Initialize ChromaDB connection
    from app.rag.vector_store import ChromaVectorStore

    ChromaVectorStore.initialize(settings.chroma_persist_dir)
    logger.info("ChromaDB initialized", persist_dir=settings.chroma_persist_dir)

    # Verify Ollama connection (non-blocking)
    from app.utils.ollama_client import OllamaClient

    ollama_ok = await OllamaClient.verify_connection()
    if ollama_ok:
        logger.info("Ollama connection verified")
    else:
        logger.warning("Ollama not available - LLM features will fail")

    yield

    logger.info("Shutting down AI Impact Assessment API")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount component routers
app.include_router(session_router, prefix="/api/v1")
app.include_router(requirement_router, prefix="/api/v1")
app.include_router(historical_match_router, prefix="/api/v1")
app.include_router(impacted_modules_router, prefix="/api/v1")
app.include_router(estimation_effort_router, prefix="/api/v1")
app.include_router(tdd_router, prefix="/api/v1")
app.include_router(jira_stories_router, prefix="/api/v1")
app.include_router(code_router, prefix="/api/v1")
app.include_router(risks_router, prefix="/api/v1")
app.include_router(orchestrator_router, prefix="/api/v1")
app.include_router(file_input_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    from app.utils.ollama_client import OllamaClient

    ollama_ok = await OllamaClient.verify_connection()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "ollama": "connected" if ollama_ok else "unavailable",
    }


@app.get("/api/v1/config")
async def get_config():
    """Get current configuration (non-sensitive)."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "ollama_gen_model": settings.ollama_gen_model,
        "ollama_embed_model": settings.ollama_embed_model,
        "search_semantic_weight": settings.search_semantic_weight,
        "search_keyword_weight": settings.search_keyword_weight,
    }


@app.get("/api/v1/samples/requirement")
async def get_sample_requirement():
    """Get sample requirement data for testing."""
    import json
    from pathlib import Path

    sample_path = Path("data/input/new_req.txt")
    if sample_path.exists():
        try:
            content = json.loads(sample_path.read_text())
            return {
                "requirement_text": content.get("requirement_text", ""),
                "jira_epic_id": content.get("jira_epic_id", ""),
            }
        except Exception:
            pass

    # Fallback sample data
    return {
        "requirement_text": "Refactor the legacy SOAP-based Customer API to a RESTful microservices architecture. The new API should support JSON payloads, implement OAuth 2.0 authentication, use pagination for large datasets, and include comprehensive OpenAPI documentation.",
        "jira_epic_id": "SDLC-5001",
    }
