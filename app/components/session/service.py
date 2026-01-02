import json
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.components.base.component import BaseComponent
from app.components.base.config import get_settings
from app.components.base.exceptions import SessionNotFoundError
from .models import SessionCreateRequest, SessionResponse, SessionAuditResponse


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

        date_folder = now.strftime("%Y-%m-%d")
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
