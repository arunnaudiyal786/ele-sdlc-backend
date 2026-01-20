"""
File upload endpoints for the pipeline API.
"""

from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from pipeline.core.config import get_pipeline_settings
from pipeline.models.api_models import JobListResponse, UploadResponse
from pipeline.models.pipeline_job import JobStatus, JobStep
from pipeline.models.source_documents import detect_document_type
from pipeline.services.job_tracker import get_job_tracker

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    epic_doc: Optional[UploadFile] = File(None, description="Epic requirements DOCX"),
    estimation_doc: Optional[UploadFile] = File(None, description="Estimation XLSX (required)"),
    tdd_doc: Optional[UploadFile] = File(None, description="TDD DOCX"),
    stories_doc: Optional[UploadFile] = File(None, description="Stories DOCX"),
):
    """
    Upload source documents to create a new pipeline job.

    At minimum, an estimation document (XLSX) is required.
    Other documents (epic, TDD, stories) are optional.

    Returns:
        Job ID and list of received files
    """
    settings = get_pipeline_settings()
    job_tracker = get_job_tracker()

    # Validate at least estimation doc is provided
    if not estimation_doc:
        raise HTTPException(
            status_code=400,
            detail="Estimation document (XLSX) is required"
        )

    # Create new job
    job_id = await job_tracker.create_job(job_type="interactive")
    upload_dir = job_tracker.get_upload_dir(job_id)

    files_received = []

    # Process each file
    files_to_process = [
        ("epic", epic_doc),
        ("estimation", estimation_doc),
        ("tdd", tdd_doc),
        ("story", stories_doc),
    ]

    for doc_type, file in files_to_process:
        if file is None:
            continue

        # Validate file extension
        filename = file.filename or f"unknown_{doc_type}"
        ext = Path(filename).suffix.lower()

        if doc_type == "estimation" and ext not in [".xlsx", ".xls"]:
            raise HTTPException(
                status_code=400,
                detail=f"Estimation file must be Excel format (.xlsx, .xls), got {ext}"
            )
        elif doc_type != "estimation" and ext != ".docx":
            raise HTTPException(
                status_code=400,
                detail=f"{doc_type.title()} file must be DOCX format, got {ext}"
            )

        # Validate file size
        max_size = (
            settings.excel_max_size_mb if ext in [".xlsx", ".xls"]
            else settings.docx_max_size_mb
        ) * 1024 * 1024

        # Read and save file
        file_path = upload_dir / filename
        content = await file.read()

        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"{doc_type.title()} file exceeds maximum size ({max_size // (1024*1024)}MB)"
            )

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Detect document type if not explicitly provided
        detected_type = detect_document_type(filename)

        # Add file to job
        await job_tracker.add_file(
            job_id=job_id,
            filename=filename,
            file_path=str(file_path),
            file_size=len(content),
            document_type=detected_type.value,
        )

        files_received.append({
            "filename": filename,
            "size": len(content),
            "type": ext,
            "document_type": detected_type.value,
        })

    # Update job status
    await job_tracker.update_status(job_id, JobStatus.UPLOADED)
    await job_tracker.mark_step_completed(job_id, JobStep.UPLOAD)

    return UploadResponse(
        job_id=job_id,
        status="uploaded",
        files_received=files_received,
        message=f"Successfully uploaded {len(files_received)} file(s)",
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List all pipeline jobs with optional filtering.

    Args:
        status: Optional status filter (e.g., "completed", "failed")
        limit: Maximum jobs to return (default 50)
        offset: Offset for pagination

    Returns:
        List of jobs with pagination info
    """
    job_tracker = get_job_tracker()

    # Convert status string to JobStatus enum if provided
    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in JobStatus]}"
            )

    jobs = await job_tracker.list_jobs(status=status_filter, limit=limit, offset=offset)

    return JobListResponse(
        jobs=[
            {
                "job_id": j.job_id,
                "job_type": j.job_type,
                "status": j.status.value,
                "current_step": j.current_step.value if j.current_step else None,
                "created_at": j.created_at.isoformat(),
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
                "files_count": len(j.files_uploaded),
                "error_message": j.error_message,
            }
            for j in jobs
        ],
        total_count=len(jobs),
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get detailed status and information for a specific job.

    Args:
        job_id: Job identifier

    Returns:
        Full job details including status, files, and progress
    """
    job_tracker = get_job_tracker()
    job = await job_tracker.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status.value,
        "current_step": job.current_step.value if job.current_step else None,
        "steps_completed": [s.value for s in job.steps_completed],
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "files_uploaded": [
            {
                "filename": f.filename,
                "file_size": f.file_size,
                "document_type": f.document_type,
                "uploaded_at": f.uploaded_at.isoformat(),
            }
            for f in job.files_uploaded
        ],
        "error_message": job.error_message,
        "metadata": job.metadata,
    }


@router.get("/jobs/{job_id}/files")
async def get_job_files(job_id: str):
    """
    Get list of files uploaded for a job.

    Args:
        job_id: Job identifier

    Returns:
        List of uploaded files with metadata
    """
    job_tracker = get_job_tracker()
    job = await job_tracker.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job_id,
        "files": [
            {
                "filename": f.filename,
                "file_path": f.file_path,
                "file_size": f.file_size,
                "document_type": f.document_type,
                "uploaded_at": f.uploaded_at.isoformat(),
            }
            for f in job.files_uploaded
        ],
    }
