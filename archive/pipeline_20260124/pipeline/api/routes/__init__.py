"""API route modules for the data engineering pipeline."""

from pipeline.api.routes.health import router as health_router
from pipeline.api.routes.upload import router as upload_router
from pipeline.api.routes.extract import router as extract_router
from pipeline.api.routes.transform import router as transform_router
from pipeline.api.routes.preview import router as preview_router
from pipeline.api.routes.export import router as export_router
from pipeline.api.routes.batch import router as batch_router

__all__ = [
    "health_router",
    "upload_router",
    "extract_router",
    "transform_router",
    "preview_router",
    "export_router",
    "batch_router",
]
