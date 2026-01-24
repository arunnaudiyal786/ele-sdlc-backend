"""
Export endpoints for the pipeline API.
"""

import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pipeline.core.config import get_pipeline_settings
from pipeline.models.api_models import ExportResponse
from pipeline.models.pipeline_job import JobStatus, JobStep
from pipeline.services.job_tracker import get_job_tracker
from shared.schemas.epic import Epic
from shared.schemas.estimation import Estimation
from shared.schemas.story import Story
from shared.schemas.tdd import TDD

router = APIRouter()

# Schema definitions for CSV export
SCHEMA_MAP = {
    "epics": Epic,
    "estimations": Estimation,
    "tdds": TDD,
    "stories": Story,
}


@router.post("/export/{job_id}", response_model=ExportResponse)
async def export_data(job_id: str):
    """
    Export validated data to CSV files.

    Generates CSV files in the target schema format for each entity type.
    Files are saved to data/pipeline/completed/{job_id}/.
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Ensure validation is complete
    if job.status.value not in ["validated", "exporting", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Data not yet validated. Run validation first."
        )

    # Update status
    await job_tracker.update_status(job_id, JobStatus.EXPORTING)

    export_dir = settings.completed_path / job_id
    export_dir.mkdir(parents=True, exist_ok=True)

    exported_files: List[Dict[str, Any]] = []
    total_records = 0

    for entity_type, schema_class in SCHEMA_MAP.items():
        # Load transformed data
        data = await job_tracker.load_artifact(
            job_id,
            f"{entity_type}_transformed",
            subfolder="transformed",
        )

        if not data:
            continue

        # Get CSV headers from schema
        headers = list(schema_class.model_fields.keys())

        # Write CSV file
        csv_path = export_dir / f"{entity_type}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for row in data:
                # Ensure row has all required fields
                csv_row = {h: row.get(h, "") for h in headers}
                writer.writerow(csv_row)

        exported_files.append({
            "entity": entity_type,
            "file_path": str(csv_path),
            "record_count": len(data),
        })
        total_records += len(data)

    # Save export metadata
    export_metadata = {
        "job_id": job_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "files": exported_files,
        "total_records": total_records,
    }

    await job_tracker.save_artifact(
        job_id,
        "export_metadata",
        export_metadata,
        subfolder="exported",
    )

    # Update job
    await job_tracker.update_job(
        job_id,
        export_results={
            "files_exported": len(exported_files),
            "total_records": total_records,
            "export_path": str(export_dir),
        },
    )
    await job_tracker.update_status(job_id, JobStatus.COMPLETED)
    await job_tracker.mark_step_completed(job_id, JobStep.EXPORT)

    return ExportResponse(
        job_id=job_id,
        status="completed",
        files_exported=exported_files,
        total_records=total_records,
        export_path=str(export_dir),
        message=f"Exported {total_records} records to {len(exported_files)} files",
    )


@router.get("/export/{job_id}/{entity}")
async def download_csv(job_id: str, entity: str):
    """
    Download a specific entity's CSV file.

    Args:
        job_id: Job identifier
        entity: Entity type (epics, estimations, tdds, stories)

    Returns:
        CSV file as streaming response
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Normalize entity name
    entity_name = entity.lower()
    if not entity_name.endswith("s"):
        entity_name += "s"

    if entity_name not in SCHEMA_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown entity type: {entity}. Must be one of: {list(SCHEMA_MAP.keys())}"
        )

    # Check if export exists
    csv_path = settings.completed_path / job_id / f"{entity_name}.csv"
    if not csv_path.exists():
        # Try to generate from transformed data
        data = await job_tracker.load_artifact(
            job_id,
            f"{entity_name}_transformed",
            subfolder="transformed",
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No {entity_name} data found for job {job_id}"
            )

        # Generate CSV in memory
        schema_class = SCHEMA_MAP[entity_name]
        headers = list(schema_class.model_fields.keys())

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for row in data:
            csv_row = {h: row.get(h, "") for h in headers}
            writer.writerow(csv_row)

        output.seek(0)
        content = output.getvalue()
    else:
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={job_id}_{entity_name}.csv"
        },
    )


@router.post("/sync-vector-db/{job_id}")
async def sync_to_vector_db(job_id: str):
    """
    Sync exported data to the main vector database.

    Copies exported CSVs to data/raw/ and triggers reindexing.
    This integrates the pipeline output with the main assessment system.
    """
    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail="Job must be completed before syncing to vector DB"
        )

    export_dir = settings.completed_path / job_id
    raw_data_dir = Path("data/raw")

    synced_files = []

    for entity_name in SCHEMA_MAP.keys():
        source_path = export_dir / f"{entity_name}.csv"
        if source_path.exists():
            # Append to existing or create new
            target_path = raw_data_dir / f"{entity_name}.csv"

            # Read existing data if present
            existing_ids = set()
            if target_path.exists():
                with open(target_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    id_field = f"{entity_name[:-1]}_id"  # epics -> epic_id
                    for row in reader:
                        if id_field in row:
                            existing_ids.add(row[id_field])

            # Append new records
            with open(source_path, "r", encoding="utf-8") as src:
                reader = csv.DictReader(src)
                fieldnames = reader.fieldnames or []

                # Open target in append mode
                mode = "a" if target_path.exists() else "w"
                with open(target_path, mode, newline="", encoding="utf-8") as dst:
                    writer = csv.DictWriter(dst, fieldnames=list(fieldnames))
                    if mode == "w":
                        writer.writeheader()

                    id_field = f"{entity_name[:-1]}_id"
                    new_count = 0
                    for row in reader:
                        if row.get(id_field) not in existing_ids:
                            writer.writerow(row)
                            new_count += 1

            synced_files.append({
                "entity": entity_name,
                "new_records": new_count,
                "target_path": str(target_path),
            })

    return {
        "job_id": job_id,
        "status": "synced",
        "synced_files": synced_files,
        "message": "Data synced to raw data directory. Run reindex script to update vector DB.",
        "next_step": "python scripts/reindex.py && python scripts/init_vector_db.py",
    }
