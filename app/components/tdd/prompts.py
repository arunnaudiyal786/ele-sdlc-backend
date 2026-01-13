TDD_SYSTEM_PROMPT = """You are an expert software architect creating Technical Design Documents (TDDs).

Given a requirement, impacted modules, and effort estimates, generate a comprehensive TDD.

OUTPUT FORMAT (JSON only, no markdown):
{
  "tdd_name": "string - descriptive name for the TDD",
  "tdd_description": "string - 2-3 paragraph detailed description of the technical design",
  "technical_components": ["string array - technologies, frameworks, libraries needed"],
  "design_decisions": "string - key architectural decisions and rationale",
  "architecture_pattern": "string - e.g., Microservices, Event-Driven, CQRS, Adapter Pattern",
  "security_considerations": "string - security requirements and compliance needs",
  "performance_requirements": "string - SLAs, response times, throughput requirements",
  "tdd_dependencies": ["string array - dependent services or systems"]
}

Be thorough and specific to the requirement. Include concrete implementation details."""

TDD_USER_PROMPT = """REQUIREMENT:
{requirement_description}

IMPACTED MODULES:
{modules_summary}

EFFORT ESTIMATE:
{effort_summary}

SIMILAR HISTORICAL PROJECTS:
{historical_matches}

Generate a comprehensive Technical Design Document for this requirement."""

TDD_MARKDOWN_TEMPLATE = """# {tdd_name}

## 1. Overview

{tdd_description}

## 2. Architecture Pattern

**Pattern:** {architecture_pattern}

## 3. Technical Components

{technical_components_list}

## 4. Design Decisions

{design_decisions}

## 5. Dependencies

{dependencies_list}

## 6. Security Considerations

{security_considerations}

## 7. Performance Requirements

{performance_requirements}

## 8. Impacted Modules

### Functional Modules
{functional_modules_list}

### Technical Modules
{technical_modules_list}

## 9. Effort Summary

| Metric | Value |
|--------|-------|
| Development Hours | {dev_hours} |
| QA Hours | {qa_hours} |
| Total Hours | {total_hours} |
| Story Points | {story_points} |
| Confidence | {confidence} |

---

*Generated on: {generated_at}*
*Session ID: {session_id}*
"""
