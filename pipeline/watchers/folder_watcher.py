"""
Folder watcher for batch mode document processing.

Monitors the inbox directory for new files and triggers processing.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pipeline.core.config import get_pipeline_settings

logger = logging.getLogger(__name__)


class PipelineEventHandler(FileSystemEventHandler):
    """
    Event handler for file system events in the pipeline inbox.

    Tracks new files and triggers processing when a complete file set
    appears to be ready (based on file stability).
    """

    def __init__(
        self,
        callback: Callable[[Path], None],
        stability_seconds: float = 2.0,
    ):
        """
        Initialize the event handler.

        Args:
            callback: Function to call when a new file is stable
            stability_seconds: Seconds to wait before considering a file stable
        """
        super().__init__()
        self.callback = callback
        self.stability_seconds = stability_seconds
        self._pending_files: Set[Path] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process supported file types
        if file_path.suffix.lower() not in [".xlsx", ".xls", ".docx"]:
            return

        logger.info(f"New file detected: {file_path.name}")
        self._pending_files.add(file_path)

        # Schedule stability check
        if self._loop:
            self._loop.call_later(
                self.stability_seconds,
                self._check_file_stability,
                file_path,
            )

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events (reset stability timer)."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path in self._pending_files:
            # File still being written, re-add to pending
            logger.debug(f"File modified, resetting stability timer: {file_path.name}")

    def _check_file_stability(self, file_path: Path) -> None:
        """Check if file is stable and trigger callback."""
        if file_path not in self._pending_files:
            return

        if not file_path.exists():
            self._pending_files.discard(file_path)
            return

        # Check if file size has stabilized
        try:
            initial_size = file_path.stat().st_size
            # Small delay to verify
            import time
            time.sleep(0.1)

            if file_path.exists() and file_path.stat().st_size == initial_size:
                self._pending_files.discard(file_path)
                logger.info(f"File stable, triggering processing: {file_path.name}")
                self.callback(file_path)
            else:
                # File still changing, reschedule
                if self._loop:
                    self._loop.call_later(
                        self.stability_seconds,
                        self._check_file_stability,
                        file_path,
                    )
        except OSError:
            self._pending_files.discard(file_path)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for scheduling callbacks."""
        self._loop = loop


class PipelineFolderWatcher:
    """
    Watches the pipeline inbox directory for new files.

    When files are detected, they are queued for batch processing.
    """

    def __init__(
        self,
        inbox_path: Optional[Path] = None,
        on_file_ready: Optional[Callable[[Path], None]] = None,
    ):
        """
        Initialize the folder watcher.

        Args:
            inbox_path: Directory to watch (defaults to settings.inbox_path)
            on_file_ready: Callback when a file is ready for processing
        """
        settings = get_pipeline_settings()
        self.inbox_path = inbox_path or settings.inbox_path
        self.on_file_ready = on_file_ready or self._default_file_handler

        self._observer: Optional[Observer] = None
        self._event_handler: Optional[PipelineEventHandler] = None
        self._running = False

    def _default_file_handler(self, file_path: Path) -> None:
        """Default handler that logs the file."""
        logger.info(f"File ready for processing: {file_path}")

    def start(self) -> None:
        """Start watching the inbox directory."""
        if self._running:
            logger.warning("Folder watcher already running")
            return

        # Ensure inbox exists
        self.inbox_path.mkdir(parents=True, exist_ok=True)

        # Create event handler
        self._event_handler = PipelineEventHandler(
            callback=self.on_file_ready,
        )

        # Try to set event loop
        try:
            loop = asyncio.get_running_loop()
            self._event_handler.set_event_loop(loop)
        except RuntimeError:
            pass

        # Create and start observer
        self._observer = Observer()
        self._observer.schedule(
            self._event_handler,
            str(self.inbox_path),
            recursive=False,
        )
        self._observer.start()
        self._running = True

        logger.info(f"Folder watcher started: {self.inbox_path}")

    def stop(self) -> None:
        """Stop watching the inbox directory."""
        if not self._running:
            return

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        self._event_handler = None
        self._running = False

        logger.info("Folder watcher stopped")

    @property
    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running

    def __enter__(self) -> "PipelineFolderWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


async def run_folder_watcher(
    on_file_ready: Optional[Callable[[Path], None]] = None,
) -> None:
    """
    Run the folder watcher as an async task.

    This is the main entry point for running the watcher in batch mode.

    Args:
        on_file_ready: Callback when a file is ready for processing
    """
    settings = get_pipeline_settings()

    watcher = PipelineFolderWatcher(
        inbox_path=settings.inbox_path,
        on_file_ready=on_file_ready,
    )

    try:
        watcher.start()
        logger.info(f"Watching {settings.inbox_path} for new files...")

        # Keep running until interrupted
        while watcher.is_running:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Folder watcher cancelled")
    finally:
        watcher.stop()
