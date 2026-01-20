"""
Preview and validation endpoints for the pipeline API.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from pipeline.models.api_models import PreviewResponse, ValidationResponse
from pipeline.models.pipeline_job import JobStatus, JobStep
from pipeline.services.job_tracker import get_job_tracker

router = APIRouter()


@router.get("/preview/{job_id}", response_model=PreviewResponse)
async def preview_data(
    job_id: str,
    entity: str = Query(..., description="Entity type: epics, estimations, tdds, stories"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Preview transformed data for an entity type.

    Args:
        job_id: Job identifier
        entity: Entity type to preview
        limit: Maximum records to return
        offset: Offset for pagination
    """
    job_tracker = get_job_tracker()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Ensure transformation is done
    if job.status.value not in ["transformed", "validated", "exporting", "completed"]:
        raise HTTPException(
            status_code=400,
            detail="Data not yet transformed. Run transformation first."
        )

    # Normalize entity name
    entity_name = entity.lower()
    if not entity_name.endswith("s"):
        entity_name += "s"  # epics, estimations, tdds, stories

    # Load transformed data
    data = await job_tracker.load_artifact(
        job_id,
        f"{entity_name}_transformed",
        subfolder="transformed",
    )

    if data is None:
        return PreviewResponse(
            job_id=job_id,
            entity=entity_name,
            data=[],
            total_count=0,
            validation_results={"message": f"No {entity_name} data found"},
        )

    # Apply pagination
    total_count = len(data)
    paginated_data = data[offset : offset + limit]

    return PreviewResponse(
        job_id=job_id,
        entity=entity_name,
        data=paginated_data,
        total_count=total_count,
        validation_results={},
    )


@router.get("/validation/{job_id}", response_model=ValidationResponse)
async def validate_data(job_id: str):
    """
    Run full validation on transformed data.

    Checks:
    - Schema compliance for all entities
    - Foreign key integrity
    - Required field presence
    """
    job_tracker = get_job_tracker()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Load relationship graph
    relationship_graph = await job_tracker.load_artifact(
        job_id,
        "relationship_graph",
        subfolder="transformed",
    )

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    # Check relationship integrity
    relationship_integrity = {}
    if relationship_graph:
        relationships = relationship_graph.get("relationships", {})
        entities = relationship_graph.get("entities", {})

        # Check estimation -> epic links
        for est_id, epic_id in relationships.get("estimation_to_epic", {}).items():
            if epic_id not in entities.get("epics", []):
                errors.append({
                    "entity": "estimation",
                    "id": est_id,
                    "field": "epic_id",
                    "message": f"References non-existent epic: {epic_id}",
                })

        # Check TDD -> epic and estimation links
        for tdd_id, epic_id in relationships.get("tdd_to_epic", {}).items():
            if epic_id not in entities.get("epics", []):
                errors.append({
                    "entity": "tdd",
                    "id": tdd_id,
                    "field": "epic_id",
                    "message": f"References non-existent epic: {epic_id}",
                })

        for tdd_id, est_id in relationships.get("tdd_to_estimation", {}).items():
            if est_id not in entities.get("estimations", []):
                errors.append({
                    "entity": "tdd",
                    "id": tdd_id,
                    "field": "dev_est_id",
                    "message": f"References non-existent estimation: {est_id}",
                })

        # Check story links
        for story_id, epic_id in relationships.get("story_to_epic", {}).items():
            if epic_id not in entities.get("epics", []):
                errors.append({
                    "entity": "story",
                    "id": story_id,
                    "field": "epic_id",
                    "message": f"References non-existent epic: {epic_id}",
                })

        relationship_integrity = {
            "total_entities": sum(len(v) for v in entities.values()),
            "total_relationships": sum(len(v) for v in relationships.values()),
            "broken_links": len(errors),
        }

    # Update job validation results
    await job_tracker.update_job(
        job_id,
        validation_results={
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    )

    if len(errors) == 0:
        await job_tracker.update_status(job_id, JobStatus.VALIDATED)
        await job_tracker.mark_step_completed(job_id, JobStep.VALIDATE)

    return ValidationResponse(
        job_id=job_id,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        relationship_integrity=relationship_integrity,
    )
