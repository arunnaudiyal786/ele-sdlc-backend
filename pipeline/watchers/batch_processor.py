"""
Batch processor for automated document processing.

Processes file sets from the inbox directory through the full pipeline.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pipeline.core.config import get_pipeline_settings
from pipeline.models.pipeline_job import JobStatus
from pipeline.services.job_tracker import get_job_tracker

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes batches of documents through the pipeline.

    Groups files by project prefix and processes each group
    as a single job through extraction, transformation, validation,
    and export.
    """

    def __init__(self):
        """Initialize the batch processor."""
        self.settings = get_pipeline_settings()
        self._processing_queue: asyncio.Queue[Path] = asyncio.Queue()
        self._active_jobs: Set[str] = set()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def enqueue_file(self, file_path: Path) -> None:
        """
        Add a file to the processing queue.

        Args:
            file_path: Path to the file to process
        """
        await self._processing_queue.put(file_path)
        logger.debug(f"Enqueued file: {file_path.name}")

    async def start(self) -> None:
        """Start the batch processor."""
        if self._running:
            logger.warning("Batch processor already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._process_loop())
        logger.info("Batch processor started")

    async def stop(self) -> None:
        """Stop the batch processor."""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        logger.info("Batch processor stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        pending_files: Dict[str, Dict[str, Path]] = {}
        last_check = datetime.now(timezone.utc)

        while self._running:
            try:
                # Check for new files (with timeout to allow periodic processing)
                try:
                    file_path = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=5.0,
                    )

                    # Group files by project prefix
                    project, doc_type = self._classify_file(file_path)

                    if project not in pending_files:
                        pending_files[project] = {}

                    pending_files[project][doc_type] = file_path
                    logger.info(f"File grouped: {file_path.name} -> {project}/{doc_type}")

                except asyncio.TimeoutError:
                    pass

                # Check if any file groups are ready to process
                now = datetime.now(timezone.utc)
                if (now - last_check).total_seconds() >= 10:
                    last_check = now

                    ready_projects = []
                    for project, files in pending_files.items():
                        # Must have estimation file to process
                        if "estimation" in files:
                            ready_projects.append(project)

                    for project in ready_projects:
                        files = pending_files.pop(project)
                        asyncio.create_task(self._process_file_group(project, files))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)

    def _classify_file(self, file_path: Path) -> tuple[str, str]:
        """
        Classify a file by project prefix and document type.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (project_prefix, document_type)
        """
        filename = file_path.name.lower()
        stem = file_path.stem.lower()
        suffix = file_path.suffix.lower()

        # Extract project prefix
        project_prefix = stem
        doc_type = "unknown"

        # Check for document type markers
        type_markers = {
            "epic": ["_epic", "epic_", "-epic"],
            "estimation": ["_estimation", "estimation_", "-estimation", "_estimate", "estimate_"],
            "tdd": ["_tdd", "tdd_", "-tdd"],
            "story": ["_stories", "stories_", "_story", "story_", "-stories", "-story"],
        }

        for doc, markers in type_markers.items():
            for marker in markers:
                if marker in filename:
                    # Extract prefix (everything before the marker)
                    idx = stem.find(marker.replace("_", "").replace("-", ""))
                    if idx > 0:
                        project_prefix = stem[:idx]
                    doc_type = doc
                    break
            if doc_type != "unknown":
                break

        # If still unknown, infer from extension
        if doc_type == "unknown":
            if suffix in [".xlsx", ".xls"]:
                doc_type = "estimation"
            elif "epic" in stem:
                doc_type = "epic"
            elif "tdd" in stem:
                doc_type = "tdd"
            elif "stor" in stem:
                doc_type = "story"

        return project_prefix, doc_type

    async def _process_file_group(
        self,
        project: str,
        files: Dict[str, Path],
    ) -> None:
        """
        Process a group of related files as a single job.

        Args:
            project: Project prefix
            files: Dict mapping document types to file paths
        """
        job_tracker = get_job_tracker()

        logger.info(f"Processing file group for project: {project}")

        try:
            # Create new job
            job_id = await job_tracker.create_job(job_type="batch")
            self._active_jobs.add(job_id)

            # Move files to processing directory
            processing_dir = self.settings.processing_path / job_id
            processing_dir.mkdir(parents=True, exist_ok=True)

            for doc_type, source_path in files.items():
                if doc_type == "unknown":
                    continue

                try:
                    dest_path = processing_dir / source_path.name
                    source_path.rename(dest_path)

                    await job_tracker.add_file(
                        job_id=job_id,
                        filename=source_path.name,
                        file_path=str(dest_path),
                        file_size=dest_path.stat().st_size,
                        document_type=doc_type,
                    )
                    logger.debug(f"Added file to job: {source_path.name} ({doc_type})")
                except Exception as e:
                    logger.error(f"Failed to add file {source_path.name}: {e}")

            await job_tracker.update_status(job_id, JobStatus.UPLOADED)

            # Run full pipeline
            await self._run_pipeline(job_id)

        except Exception as e:
            logger.error(f"Failed to process file group for {project}: {e}")
        finally:
            self._active_jobs.discard(job_id)

    async def _run_pipeline(self, job_id: str) -> None:
        """
        Run the full pipeline for a job.

        Args:
            job_id: Job identifier
        """
        from pipeline.api.routes.extract import extract_documents
        from pipeline.api.routes.export import export_data
        from pipeline.api.routes.preview import validate_data
        from pipeline.api.routes.transform import transform_data
        from pipeline.models.api_models import ExtractRequest

        job_tracker = get_job_tracker()

        try:
            logger.info(f"Starting pipeline for job {job_id}")

            # Step 1: Extract
            logger.debug(f"[{job_id}] Running extraction...")
            await extract_documents(job_id, ExtractRequest(use_llm_enhancement=True))

            # Step 2: Apply default mappings
            job = await job_tracker.get_job(job_id)
            if job:
                current_mappings = job.mapping_results or {}
                for file_info in job.files_uploaded:
                    doc_type = file_info.document_type
                    if doc_type not in current_mappings:
                        current_mappings[doc_type] = {}
                await job_tracker.update_job(job_id, mapping_results=current_mappings)

            # Step 3: Transform
            logger.debug(f"[{job_id}] Running transformation...")
            await transform_data(job_id)

            # Step 4: Validate
            logger.debug(f"[{job_id}] Running validation...")
            await validate_data(job_id)

            # Step 5: Export
            logger.debug(f"[{job_id}] Running export...")
            await export_data(job_id)

            # Clean up processing directory
            job = await job_tracker.get_job(job_id)
            if job and job.status == JobStatus.COMPLETED:
                processing_dir = self.settings.processing_path / job_id
                if processing_dir.exists():
                    import shutil
                    shutil.rmtree(processing_dir)
                logger.info(f"Pipeline completed successfully for job {job_id}")

        except Exception as e:
            logger.error(f"Pipeline failed for job {job_id}: {e}")
            await job_tracker.update_status(job_id, JobStatus.FAILED)
            await job_tracker.update_job(job_id, error_message=str(e))

            # Move to failed directory
            processing_dir = self.settings.processing_path / job_id
            failed_dir = self.settings.failed_path / job_id
            if processing_dir.exists():
                processing_dir.rename(failed_dir)


async def run_batch_processor() -> None:
    """
    Run the batch processor as a standalone service.

    This combines the folder watcher and batch processor
    into a single entry point for batch mode.
    """
    from pipeline.watchers.folder_watcher import PipelineFolderWatcher

    processor = BatchProcessor()

    async def on_file_ready(file_path: Path) -> None:
        await processor.enqueue_file(file_path)

    watcher = PipelineFolderWatcher(on_file_ready=on_file_ready)

    try:
        # Start both components
        await processor.start()
        watcher.start()

        logger.info("Batch mode running. Watching for files...")

        # Run until interrupted
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Batch mode shutting down...")
    finally:
        watcher.stop()
        await processor.stop()


if __name__ == "__main__":
    # Allow running batch processor directly
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(run_batch_processor())
