"""
Data Engineering Pipeline - FastAPI Application

A separate FastAPI application for processing source documents
(DOCX, XLSX) into structured CSV files for the AI Impact Assessment System.

Runs on port 8001, separate from the main assessment API on port 8000.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline import __version__
from pipeline.core.config import get_pipeline_settings
from pipeline.services.job_tracker import get_job_tracker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_pipeline_settings()

    # Initialize job tracker (creates directories if needed)
    job_tracker = get_job_tracker()

    # Ensure data directories exist
    settings.get_jobs_path()
    settings.get_inbox_path()
    settings.get_output_path()

    print(f"Data Engineering Pipeline v{__version__} starting...")
    print(f"Jobs directory: {settings.jobs_path}")
    print(f"Batch inbox: {settings.inbox_path}")
    print(f"Output directory: {settings.output_path}")

    yield

    # Shutdown
    print("Data Engineering Pipeline shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Data Engineering Pipeline",
    description="Transforms source documents (DOCX, XLSX) into structured CSV files for the AI Impact Assessment System",
    version=__version__,
    lifespan=lifespan,
)

# Configure CORS
settings = get_pipeline_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import and include routers
from pipeline.api.routes.health import router as health_router
from pipeline.api.routes.upload import router as upload_router
from pipeline.api.routes.extract import router as extract_router
from pipeline.api.routes.transform import router as transform_router
from pipeline.api.routes.preview import router as preview_router
from pipeline.api.routes.export import router as export_router
from pipeline.api.routes.batch import router as batch_router

app.include_router(health_router, prefix="/api/v1/pipeline", tags=["health"])
app.include_router(upload_router, prefix="/api/v1/pipeline", tags=["upload"])
app.include_router(extract_router, prefix="/api/v1/pipeline", tags=["extract"])
app.include_router(transform_router, prefix="/api/v1/pipeline", tags=["transform"])
app.include_router(preview_router, prefix="/api/v1/pipeline", tags=["preview"])
app.include_router(export_router, prefix="/api/v1/pipeline", tags=["export"])
app.include_router(batch_router, prefix="/api/v1/pipeline", tags=["batch"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Data Engineering Pipeline",
        "version": __version__,
        "description": "Transforms source documents into structured CSV files",
        "docs_url": "/docs",
        "health_url": "/api/v1/pipeline/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "pipeline.main:app",
        host="0.0.0.0",
        port=settings.pipeline_port,
        reload=True,
    )
