"""
Transformation endpoints for the pipeline API.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from pipeline.core.id_generator import IDGenerator
from pipeline.core.relationship_manager import RelationshipManager
from pipeline.extractors.base import ExtractedData, ExtractedField, ExtractedTable
from pipeline.models.api_models import TransformResponse
from pipeline.models.pipeline_job import JobStatus, JobStep
from pipeline.services.job_tracker import get_job_tracker
from pipeline.transformers.epic_transformer import EpicTransformer
from pipeline.transformers.estimation_transformer import EstimationTransformer
from pipeline.transformers.story_transformer import StoryTransformer
from pipeline.transformers.tdd_transformer import TDDTransformer

router = APIRouter()


@router.post("/transform/{job_id}", response_model=TransformResponse)
async def transform_data(job_id: str):
    """
    Transform extracted data to target schemas.

    Runs transformers in order: epics → estimations → tdds → stories
    to ensure proper FK relationships.
    """
    job_tracker = get_job_tracker()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Update status
    await job_tracker.update_status(job_id, JobStatus.TRANSFORMING)

    # Initialize ID generator and relationship manager
    id_gen = IDGenerator(job_id)
    rel_mgr = RelationshipManager(job_id)

    # Initialize transformers
    epic_transformer = EpicTransformer()
    estimation_transformer = EstimationTransformer()
    tdd_transformer = TDDTransformer()
    story_transformer = StoryTransformer()

    records_created: Dict[str, int] = {
        "epics": 0,
        "estimations": 0,
        "tdds": 0,
        "stories": 0,
    }
    validation_warnings = []
    transformed_data: Dict[str, list] = {
        "epics": [],
        "estimations": [],
        "tdds": [],
        "stories": [],
    }

    # Get mappings (use empty dict if not set)
    mappings = job.mapping_results or {}

    # Process each file by document type
    for file_info in job.files_uploaded:
        doc_type = file_info.document_type

        # Load extraction
        extraction_data = await job_tracker.load_artifact(
            job_id,
            f"{file_info.filename}_extraction",
            subfolder="extracted",
        )

        if not extraction_data:
            validation_warnings.append(f"No extraction found for {file_info.filename}")
            continue

        # Reconstruct ExtractedData
        extracted = _reconstruct_extracted_data(extraction_data)

        # Get mapping for this entity type
        entity_mapping = mappings.get(doc_type, {})

        # Transform based on document type
        if doc_type == "epic":
            result = await epic_transformer.transform(
                extracted, entity_mapping, id_gen, rel_mgr, 0
            )
            if result.success and result.entity:
                transformed_data["epics"].append(result.entity.to_csv_row())
                records_created["epics"] += 1
            validation_warnings.extend([w.message for w in result.warnings])

        elif doc_type == "estimation":
            # Estimations typically have multiple rows in a table
            results = await estimation_transformer.transform_all_rows(
                extracted, entity_mapping, id_gen, rel_mgr
            )
            for result in results:
                if result.success and result.entity:
                    transformed_data["estimations"].append(result.entity.to_csv_row())
                    records_created["estimations"] += 1
                validation_warnings.extend([w.message for w in result.warnings])

        elif doc_type == "tdd":
            result = await tdd_transformer.transform(
                extracted, entity_mapping, id_gen, rel_mgr, 0
            )
            if result.success and result.entity:
                transformed_data["tdds"].append(result.entity.to_csv_row())
                records_created["tdds"] += 1
            validation_warnings.extend([w.message for w in result.warnings])

        elif doc_type == "story":
            # Stories can have multiple entries
            results = await story_transformer.transform_all_rows(
                extracted, entity_mapping, id_gen, rel_mgr
            )
            for result in results:
                if result.success and result.entity:
                    transformed_data["stories"].append(result.entity.to_csv_row())
                    records_created["stories"] += 1
                validation_warnings.extend([w.message for w in result.warnings])

    # Validate all relationships
    relationship_errors = rel_mgr.validate_all_relationships()
    for error in relationship_errors:
        validation_warnings.append(
            f"{error.entity_type}[{error.entity_id}].{error.field_name}: {error.message}"
        )

    # Save transformed data
    for entity_type, data in transformed_data.items():
        if data:
            await job_tracker.save_artifact(
                job_id,
                f"{entity_type}_transformed",
                data,
                subfolder="transformed",
            )

    # Save relationship graph
    await job_tracker.save_artifact(
        job_id,
        "relationship_graph",
        rel_mgr.export_relationship_graph(),
        subfolder="transformed",
    )

    # Update job
    await job_tracker.update_job(
        job_id,
        transformation_results={
            "records_created": records_created,
            "relationship_stats": rel_mgr.get_stats(),
        },
    )
    await job_tracker.update_status(job_id, JobStatus.TRANSFORMED)
    await job_tracker.mark_step_completed(job_id, JobStep.TRANSFORM)

    return TransformResponse(
        job_id=job_id,
        status="transformed",
        records_created=records_created,
        relationship_summary=rel_mgr.get_stats(),
        validation_warnings=validation_warnings[:20],  # Limit warnings
        message=f"Transformed {sum(records_created.values())} total records",
    )


def _reconstruct_extracted_data(data: Dict[str, Any]) -> ExtractedData:
    """Reconstruct ExtractedData from saved artifact."""
    extracted = ExtractedData(
        raw_content=data.get("raw_content", ""),
        key_value_pairs=data.get("key_value_pairs", {}),
        jira_ids=data.get("jira_ids", []),
        emails=data.get("emails", []),
        dates=data.get("dates", []),
        overall_confidence=data.get("overall_confidence", 1.0),
        warnings=data.get("warnings", []),
    )

    # Reconstruct fields
    for field_name, field_data in data.get("fields", {}).items():
        extracted.fields[field_name] = ExtractedField(
            name=field_name,
            value=field_data.get("value"),
            confidence=field_data.get("confidence", 1.0),
        )

    # Reconstruct tables if present
    for table_data in data.get("tables", []):
        if isinstance(table_data, dict):
            extracted.tables.append(
                ExtractedTable(
                    headers=table_data.get("headers", []),
                    rows=table_data.get("rows", []),
                    confidence=table_data.get("confidence", 1.0),
                )
            )

    return extracted
