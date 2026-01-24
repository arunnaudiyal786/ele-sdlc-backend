"""
LLM-enhanced extractor using Ollama.

Uses the LLM to:
- Enhance extraction by identifying field values from unstructured text
- Suggest field mappings between extracted data and target schemas
- Increase confidence scores for ambiguous extractions
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import httpx
from pydantic import BaseModel

from pipeline.core.config import get_pipeline_settings
from pipeline.extractors.base import ExtractedData, ExtractedField


class FieldMapping:
    """Represents a suggested mapping from source to target field."""

    def __init__(
        self,
        source_field: str,
        target_field: str,
        confidence: float,
        source_value: Any = None,
        reasoning: Optional[str] = None,
    ):
        self.source_field = source_field
        self.target_field = target_field
        self.confidence = confidence
        self.source_value = source_value
        self.reasoning = reasoning

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_field": self.source_field,
            "target_field": self.target_field,
            "confidence": self.confidence,
            "source_value": self.source_value,
            "reasoning": self.reasoning,
        }


class EnhancedExtraction:
    """Result of LLM-enhanced extraction."""

    def __init__(self):
        self.identified_fields: Dict[str, Any] = {}
        self.confidence_scores: Dict[str, float] = {}
        self.unmapped_content: List[Dict[str, Any]] = []
        self.suggestions: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identified_fields": self.identified_fields,
            "confidence_scores": self.confidence_scores,
            "unmapped_content": self.unmapped_content,
            "suggestions": self.suggestions,
        }


class LLMExtractor:
    """
    Enhances document extraction using Ollama LLM.

    Provides:
    - Field identification from unstructured text
    - Mapping suggestions between source and target schemas
    - Confidence scoring for ambiguous extractions
    """

    def __init__(self):
        self.settings = get_pipeline_settings()
        self.prompts_dir = Path(__file__).parent.parent / "prompts"

    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt template from the prompts directory."""
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        if prompt_path.exists():
            return prompt_path.read_text()
        return ""

    async def _call_ollama(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """
        Call Ollama API for text generation.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text response
        """
        payload = {
            "model": self.settings.llm_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.TimeoutException:
            return json.dumps({"error": "LLM request timed out"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"LLM unavailable: {str(e)}"})

    def _parse_llm_json(self, raw: str, default: Any = None) -> Any:
        """
        Parse JSON from LLM response with error recovery.

        Handles common LLM JSON issues like trailing commas,
        unquoted keys, etc.
        """
        if not raw:
            return default or {}

        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        import re

        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object/array in the text
        json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Basic repairs
        cleaned = raw.strip()
        # Remove trailing commas
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        # Fix unquoted keys
        cleaned = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return default or {}

    async def enhance_extraction(
        self, extracted: ExtractedData, target_entity: str
    ) -> EnhancedExtraction:
        """
        Use LLM to enhance extraction by identifying field values.

        Args:
            extracted: Initial extraction from document extractor
            target_entity: Target entity type (epic, estimation, tdd, story)

        Returns:
            EnhancedExtraction with identified fields and confidence scores
        """
        result = EnhancedExtraction()

        # Load the appropriate prompt template
        prompt_template = self._load_prompt(f"{target_entity}_extraction")
        if not prompt_template:
            # Use generic extraction prompt
            prompt_template = self._get_generic_extraction_prompt(target_entity)

        # Prepare document content for LLM
        doc_content = self._prepare_document_content(extracted)

        # Format the prompt
        prompt = prompt_template.replace("{document_text}", doc_content)

        # Call LLM
        raw_response = await self._call_ollama(prompt)

        # Parse response
        parsed = self._parse_llm_json(raw_response, {})

        # Process extractions
        extractions = parsed.get("extractions", [])
        if extractions and isinstance(extractions, list):
            # Take the first extraction (most confident)
            for extraction in extractions:
                for field_name, field_value in extraction.items():
                    if field_name not in ["confidence", "source_location"]:
                        result.identified_fields[field_name] = field_value
                        result.confidence_scores[field_name] = extraction.get(
                            "confidence", 0.7
                        )

        # Process unmapped content
        unmapped = parsed.get("unmapped_content", [])
        if unmapped and isinstance(unmapped, list):
            result.unmapped_content = unmapped

        return result

    async def suggest_field_mappings(
        self, extracted: ExtractedData, target_schema: Type[BaseModel]
    ) -> List[FieldMapping]:
        """
        Suggest mappings between extracted fields and target schema.

        Args:
            extracted: Extraction from document
            target_schema: Pydantic model for target entity

        Returns:
            List of suggested field mappings
        """
        mappings: List[FieldMapping] = []

        # Get target field names from schema
        target_fields = list(target_schema.model_fields.keys())

        # Get source fields from extraction
        source_fields = list(extracted.fields.keys())
        source_fields.extend(list(extracted.key_value_pairs.keys()))

        # Build mapping prompt
        prompt = f"""You are a data mapping assistant. Map source fields to target fields.

SOURCE FIELDS (from extracted document):
{json.dumps(source_fields, indent=2)}

TARGET FIELDS (required schema):
{json.dumps(target_fields, indent=2)}

SOURCE VALUES:
{json.dumps({k: v.value for k, v in extracted.fields.items()}, indent=2)}

KEY-VALUE PAIRS:
{json.dumps(extracted.key_value_pairs, indent=2)}

For each source field, suggest the best target field match.

OUTPUT FORMAT (valid JSON):
{{
  "mappings": [
    {{
      "source_field": "source field name",
      "target_field": "target field name",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }}
  ]
}}

RULES:
- Only map fields with clear semantic similarity
- Use confidence < 0.5 for uncertain mappings
- Leave unmapped if no good match exists
"""

        raw_response = await self._call_ollama(prompt)
        parsed = self._parse_llm_json(raw_response, {"mappings": []})

        for mapping in parsed.get("mappings", []):
            source = mapping.get("source_field", "")
            target = mapping.get("target_field", "")
            if source and target:
                # Get source value
                source_value = None
                if source in extracted.fields:
                    source_value = extracted.fields[source].value
                elif source in extracted.key_value_pairs:
                    source_value = extracted.key_value_pairs[source]

                mappings.append(
                    FieldMapping(
                        source_field=source,
                        target_field=target,
                        confidence=mapping.get("confidence", 0.5),
                        source_value=source_value,
                        reasoning=mapping.get("reasoning"),
                    )
                )

        return mappings

    def _prepare_document_content(self, extracted: ExtractedData) -> str:
        """Prepare document content for LLM processing."""
        parts = []

        # Add raw content (truncated if too long)
        if extracted.raw_content:
            content = extracted.raw_content[:4000]  # Limit to ~4k chars
            if len(extracted.raw_content) > 4000:
                content += "\n[... content truncated ...]"
            parts.append(f"DOCUMENT TEXT:\n{content}")

        # Add key-value pairs
        if extracted.key_value_pairs:
            kv_text = "\n".join(
                f"- {k}: {v}" for k, v in extracted.key_value_pairs.items()
            )
            parts.append(f"\nDETECTED KEY-VALUE PAIRS:\n{kv_text}")

        # Add table summaries
        if extracted.tables:
            for i, table in enumerate(extracted.tables):
                table_summary = f"\nTABLE {i + 1} (Columns: {', '.join(table.headers)}):"
                for j, row in enumerate(table.rows[:5]):  # First 5 rows
                    row_text = " | ".join(f"{k}={v}" for k, v in row.items())
                    table_summary += f"\n  Row {j + 1}: {row_text}"
                if len(table.rows) > 5:
                    table_summary += f"\n  [... {len(table.rows) - 5} more rows ...]"
                parts.append(table_summary)

        # Add detected patterns
        if extracted.jira_ids:
            parts.append(f"\nDETECTED JIRA IDs: {', '.join(extracted.jira_ids)}")
        if extracted.emails:
            parts.append(f"\nDETECTED EMAILS: {', '.join(extracted.emails)}")
        if extracted.dates:
            parts.append(f"\nDETECTED DATES: {', '.join(extracted.dates)}")

        return "\n".join(parts)

    def _get_generic_extraction_prompt(self, entity_type: str) -> str:
        """Get a generic extraction prompt for entity type."""
        field_hints = {
            "epic": "epic_name, jira_id, req_description, status, epic_priority, epic_owner, epic_team, epic_target_date",
            "estimation": "task_description, complexity, dev_effort_hours, qa_effort_hours, story_points, risk_level, estimation_method",
            "tdd": "tdd_name, tdd_description, tdd_version, tdd_status, tdd_author, technical_components, architecture_pattern",
            "story": "jira_story_id, summary, description, assignee, status, story_points, sprint, priority, labels, acceptance_criteria",
        }

        fields = field_hints.get(entity_type, "")

        return f"""You are a data extraction assistant.

Extract {entity_type.upper()} information from the following document content.

DOCUMENT CONTENT:
{{document_text}}

TARGET FIELDS TO EXTRACT:
{fields}

OUTPUT FORMAT (valid JSON):
{{
  "extractions": [
    {{
      "field_name": "value or null",
      "confidence": 0.0-1.0
    }}
  ],
  "unmapped_content": [
    {{
      "text": "content that couldn't be mapped",
      "possible_field": "suggested field or null"
    }}
  ]
}}

RULES:
- If a field cannot be determined with confidence, set value to null
- Be precise - don't guess values that aren't clearly stated
"""

    @staticmethod
    async def verify_ollama_connection() -> bool:
        """Verify Ollama is accessible."""
        settings = get_pipeline_settings()
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_llm_extractor: Optional[LLMExtractor] = None


def get_llm_extractor() -> LLMExtractor:
    """Get singleton LLMExtractor instance."""
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = LLMExtractor()
    return _llm_extractor
