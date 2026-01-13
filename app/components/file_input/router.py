"""FastAPI router for file-based input processing."""

from fastapi import APIRouter, HTTPException
from app.components.base.exceptions import ComponentError
from .service import FileInputService
from .models import FileInputRequest, FileProcessingResponse

router = APIRouter(prefix="/impact", tags=["File Input"])

_service: FileInputService | None = None


def get_service() -> FileInputService:
    """Get or create singleton service instance."""
    global _service
    if _service is None:
        _service = FileInputService()
    return _service


@router.post("/process-file", response_model=FileProcessingResponse)
async def process_file(request: FileInputRequest) -> FileProcessingResponse:
    """Process an input file through the impact assessment pipeline.

    This endpoint reads a JSON-formatted input file from the `input/` directory
    and runs it through the full LangGraph multi-agent pipeline.

    **Input File Format (JSON):**
    ```json
    {
        "requirement_text": "Description of the requirement...",
        "jira_epic_id": "PROJ-123",  // optional
        "selected_matches": [],      // empty = auto-select top 5
        "session_id": "my-session"   // optional, auto-generated if omitted
    }
    ```

    **Example Request:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/impact/process-file \\
      -H "Content-Type: application/json" \\
      -d '{"file_path": "input/new_req.txt"}'
    ```

    **Response:**
    - `session_id`: Auto-generated or provided session identifier
    - `status`: Pipeline completion status (completed/failed)
    - `output_path`: Path to session output directory
    - `message`: Human-readable status message

    **Error Codes:**
    - 400: Invalid file path, JSON format, or schema
    - 404: File not found
    - 503: ChromaDB not initialized
    """
    service = get_service()

    try:
        result = await service.process_file(request.file_path)
        return result
    except ComponentError as e:
        # Map specific errors to appropriate HTTP status codes
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=e.to_dict())
        elif "chromadb not initialized" in str(e).lower():
            raise HTTPException(status_code=503, detail=e.to_dict())
        else:
            raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )
