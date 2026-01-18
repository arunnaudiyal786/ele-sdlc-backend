import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.components.base.component import BaseComponent
from app.components.base.config import get_settings
from app.components.base.exceptions import SessionNotFoundError
from .models import (
    SessionCreateRequest,
    SessionResponse,
    SessionAuditResponse,
    SessionSummaryItem,
    SessionListResponse,
)


class SessionService(BaseComponent[SessionCreateRequest, SessionResponse]):
    """Session lifecycle management as a component."""

    def __init__(self):
        self.config = get_settings()
        self.sessions_path = Path(self.config.data_sessions_path)

    @property
    def component_name(self) -> str:
        return "session"

    async def process(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new session."""
        now = datetime.now()
        random_suffix = secrets.token_hex(3)
        session_id = f"sess_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}_{random_suffix}"

        date_folder = now.strftime("%Y-%m-%d-%H%M")
        session_dir = self.sessions_path / date_folder / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "session_id": session_id,
            "created_at": now.isoformat(),
            "status": "created",
            "user_id": request.user_id,
            "steps_completed": [],
            "timing": {},
        }
        self._save_metadata(session_dir, metadata)

        return SessionResponse(
            session_id=session_id,
            created_at=now,
            status="created",
            audit_path=str(session_dir),
            user_id=request.user_id,
        )

    async def get_session(self, session_id: str) -> SessionResponse:
        """Retrieve session by ID."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            raise SessionNotFoundError(f"Session {session_id} not found", component="session")
        metadata = self._load_metadata(session_dir)
        return SessionResponse(
            session_id=metadata["session_id"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            status=metadata["status"],
            audit_path=str(session_dir),
            user_id=metadata.get("user_id"),
        )

    async def get_audit(self, session_id: str) -> SessionAuditResponse:
        """Get full audit trail for a session."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            raise SessionNotFoundError(f"Session {session_id} not found", component="session")
        metadata = self._load_metadata(session_dir)
        return SessionAuditResponse(
            session_id=metadata["session_id"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            status=metadata["status"],
            steps_completed=metadata.get("steps_completed", []),
            timing=metadata.get("timing", {}),
            data=metadata,
        )

    async def update_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        session_dir = self._find_session_dir(session_id)
        if not session_dir:
            raise SessionNotFoundError(f"Session {session_id} not found", component="session")
        metadata = self._load_metadata(session_dir)
        metadata["status"] = status
        self._save_metadata(session_dir, metadata)

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> SessionListResponse:
        """List all sessions with summaries, sorted by created_at descending."""
        all_sessions: list[SessionSummaryItem] = []

        if not self.sessions_path.exists():
            return SessionListResponse(sessions=[], total=0, limit=limit, offset=offset)

        # Iterate through all date folders and session folders
        for date_folder in self.sessions_path.iterdir():
            if not date_folder.is_dir():
                continue
            for session_dir in date_folder.iterdir():
                if not session_dir.is_dir():
                    continue
                metadata_file = session_dir / "session_metadata.json"
                if not metadata_file.exists():
                    continue

                try:
                    metadata = self._load_metadata(session_dir)
                    # Ensure required fields exist with fallbacks
                    metadata = self._ensure_metadata_fields(session_dir, metadata)
                    summary = self._build_session_summary(session_dir, metadata)
                    all_sessions.append(summary)
                except (json.JSONDecodeError, KeyError) as e:
                    # Log but skip corrupted sessions
                    print(f"Skipping session {session_dir.name}: {e}")
                    continue

        # Sort by created_at descending (newest first)
        all_sessions.sort(key=lambda s: s.created_at, reverse=True)

        # Apply pagination
        total = len(all_sessions)
        paginated = all_sessions[offset : offset + limit]

        return SessionListResponse(
            sessions=paginated,
            total=total,
            limit=limit,
            offset=offset,
        )

    def _build_session_summary(
        self, session_dir: Path, metadata: dict
    ) -> SessionSummaryItem:
        """Build a session summary from metadata and optional final_summary."""
        requirement_text = None
        jira_epic_id = None
        total_story_points = None
        total_hours = None

        # Try to load requirement text from step1_input
        req_file = session_dir / "step1_input" / "requirement.json"
        if req_file.exists():
            try:
                with open(req_file) as f:
                    req_data = json.load(f)
                    full_text = req_data.get("requirement_text", "")
                    # Truncate to 200 chars
                    requirement_text = full_text[:200] + "..." if len(full_text) > 200 else full_text
                    jira_epic_id = req_data.get("jira_epic_id")
            except (json.JSONDecodeError, KeyError):
                pass

        # Try to load metrics from final_summary
        summary_file = session_dir / "final_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file) as f:
                    summary_data = json.load(f)
                    # Extract story points - check both key formats for compatibility
                    jira_output = (
                        summary_data.get("jira_stories_output")
                        or summary_data.get("jira_stories")
                        or {}
                    )
                    total_story_points = jira_output.get("total_story_points")
                    # Extract hours - check both key formats for compatibility
                    estimation_output = (
                        summary_data.get("estimation_effort_output")
                        or summary_data.get("estimation_effort")
                        or {}
                    )
                    total_hours = estimation_output.get("total_hours")
            except (json.JSONDecodeError, KeyError):
                pass

        return SessionSummaryItem(
            session_id=metadata["session_id"],
            created_at=datetime.fromisoformat(metadata["created_at"]),
            status=metadata.get("status", "unknown"),
            requirement_text=requirement_text,
            jira_epic_id=jira_epic_id,
            total_story_points=total_story_points,
            total_hours=total_hours,
        )

    def _ensure_metadata_fields(self, session_dir: Path, metadata: dict) -> dict:
        """Ensure required metadata fields exist with fallbacks."""
        # Fallback session_id to directory name
        if "session_id" not in metadata:
            metadata["session_id"] = session_dir.name

        # Fallback created_at to file modification time or parse from date folder
        if "created_at" not in metadata:
            metadata_file = session_dir / "session_metadata.json"
            if metadata_file.exists():
                # Use file modification time as fallback
                mtime = metadata_file.stat().st_mtime
                metadata["created_at"] = datetime.fromtimestamp(mtime).isoformat()
            else:
                # Parse from parent folder name (format: YYYY-MM-DD-HHMM)
                try:
                    date_folder_name = session_dir.parent.name
                    parsed_date = datetime.strptime(date_folder_name, "%Y-%m-%d-%H%M")
                    metadata["created_at"] = parsed_date.isoformat()
                except ValueError:
                    metadata["created_at"] = datetime.now().isoformat()

        # Ensure status has a default
        if "status" not in metadata:
            metadata["status"] = "unknown"

        return metadata

    def _find_session_dir(self, session_id: str) -> Optional[Path]:
        """Find session directory by ID."""
        for date_folder in self.sessions_path.iterdir():
            if date_folder.is_dir():
                session_dir = date_folder / session_id
                if session_dir.exists():
                    return session_dir
        return None

    def _save_metadata(self, session_dir: Path, metadata: dict) -> None:
        """Save session metadata."""
        with open(session_dir / "session_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    def _load_metadata(self, session_dir: Path) -> dict:
        """Load session metadata."""
        with open(session_dir / "session_metadata.json") as f:
            return json.load(f)
