"""Service for processing file-based pipeline input."""

import json
import secrets
from pathlib import Path
from datetime import datetime

from app.components.base.config import get_settings
from app.components.base.exceptions import ComponentError
from app.rag.vector_store import ChromaVectorStore
from app.components.orchestrator.service import OrchestratorService, PipelineRequest
from .models import FileInputContent, FileProcessingResponse


class FileInputService:
    """Service for file-based pipeline execution."""

    # Allowed input directory (relative to backend root)
    ALLOWED_INPUT_DIR = "input"

    # Required ChromaDB collections for pipeline to work
    REQUIRED_COLLECTIONS = ["epics", "estimations", "tdds", "stories", "gitlab_code"]

    def __init__(self):
        self.settings = get_settings()
        self._orchestrator: OrchestratorService | None = None

    @property
    def orchestrator(self) -> OrchestratorService:
        """Lazy-load orchestrator service."""
        if self._orchestrator is None:
            self._orchestrator = OrchestratorService()
        return self._orchestrator

    def _get_backend_root(self) -> Path:
        """Get the backend root directory."""
        # This file is at app/components/file_input/service.py
        # Backend root is 4 levels up
        return Path(__file__).parent.parent.parent.parent

    def _validate_file_path(self, file_path: str) -> Path:
        """Validate file path is within allowed directory and exists."""
        backend_root = self._get_backend_root()

        # Resolve the full path
        full_path = (backend_root / file_path).resolve()

        # Security: Ensure path is within allowed input directory
        allowed_dir = (backend_root / self.ALLOWED_INPUT_DIR).resolve()
        if not str(full_path).startswith(str(allowed_dir)):
            raise ComponentError(
                f"File path must be within '{self.ALLOWED_INPUT_DIR}/' directory",
                component="file_input",
                details={"file_path": file_path, "allowed_dir": self.ALLOWED_INPUT_DIR}
            )

        # Check file exists
        if not full_path.exists():
            raise ComponentError(
                f"File not found: {file_path}",
                component="file_input",
                details={"file_path": file_path}
            )

        if not full_path.is_file():
            raise ComponentError(
                f"Path is not a file: {file_path}",
                component="file_input",
                details={"file_path": file_path}
            )

        return full_path

    def _parse_file_content(self, file_path: Path) -> FileInputContent:
        """Parse and validate JSON content from input file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            raise ComponentError(
                f"Failed to read file: {e}",
                component="file_input",
                details={"file_path": str(file_path)}
            )

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise ComponentError(
                f"Invalid JSON format: {e.msg}",
                component="file_input",
                details={"file_path": str(file_path), "line": e.lineno, "column": e.colno}
            )

        try:
            return FileInputContent(**data)
        except Exception as e:
            raise ComponentError(
                f"Invalid file schema: {e}",
                component="file_input",
                details={"file_path": str(file_path)}
            )

    def _check_vector_db_initialized(self) -> None:
        """Verify ChromaDB has required collections with data."""
        try:
            vector_store = ChromaVectorStore.get_instance()
            existing_collections = vector_store.list_collections()
        except Exception as e:
            raise ComponentError(
                f"Failed to connect to ChromaDB: {e}",
                component="file_input",
                details={"chroma_dir": self.settings.chroma_persist_dir}
            )

        # Check if required collections exist (with prefix)
        prefix = self.settings.chroma_collection_prefix
        missing = []
        for name in self.REQUIRED_COLLECTIONS:
            full_name = f"{prefix}_{name}"
            if full_name not in existing_collections:
                missing.append(name)

        if missing:
            raise ComponentError(
                "ChromaDB not initialized. Run 'python scripts/init_vector_db.py' first.",
                component="file_input",
                details={
                    "missing_collections": missing,
                    "hint": "python scripts/init_vector_db.py"
                }
            )

    def _get_output_path(self, session_id: str) -> str:
        """Get the output directory path for a session."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"data/sessions/{date_str}/{session_id}/"

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        now = datetime.now()
        random_suffix = secrets.token_hex(3)
        return f"sess_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}_{random_suffix}"

    def _create_session_folder(self, session_id: str) -> Path:
        """Create the session folder and return its path."""
        date_folder = datetime.now().strftime("%Y-%m-%d-%H%M")
        session_dir = Path(self.settings.data_sessions_path) / date_folder / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save initial session metadata
        metadata = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "created",
        }
        with open(session_dir / "session_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return session_dir

    async def process_file(self, file_path: str) -> FileProcessingResponse:
        """Process an input file through the full pipeline.

        Args:
            file_path: Relative path to input file (e.g., 'input/new_req.txt')

        Returns:
            FileProcessingResponse with session info and output path

        Raises:
            ComponentError: If file validation, DB check, or pipeline fails
        """
        # Step 1: Validate file path (security + existence)
        validated_path = self._validate_file_path(file_path)

        # Step 2: Parse and validate JSON content
        content = self._parse_file_content(validated_path)

        # Step 3: Verify ChromaDB is initialized
        self._check_vector_db_initialized()

        # Step 4: Generate session_id if not provided
        session_id = content.session_id or self._generate_session_id()

        # Step 5: Create session folder
        self._create_session_folder(session_id)

        # Step 6: Build pipeline request
        request = PipelineRequest(
            session_id=session_id,
            requirement_text=content.requirement_text,
            jira_epic_id=content.jira_epic_id,
            selected_matches=content.selected_matches,
        )

        # Step 7: Run the pipeline
        try:
            response = await self.orchestrator.process(request)
        except Exception as e:
            return FileProcessingResponse(
                session_id=session_id,
                status="failed",
                output_path=self._get_output_path(session_id),
                message="Pipeline execution failed",
                error_message=str(e)
            )

        # Step 8: Return result
        output_path = self._get_output_path(session_id)

        return FileProcessingResponse(
            session_id=response.session_id,
            status=response.status,
            output_path=output_path,
            message=f"Pipeline completed with status: {response.status}",
            error_message=response.error_message
        )
