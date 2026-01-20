"""
Extraction endpoints for the pipeline API.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from pipeline.core.config import get_pipeline_settings
from pipeline.extractors.docx_extractor import DocxExtractor
from pipeline.extractors.excel_extractor import ExcelExtractor
from pipeline.extractors.llm_extractor import get_llm_extractor
from pipeline.models.api_models import ExtractRequest, ExtractResponse, MappingSuggestionsResponse
from pipeline.models.pipeline_job import JobStatus, JobStep
from pipeline.services.job_tracker import get_job_tracker

router = APIRouter()


@router.post("/extract/{job_id}", response_model=ExtractResponse)
async def extract_documents(job_id: str, request: ExtractRequest = None):
    """
    Extract structured data from uploaded documents.

    Runs appropriate extractors on each file and optionally uses
    LLM enhancement for low-confidence extractions.
    """
    if request is None:
        request = ExtractRequest()

    job_tracker = get_job_tracker()
    settings = get_pipeline_settings()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if not job.files_uploaded:
        raise HTTPException(status_code=400, detail="No files uploaded for this job")

    # Update status
    await job_tracker.update_status(job_id, JobStatus.EXTRACTING)

    # Initialize extractors
    docx_extractor = DocxExtractor()
    excel_extractor = ExcelExtractor()
    llm_extractor = get_llm_extractor() if request.use_llm_enhancement else None

    extractions: Dict[str, Any] = {}
    overall_confidences = []

    for file_info in job.files_uploaded:
        file_path = Path(file_info.file_path)
        doc_type = file_info.document_type

        try:
            # Select appropriate extractor
            if file_path.suffix.lower() in [".xlsx", ".xls"]:
                extraction = await excel_extractor.extract(file_path)
            elif file_path.suffix.lower() == ".docx":
                extraction = await docx_extractor.extract(file_path)
            else:
                continue

            # Optionally enhance with LLM if confidence is low
            if (
                llm_extractor
                and extraction.overall_confidence < request.llm_confidence_threshold
            ):
                enhanced = await llm_extractor.enhance_extraction(extraction, doc_type)
                # Merge enhanced fields into extraction
                for field_name, value in enhanced.identified_fields.items():
                    if field_name not in extraction.key_value_pairs:
                        extraction.key_value_pairs[field_name] = value
                # Update confidence
                if enhanced.confidence_scores:
                    avg_enhanced_conf = sum(enhanced.confidence_scores.values()) / len(
                        enhanced.confidence_scores
                    )
                    extraction.overall_confidence = (
                        extraction.overall_confidence + avg_enhanced_conf
                    ) / 2

            # Store extraction result
            extractions[file_info.filename] = {
                "document_type": doc_type,
                "fields_count": len(extraction.fields) + len(extraction.key_value_pairs),
                "tables_count": len(extraction.tables),
                "jira_ids": extraction.jira_ids,
                "emails": extraction.emails,
                "confidence": extraction.overall_confidence,
                "warnings": extraction.warnings,
            }

            overall_confidences.append(extraction.overall_confidence)

            # Save extraction artifact
            await job_tracker.save_artifact(
                job_id,
                f"{file_info.filename}_extraction",
                extraction.to_dict(),
                subfolder="extracted",
            )

        except Exception as e:
            extractions[file_info.filename] = {
                "error": str(e),
                "confidence": 0.0,
            }
            overall_confidences.append(0.0)

    # Calculate overall confidence
    overall_confidence = (
        sum(overall_confidences) / len(overall_confidences)
        if overall_confidences
        else 0.0
    )

    # Update job
    await job_tracker.update_job(
        job_id,
        extraction_results=extractions,
    )
    await job_tracker.update_status(job_id, JobStatus.EXTRACTED)
    await job_tracker.mark_step_completed(job_id, JobStep.EXTRACT)

    return ExtractResponse(
        job_id=job_id,
        status="extracted",
        extractions=extractions,
        overall_confidence=overall_confidence,
        message=f"Extracted data from {len(extractions)} file(s)",
    )


@router.get("/mapping-suggestions/{job_id}")
async def get_mapping_suggestions(job_id: str, entity: str = "estimation"):
    """
    Get AI-suggested field mappings for an entity type.

    Args:
        job_id: Job identifier
        entity: Entity type (epic, estimation, tdd, story)
    """
    job_tracker = get_job_tracker()
    llm_extractor = get_llm_extractor()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Find the extraction for the specified entity
    target_file = None
    for file_info in job.files_uploaded:
        if file_info.document_type == entity:
            target_file = file_info
            break

    if not target_file:
        raise HTTPException(
            status_code=404,
            detail=f"No {entity} document found in job"
        )

    # Load extraction
    extraction_data = await job_tracker.load_artifact(
        job_id,
        f"{target_file.filename}_extraction",
        subfolder="extracted",
    )

    if not extraction_data:
        raise HTTPException(
            status_code=400,
            detail="Extraction not found. Run extraction first."
        )

    # Get target schema
    from shared.schemas.epic import Epic
    from shared.schemas.estimation import Estimation
    from shared.schemas.story import Story
    from shared.schemas.tdd import TDD

    schema_map = {
        "epic": Epic,
        "estimation": Estimation,
        "tdd": TDD,
        "story": Story,
    }

    target_schema = schema_map.get(entity)
    if not target_schema:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {entity}")

    # Reconstruct ExtractedData for mapping suggestions
    from pipeline.extractors.base import ExtractedData, ExtractedField

    extracted = ExtractedData(
        raw_content=extraction_data.get("raw_content", ""),
        key_value_pairs=extraction_data.get("key_value_pairs", {}),
    )
    for field_name, field_data in extraction_data.get("fields", {}).items():
        extracted.fields[field_name] = ExtractedField(
            name=field_name,
            value=field_data.get("value"),
            confidence=field_data.get("confidence", 1.0),
        )

    # Get mapping suggestions from LLM
    mappings = await llm_extractor.suggest_field_mappings(extracted, target_schema)

    return MappingSuggestionsResponse(
        job_id=job_id,
        entity_type=entity,
        suggestions=[
            {
                "source_field": m.source_field,
                "target_field": m.target_field,
                "confidence": m.confidence,
                "source_value": m.source_value,
                "reasoning": m.reasoning,
            }
            for m in mappings
        ],
        unmapped_fields=[
            f for f in target_schema.model_fields.keys()
            if f not in [m.target_field for m in mappings]
        ],
    )


@router.post("/apply-mapping/{job_id}")
async def apply_mapping(job_id: str, entity: str, mappings: Dict[str, str]):
    """
    Apply confirmed field mappings for an entity.

    Args:
        job_id: Job identifier
        entity: Entity type
        mappings: Dict of source_field -> target_field
    """
    job_tracker = get_job_tracker()

    job = await job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Save mapping
    await job_tracker.save_artifact(
        job_id,
        f"{entity}_mapping",
        {"entity": entity, "mappings": mappings},
        subfolder="extracted",
    )

    # Update job status
    current_mappings = job.mapping_results or {}
    current_mappings[entity] = mappings
    await job_tracker.update_job(job_id, mapping_results=current_mappings)

    # Check if all entities are mapped
    entities_with_files = set(f.document_type for f in job.files_uploaded)
    entities_mapped = set(current_mappings.keys())

    if entities_with_files.issubset(entities_mapped):
        await job_tracker.update_status(job_id, JobStatus.MAPPED)
        await job_tracker.mark_step_completed(job_id, JobStep.MAP)

    return {
        "job_id": job_id,
        "status": "mapping_applied",
        "entity": entity,
        "applied_mappings": mappings,
    }
