import re
from datetime import datetime
from typing import List
from app.components.base.component import BaseComponent
from app.components.base.exceptions import RequirementTooShortError
from app.utils.audit import AuditTrailManager
from .models import RequirementSubmitRequest, RequirementResponse


class RequirementService(BaseComponent[RequirementSubmitRequest, RequirementResponse]):
    """Process and validate requirements."""

    STOPWORDS = {
        "that", "this", "with", "from", "have", "will", "should", "would",
        "could", "must", "need", "want", "like", "make", "create", "update",
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her",
    }

    @property
    def component_name(self) -> str:
        return "requirement"

    async def process(self, request: RequirementSubmitRequest) -> RequirementResponse:
        """Process submitted requirement."""
        if len(request.requirement_description) < 20:
            raise RequirementTooShortError(
                "Requirement must be at least 20 characters",
                component="requirement",
            )

        keywords = self._extract_keywords(request.requirement_description)

        # Save to audit trail
        audit = AuditTrailManager(request.session_id)
        audit.save_json(
            "requirement.json",
            {
                "requirement_description": request.requirement_description,
                "jira_epic_id": request.jira_epic_id,
            },
            subfolder="step1_input",
        )
        audit.save_json(
            "extracted_keywords.json",
            {"keywords": keywords},
            subfolder="step1_input",
        )
        audit.add_step_completed("requirement_submitted")

        return RequirementResponse(
            session_id=request.session_id,
            requirement_id=f"req_{request.session_id}",
            status="submitted",
            character_count=len(request.requirement_description),
            extracted_keywords=keywords,
            created_at=datetime.now(),
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from requirement text."""
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        filtered = [w for w in words if w not in self.STOPWORDS]
        return list(dict.fromkeys(filtered))[:20]  # Unique, max 20
