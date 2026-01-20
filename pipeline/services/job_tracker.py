"""
Job tracker service for managing pipeline jobs.

Handles job creation, status updates, and artifact persistence.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from pipeline.core.config import get_pipeline_settings
from pipeline.models.pipeline_job import FileInfo, JobStatus, JobStep, PipelineJob


class JobTracker:
    """
    Manages pipeline job state and artifacts.

    Jobs are stored as JSON files in data/pipeline/jobs/{job_id}/state.json
    with artifacts in subdirectories.
    """

    def __init__(self, jobs_dir: Optional[Path] = None):
        settings = get_pipeline_settings()
        self.jobs_dir = jobs_dir or settings.get_jobs_path()
        self._job_counter_file = self.jobs_dir / ".job_counter"

    async def create_job(self, job_type: str = "interactive") -> str:
        """
        Create a new pipeline job.

        Args:
            job_type: "interactive" or "batch"

        Returns:
            Generated job_id
        """
        job_id = await self._generate_job_id()

        # Create job directory structure
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "uploads").mkdir(exist_ok=True)
        (job_dir / "extracted").mkdir(exist_ok=True)
        (job_dir / "transformed").mkdir(exist_ok=True)
        (job_dir / "logs").mkdir(exist_ok=True)

        # Create initial job state
        job = PipelineJob(
            job_id=job_id,
            job_type=job_type,
            status=JobStatus.CREATED,
        )

        await self._save_job(job)
        return job_id

    async def get_job(self, job_id: str) -> Optional[PipelineJob]:
        """
        Load job state from file.

        Args:
            job_id: Job identifier

        Returns:
            PipelineJob or None if not found
        """
        state_file = self.jobs_dir / job_id / "state.json"
        if not state_file.exists():
            return None

        try:
            async with aiofiles.open(state_file, "r") as f:
                data = await f.read()
                return PipelineJob.model_validate_json(data)
        except Exception:
            return None

    async def update_job(self, job_id: str, **updates) -> Optional[PipelineJob]:
        """
        Update job state with provided fields.

        Args:
            job_id: Job identifier
            **updates: Fields to update

        Returns:
            Updated PipelineJob or None if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.updated_at = datetime.now(timezone.utc)
        await self._save_job(job)
        return job

    async def update_status(self, job_id: str, status: JobStatus) -> Optional[PipelineJob]:
        """Update job status."""
        job = await self.get_job(job_id)
        if job:
            job.update_status(status)
            await self._save_job(job)
        return job

    async def mark_step_completed(self, job_id: str, step: JobStep) -> Optional[PipelineJob]:
        """Mark a processing step as completed."""
        job = await self.get_job(job_id)
        if job:
            job.mark_step_completed(step)
            await self._save_job(job)
        return job

    async def set_error(self, job_id: str, message: str) -> Optional[PipelineJob]:
        """Set job error and mark as failed."""
        job = await self.get_job(job_id)
        if job:
            job.set_error(message)
            await self._save_job(job)
        return job

    async def add_file(
        self,
        job_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        document_type: str,
    ) -> Optional[PipelineJob]:
        """Add a file to the job's files list."""
        job = await self.get_job(job_id)
        if not job:
            return None

        file_info = FileInfo(
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            document_type=document_type,
            uploaded_at=datetime.now(timezone.utc),
        )
        job.files_uploaded.append(file_info)
        await self._save_job(job)
        return job

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PipelineJob]:
        """
        List jobs with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum jobs to return
            offset: Offset for pagination

        Returns:
            List of PipelineJob objects
        """
        jobs = []

        if not self.jobs_dir.exists():
            return jobs

        # Get all job directories sorted by name (date-based)
        job_dirs = sorted(self.jobs_dir.iterdir(), reverse=True)

        for job_dir in job_dirs:
            if not job_dir.is_dir() or job_dir.name.startswith("."):
                continue

            job = await self.get_job(job_dir.name)
            if job:
                if status is None or job.status == status:
                    jobs.append(job)

        # Apply pagination
        return jobs[offset : offset + limit]

    async def save_artifact(
        self,
        job_id: str,
        artifact_name: str,
        data: Any,
        subfolder: str = "",
    ) -> Path:
        """
        Save a job artifact (JSON serializable data).

        Args:
            job_id: Job identifier
            artifact_name: Name for the artifact file
            data: Data to save (must be JSON serializable)
            subfolder: Optional subfolder within job directory

        Returns:
            Path to saved artifact
        """
        job_dir = self.jobs_dir / job_id
        if subfolder:
            artifact_dir = job_dir / subfolder
        else:
            artifact_dir = job_dir
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Ensure .json extension
        if not artifact_name.endswith(".json"):
            artifact_name = f"{artifact_name}.json"

        artifact_path = artifact_dir / artifact_name

        async with aiofiles.open(artifact_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

        return artifact_path

    async def load_artifact(
        self,
        job_id: str,
        artifact_name: str,
        subfolder: str = "",
    ) -> Optional[Any]:
        """
        Load a job artifact.

        Args:
            job_id: Job identifier
            artifact_name: Artifact filename
            subfolder: Optional subfolder

        Returns:
            Loaded data or None if not found
        """
        job_dir = self.jobs_dir / job_id
        if subfolder:
            artifact_dir = job_dir / subfolder
        else:
            artifact_dir = job_dir

        if not artifact_name.endswith(".json"):
            artifact_name = f"{artifact_name}.json"

        artifact_path = artifact_dir / artifact_name

        if not artifact_path.exists():
            return None

        async with aiofiles.open(artifact_path, "r") as f:
            data = await f.read()
            return json.loads(data)

    def get_job_dir(self, job_id: str) -> Path:
        """Get the directory path for a job."""
        return self.jobs_dir / job_id

    def get_upload_dir(self, job_id: str) -> Path:
        """Get the upload directory for a job."""
        path = self.jobs_dir / job_id / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def _save_job(self, job: PipelineJob) -> None:
        """Save job state to file."""
        job_dir = self.jobs_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        state_file = job_dir / "state.json"

        async with aiofiles.open(state_file, "w") as f:
            await f.write(job.model_dump_json(indent=2))

    async def _generate_job_id(self) -> str:
        """Generate a unique job ID in format JOB-YYYYMMDD-NNN."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")

        # Get or initialize daily counter
        counter = 1
        if self._job_counter_file.exists():
            try:
                async with aiofiles.open(self._job_counter_file, "r") as f:
                    data = json.loads(await f.read())
                    if data.get("date") == today:
                        counter = data.get("counter", 0) + 1
            except Exception:
                pass

        # Save updated counter
        async with aiofiles.open(self._job_counter_file, "w") as f:
            await f.write(json.dumps({"date": today, "counter": counter}))

        return f"JOB-{today}-{counter:03d}"


# Singleton instance
_job_tracker: Optional[JobTracker] = None


def get_job_tracker() -> JobTracker:
    """Get singleton JobTracker instance."""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker
