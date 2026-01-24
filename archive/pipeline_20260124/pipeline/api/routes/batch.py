"""
Batch processing endpoints for the pipeline API.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from pipeline.core.config import get_pipeline_settings
from pipeline.models.pipeline_job import JobStatus
from pipeline.services.job_tracker import get_job_tracker

router = APIRouter()


@router.get("/batch/queue")
async def get_batch_queue():
    """
    Get list of files waiting in the batch inbox.

    Returns files in data/pipeline/inbox/ ready for processing.
    """
    settings = get_pipeline_settings()

    inbox_files: List[Dict[str, Any]] = []
    inbox_path = settings.inbox_path

    if inbox_path.exists():
        for file_path in inbox_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in [".xlsx", ".xls", ".docx"]:
                stat = file_path.stat()
                inbox_files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "type": file_path.suffix.lower(),
                })

    return {
        "inbox_path": str(inbox_path),
        "file_count": len(inbox_files),
        "files": sorted(inbox_files, key=lambda x: x["modified"]),
    }


@router.post("/batch/process")
async def trigger_batch_processing(background_tasks: BackgroundTasks):
    """
    Trigger batch processing of all files in the inbox.

    Creates jobs for each file set and processes them asynchronously.
    Files are grouped by naming convention (e.g., project_epic.docx, project_estimation.xlsx).
    """
    settings = get_pipeline_settings()
    job_tracker = get_job_tracker()

    inbox_path = settings.inbox_path
    if not inbox_path.exists():
        return {
            "status": "no_files",
            "message": "Inbox directory is empty or does not exist",
        }

    # Group files by project prefix
    file_groups: Dict[str, Dict[str, Path]] = {}

    for file_path in inbox_path.iterdir():
        if not file_path.is_file():
            continue

        filename = file_path.name.lower()
        suffix = file_path.suffix.lower()

        if suffix not in [".xlsx", ".xls", ".docx"]:
            continue

        # Extract project prefix (everything before _epic, _estimation, _tdd, _stories)
        project_prefix = filename
        for doc_type in ["_epic", "_estimation", "_tdd", "_stories", "_story"]:
            if doc_type in filename:
                project_prefix = filename.split(doc_type)[0]
                break

        if project_prefix not in file_groups:
            file_groups[project_prefix] = {}

        # Determine document type
        if "_epic" in filename or filename.startswith("epic"):
            file_groups[project_prefix]["epic"] = file_path
        elif "_estimation" in filename or filename.startswith("estimation"):
            file_groups[project_prefix]["estimation"] = file_path
        elif "_tdd" in filename or filename.startswith("tdd"):
            file_groups[project_prefix]["tdd"] = file_path
        elif "_stories" in filename or "_story" in filename or filename.startswith("stor"):
            file_groups[project_prefix]["story"] = file_path
        else:
            # Try to detect by extension
            if suffix in [".xlsx", ".xls"]:
                file_groups[project_prefix]["estimation"] = file_path
            else:
                # Default to unknown
                if "unknown" not in file_groups[project_prefix]:
                    file_groups[project_prefix]["unknown"] = file_path

    # Create jobs for valid file groups
    jobs_created: List[Dict[str, Any]] = []

    for project, files in file_groups.items():
        # Must have at least estimation file
        if "estimation" not in files:
            continue

        # Create batch job
        job_id = await job_tracker.create_job(job_type="batch")

        # Move files to processing directory
        processing_dir = settings.processing_path / job_id
        processing_dir.mkdir(parents=True, exist_ok=True)

        files_added = []
        for doc_type, source_path in files.items():
            if doc_type == "unknown":
                continue

            dest_path = processing_dir / source_path.name
            source_path.rename(dest_path)

            await job_tracker.add_file(
                job_id=job_id,
                filename=source_path.name,
                file_path=str(dest_path),
                file_size=dest_path.stat().st_size,
                document_type=doc_type,
            )
            files_added.append({"type": doc_type, "filename": source_path.name})

        await job_tracker.update_status(job_id, JobStatus.UPLOADED)

        jobs_created.append({
            "job_id": job_id,
            "project": project,
            "files": files_added,
        })

        # Add background task to process this job
        background_tasks.add_task(_process_batch_job, job_id)

    return {
        "status": "processing",
        "jobs_created": len(jobs_created),
        "jobs": jobs_created,
        "message": f"Created {len(jobs_created)} batch job(s) for processing",
    }


async def _process_batch_job(job_id: str):
    """
    Process a single batch job through the full pipeline.

    This runs extraction, transformation, validation, and export
    automatically without user interaction.
    """
    from pipeline.api.routes.extract import extract_documents
    from pipeline.api.routes.export import export_data
    from pipeline.api.routes.preview import validate_data
    from pipeline.api.routes.transform import transform_data
    from pipeline.models.api_models import ExtractRequest

    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    try:
        # Step 1: Extract
        await extract_documents(job_id, ExtractRequest(use_llm_enhancement=True))

        # Step 2: Auto-apply default mappings (identity mapping)
        job = await job_tracker.get_job(job_id)
        if job:
            for file_info in job.files_uploaded:
                # Use identity mapping (source field = target field)
                doc_type = file_info.document_type
                current_mappings = job.mapping_results or {}
                current_mappings[doc_type] = {}  # Empty mapping = use defaults
                await job_tracker.update_job(job_id, mapping_results=current_mappings)

        # Step 3: Transform
        await transform_data(job_id)

        # Step 4: Validate
        await validate_data(job_id)

        # Step 5: Export
        await export_data(job_id)

        # Move to completed
        job = await job_tracker.get_job(job_id)
        if job and job.status == JobStatus.COMPLETED:
            # Clean up processing directory
            processing_dir = settings.processing_path / job_id
            if processing_dir.exists():
                import shutil
                shutil.rmtree(processing_dir)

    except Exception as e:
        # Mark job as failed
        await job_tracker.update_status(job_id, JobStatus.FAILED)
        await job_tracker.update_job(
            job_id,
            error_message=str(e),
        )

        # Move files to failed directory
        processing_dir = settings.processing_path / job_id
        failed_dir = settings.failed_path / job_id
        if processing_dir.exists():
            processing_dir.rename(failed_dir)


@router.get("/batch/status")
async def get_batch_status():
    """
    Get status of all batch jobs.

    Returns summary of jobs in various states.
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    # Get all jobs
    jobs_path = settings.jobs_path
    jobs_by_status: Dict[str, List[Dict[str, Any]]] = {
        "pending": [],
        "processing": [],
        "completed": [],
        "failed": [],
    }

    if jobs_path.exists():
        for job_dir in jobs_path.iterdir():
            if not job_dir.is_dir():
                continue

            job_id = job_dir.name
            job = await job_tracker.get_job(job_id)

            if not job or job.job_type != "batch":
                continue

            job_summary = {
                "job_id": job_id,
                "status": job.status.value,
                "created_at": job.created_at.isoformat(),
                "files_count": len(job.files_uploaded),
            }

            if job.status in [JobStatus.CREATED, JobStatus.UPLOADED]:
                jobs_by_status["pending"].append(job_summary)
            elif job.status == JobStatus.FAILED:
                jobs_by_status["failed"].append(job_summary)
            elif job.status == JobStatus.COMPLETED:
                jobs_by_status["completed"].append(job_summary)
            else:
                jobs_by_status["processing"].append(job_summary)

    return {
        "summary": {
            status: len(jobs) for status, jobs in jobs_by_status.items()
        },
        "jobs": jobs_by_status,
    }


@router.post("/batch/retry/{job_id}")
async def retry_failed_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Retry a failed batch job.

    Resets job status and re-runs the pipeline.
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not in failed state (current: {job.status.value})"
        )

    # Move files back from failed to processing
    failed_dir = settings.failed_path / job_id
    processing_dir = settings.processing_path / job_id

    if failed_dir.exists():
        failed_dir.rename(processing_dir)

    # Reset job status
    await job_tracker.update_status(job_id, JobStatus.UPLOADED)
    await job_tracker.update_job(
        job_id,
        error_message=None,
        steps_completed=[],
    )

    # Re-process
    background_tasks.add_task(_process_batch_job, job_id)

    return {
        "job_id": job_id,
        "status": "retrying",
        "message": "Job queued for reprocessing",
    }


@router.delete("/batch/job/{job_id}")
async def delete_batch_job(job_id: str):
    """
    Delete a batch job and its associated files.

    Only allows deletion of completed or failed jobs.
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail="Can only delete completed or failed jobs"
        )

    import shutil

    # Remove job directory
    job_dir = settings.jobs_path / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)

    # Remove from completed/failed
    for cleanup_path in [settings.completed_path, settings.failed_path]:
        output_dir = cleanup_path / job_id
        if output_dir.exists():
            shutil.rmtree(output_dir)

    return {
        "job_id": job_id,
        "status": "deleted",
        "message": "Job and associated files deleted",
    }
