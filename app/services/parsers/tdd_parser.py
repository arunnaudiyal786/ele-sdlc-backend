"""
TDD Parser

Parses TDD.docx files into structured JSON for agent context.
Extracts sections, tables, and full text content.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from docx import Document
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===== Pydantic Models =====

class ModuleInfo(BaseModel):
    """Module information from TDD Module List table"""

    system: str = Field(..., description="System code (e.g., INV)")
    component_name: str = Field(..., description="Component name (e.g., SVC4010)")
    component_type: str = Field(..., description="Component type (e.g., Java Service)")
    new_or_existing: str = Field(..., description="New or Existing")
    description: str = Field(..., description="Component description")


class ModuleDesign(BaseModel):
    """Module technical design details"""

    module_name: str = Field(..., description="Module name")
    description: str = Field(..., description="Design description")
    code_samples: List[str] = Field(default_factory=list, description="Code snippets")


class TableData(BaseModel):
    """Generic table structure"""

    table_number: int = Field(..., description="Table index in document")
    headers: List[str] = Field(..., description="Table column headers")
    rows: List[List[str]] = Field(..., description="Table data rows")
    context: str = Field(default="", description="Heading before table")


class TDDDocument(BaseModel):
    """Complete TDD document structure"""

    project_id: str = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project name")
    epic_description: str = Field(..., description="From 1.1 Purpose")
    scope: str = Field(default="", description="From 1.4 Scope")
    references: List[str] = Field(default_factory=list, description="From 1.2 References")
    glossary: Dict[str, str] = Field(default_factory=dict, description="From 1.3 Glossary table")
    assumptions: List[str] = Field(default_factory=list, description="From 1.5 Assumptions")
    design_overview: str = Field(default="", description="From 2. Design Overview")
    module_list: List[ModuleInfo] = Field(default_factory=list, description="From 2.1 Module List table")
    interaction_flow: str = Field(default="", description="From 2.2 Modules Interaction Flow")
    design_decisions: str = Field(default="", description="From 2.3 Key Design Decisions")
    design_patterns: List[str] = Field(default_factory=list, description="From 2.4 Design Patterns")
    risks: List[str] = Field(default_factory=list, description="From 2.5 Risks")
    module_designs: List[ModuleDesign] = Field(default_factory=list, description="From 3. Module Technical Design")
    full_text: str = Field(..., description="Complete document text")
    tables: List[TableData] = Field(default_factory=list, description="All tables")


# ===== Parser Class =====

class TDDParser:
    """Parse TDD.docx into structured TDDDocument"""

    async def parse(self, tdd_path: Path) -> TDDDocument:
        """
        Parse TDD document

        Args:
            tdd_path: Path to TDD.docx file

        Returns:
            TDDDocument with extracted structured data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If parsing fails
        """
        if not tdd_path.exists():
            raise FileNotFoundError(f"TDD file not found: {tdd_path}")

        logger.info(f"Parsing TDD: {tdd_path.name}")

        # Load document
        doc = Document(str(tdd_path))

        # Extract all components
        sections = self._extract_sections(doc)
        tables = self._extract_tables(doc)
        full_text = self._extract_full_text(doc)

        # Parse specific tables
        glossary = self._parse_glossary_table(tables)
        module_list = self._parse_module_table(tables)

        # Extract project metadata
        project_id = self._extract_project_id(tdd_path)
        project_name = sections.get("project_name", "")

        return TDDDocument(
            project_id=project_id,
            project_name=project_name,
            epic_description=sections.get("purpose", ""),
            scope=sections.get("scope", ""),
            references=sections.get("references", []),
            glossary=glossary,
            assumptions=sections.get("assumptions", []),
            design_overview=sections.get("design_overview", ""),
            module_list=module_list,
            interaction_flow=sections.get("interaction_flow", ""),
            design_decisions=sections.get("design_decisions", ""),
            design_patterns=sections.get("design_patterns", []),
            risks=sections.get("risks", []),
            module_designs=sections.get("module_designs", []),
            full_text=full_text,
            tables=tables,
        )

    def _extract_project_id(self, tdd_path: Path) -> str:
        """Extract project ID from file path"""
        # Pattern: PRJ-XXXXX in parent folder name
        folder_name = tdd_path.parent.name
        match = re.match(r"(PRJ-\d+)", folder_name)
        if match:
            return match.group(1)
        return folder_name

    def _extract_sections(self, doc: Document) -> Dict[str, Any]:
        """Extract all sections by heading hierarchy"""
        sections = {}
        current_section = None
        current_content = []

        for para in doc.paragraphs:
            text = para.text.strip()
            style = para.style.name if para.style else ""

            # Skip empty paragraphs
            if not text:
                continue

            # Check if heading
            if "Heading" in style or self._is_heading(text):
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content)

                # Start new section
                current_section = self._section_key(text)
                current_content = []
            else:
                # Accumulate content
                if current_section:
                    current_content.append(text)

        # Save last section
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content)

        # Extract specific sections
        result = {}

        # Project name from references
        if "references" in sections:
            result["project_name"] = self._extract_project_name_from_text(
                sections["references"]
            )
            result["references"] = self._parse_list_section(sections["references"])

        # Purpose (epic description)
        result["purpose"] = sections.get("purpose", "")

        # Scope
        result["scope"] = sections.get("scope", "")

        # Assumptions
        if "assumptions" in sections or "assumptions_dependencies" in sections:
            assumptions_text = sections.get("assumptions", sections.get("assumptions_dependencies", ""))
            result["assumptions"] = self._parse_list_section(assumptions_text)

        # Design overview
        result["design_overview"] = sections.get("design_overview", "")

        # Interaction flow
        result["interaction_flow"] = sections.get("modules_interaction_flow", sections.get("interaction_flow", ""))

        # Design decisions
        result["design_decisions"] = sections.get("key_design_decisions", sections.get("design_decisions", ""))

        # Design patterns
        if "design_patterns" in sections or "design_patterns_frameworks" in sections:
            patterns_text = sections.get("design_patterns", sections.get("design_patterns_frameworks", ""))
            result["design_patterns"] = self._parse_list_section(patterns_text)

        # Risks
        if "risks" in sections or "risks_issues" in sections:
            risks_text = sections.get("risks", sections.get("risks_issues", ""))
            result["risks"] = self._parse_list_section(risks_text)

        # Module designs (from section 3)
        result["module_designs"] = self._extract_module_designs(doc)

        return result

    def _is_heading(self, text: str) -> bool:
        """Check if text looks like a heading"""
        # Pattern: Numbers like "1.", "1.1", "2.3.4" at start
        return bool(re.match(r"^\d+(\.\d+)*\s+[A-Z]", text))

    def _section_key(self, heading: str) -> str:
        """Convert heading to section key"""
        # Remove numbers and clean
        text = re.sub(r"^\d+(\.\d+)*\s*", "", heading)
        # Convert to snake_case
        key = text.lower().replace(" ", "_").replace("&", "and")
        # Remove special chars
        key = re.sub(r"[^\w_]", "", key)
        return key

    def _parse_list_section(self, text: str) -> List[str]:
        """Parse bulleted or numbered list into list of strings"""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            # Remove bullet points or numbers
            cleaned = re.sub(r"^[-•*\d.)\s]+", "", line)
            if cleaned:
                items.append(cleaned)
        return items

    def _extract_project_name_from_text(self, references_text: str) -> str:
        """Extract project name from references section"""
        for line in references_text.split("\n"):
            if "PRJ-" in line:
                # Extract text after PRJ-XXXXX
                match = re.search(r"PRJ-\d+\s+(.+)", line)
                if match:
                    name = match.group(1).strip()
                    # Remove "Project Charter" or "Initiative"
                    name = re.sub(r"(Project Charter|Initiative).*$", "", name, flags=re.IGNORECASE)
                    return name.strip()
        return ""

    def _extract_tables(self, doc: Document) -> List[TableData]:
        """Extract all tables from document"""
        tables = []
        last_heading = ""

        # Track headings before tables
        for element in doc.element.body:
            if element.tag.endswith("p"):
                # Paragraph
                para = next((p for p in doc.paragraphs if p._element == element), None)
                if para and para.style and "Heading" in para.style.name:
                    last_heading = para.text.strip()

            elif element.tag.endswith("tbl"):
                # Table
                table_obj = next((t for t in doc.tables if t._element == element), None)
                if table_obj and len(table_obj.rows) > 0:
                    table_data = self._parse_table(table_obj, len(tables), last_heading)
                    tables.append(table_data)

        return tables

    def _parse_table(self, table, table_num: int, context: str) -> TableData:
        """Parse a single table"""
        rows_data = []

        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells]
            rows_data.append(row_cells)

        # First row is usually headers
        headers = rows_data[0] if rows_data else []
        data_rows = rows_data[1:] if len(rows_data) > 1 else []

        return TableData(
            table_number=table_num,
            headers=headers,
            rows=data_rows,
            context=context,
        )

    def _parse_glossary_table(self, tables: List[TableData]) -> Dict[str, str]:
        """Find and parse glossary table (usually first table)"""
        for table in tables:
            # Check if this looks like a glossary (Term, Definition columns)
            if len(table.headers) >= 2:
                if "term" in table.headers[0].lower() or "definition" in table.headers[1].lower():
                    glossary = {}
                    for row in table.rows:
                        if len(row) >= 2:
                            term = row[0].strip()
                            definition = row[1].strip()
                            if term and definition:
                                glossary[term] = definition
                    return glossary
        return {}

    def _parse_module_table(self, tables: List[TableData]) -> List[ModuleInfo]:
        """Find and parse module list table (usually second table)"""
        modules = []

        for table in tables:
            # Check if this looks like a module table
            headers_lower = [h.lower() for h in table.headers]

            # Look for module-related columns
            has_component = any("component" in h or "module" in h for h in headers_lower)
            has_system = any("system" in h for h in headers_lower)

            if has_component or has_system:
                # Try to map columns
                col_map = {}
                for i, header in enumerate(headers_lower):
                    if "system" in header:
                        col_map["system"] = i
                    elif "component name" in header or "module name" in header:
                        col_map["component_name"] = i
                    elif "component type" in header or "type" in header:
                        col_map["component_type"] = i
                    elif "new" in header or "existing" in header:
                        col_map["new_or_existing"] = i
                    elif "description" in header or "change description" in header:
                        col_map["description"] = i

                # Parse rows
                for row in table.rows:
                    if len(row) < 3:  # Need at least a few columns
                        continue

                    try:
                        module = ModuleInfo(
                            system=row[col_map.get("system", 0)] if "system" in col_map else "",
                            component_name=row[col_map.get("component_name", 1)] if "component_name" in col_map else row[1],
                            component_type=row[col_map.get("component_type", 2)] if "component_type" in col_map else row[2],
                            new_or_existing=row[col_map.get("new_or_existing", 3)] if "new_or_existing" in col_map else "New",
                            description=row[col_map.get("description", 4)] if "description" in col_map and len(row) > 4 else "",
                        )
                        modules.append(module)
                    except Exception as e:
                        logger.warning(f"Failed to parse module row: {e}")
                        continue

                # If we found modules, return them
                if modules:
                    return modules

        return modules

    def _extract_module_designs(self, doc: Document) -> List[ModuleDesign]:
        """Extract module designs from section 3"""
        designs = []
        current_module = None
        current_desc = []
        current_code = []

        for para in doc.paragraphs:
            text = para.text.strip()
            style = para.style.name if para.style else ""

            # Check for module heading (e.g., "SVC4010 (Java):")
            if "Heading" in style and re.search(r"SVC\d+|MOD\d+|BTH\d+", text):
                # Save previous module
                if current_module:
                    designs.append(
                        ModuleDesign(
                            module_name=current_module,
                            description="\n".join(current_desc),
                            code_samples=current_code,
                        )
                    )

                # Start new module
                current_module = text
                current_desc = []
                current_code = []

            elif current_module:
                # Check if this is code (has programming keywords or syntax)
                if self._looks_like_code(text):
                    current_code.append(text)
                else:
                    current_desc.append(text)

        # Save last module
        if current_module:
            designs.append(
                ModuleDesign(
                    module_name=current_module,
                    description="\n".join(current_desc),
                    code_samples=current_code,
                )
            )

        return designs

    def _looks_like_code(self, text: str) -> bool:
        """Heuristic to detect code samples"""
        code_indicators = [
            "@Service", "@Component", "public", "private", "class", "function",
            "async", "await", "import", "from", "def", "return",
            "{", "}", "(", ")", ";", "=>"
        ]
        return any(indicator in text for indicator in code_indicators)

    def _extract_full_text(self, doc: Document) -> str:
        """Extract complete document text"""
        paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)
