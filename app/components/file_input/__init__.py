"""File input processing component for file-based pipeline execution."""

from .service import FileInputService
from .router import router

__all__ = ["FileInputService", "router"]
