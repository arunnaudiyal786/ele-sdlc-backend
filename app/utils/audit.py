import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from app.components.base.config import get_settings


class AuditTrailManager:
    """Manages session audit trail persistence."""

    session_dir: Path  # Always set after __init__

    def __init__(self, session_id: str):
        self.session_id = session_id
        settings = get_settings()
        sessions_path = Path(settings.data_sessions_path)

        # Find existing session folder instead of creating new one
        existing_dir = self._find_session_dir(sessions_path, session_id)
        if existing_dir:
            self.session_dir = existing_dir
        else:
            # Fallback: create new folder if session not found
            date_folder = datetime.now().strftime("%Y-%m-%d-%H%M")
            self.session_dir = sessions_path / date_folder / session_id
            self.session_dir.mkdir(parents=True, exist_ok=True)

    def _find_session_dir(self, sessions_path: Path, session_id: str) -> Optional[Path]:
        """Find existing session directory by ID."""
        if not sessions_path.exists():
            return None
        for date_folder in sessions_path.iterdir():
            if date_folder.is_dir():
                session_dir = date_folder / session_id
                if session_dir.exists():
                    return session_dir
        return None

    def save_json(self, filename: str, data: Any, subfolder: Optional[str] = None) -> Path:
        """Save data as JSON to session directory."""
        target_dir = self.session_dir / subfolder if subfolder else self.session_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath

    def save_text(self, filename: str, content: str, subfolder: Optional[str] = None) -> Path:
        """Save text content to session directory."""
        target_dir = self.session_dir / subfolder if subfolder else self.session_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def load_json(self, filename: str, subfolder: Optional[str] = None) -> Dict:
        """Load JSON from session directory."""
        target_dir = self.session_dir / subfolder if subfolder else self.session_dir
        filepath = target_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return {}

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update session_metadata.json with new values."""
        metadata = self.load_json("session_metadata.json")
        metadata.update(updates)
        self.save_json("session_metadata.json", metadata)

    def record_timing(self, step_name: str, duration_ms: int) -> None:
        """Record step timing in metadata."""
        metadata = self.load_json("session_metadata.json")
        timing = metadata.get("timing", {})
        timing[step_name] = duration_ms
        metadata["timing"] = timing
        self.save_json("session_metadata.json", metadata)

    def add_step_completed(self, step_name: str) -> None:
        """Mark a step as completed."""
        metadata = self.load_json("session_metadata.json")
        steps = metadata.get("steps_completed", [])
        if step_name not in steps:
            steps.append(step_name)
        metadata["steps_completed"] = steps
        self.save_json("session_metadata.json", metadata)
