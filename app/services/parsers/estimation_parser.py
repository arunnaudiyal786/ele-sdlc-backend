"""
Estimation Parser

Parses estimation.xlsx files into structured JSON for agent context.
Handles dynamic column names with fuzzy matching.
"""

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===== Column Mapping for Fuzzy Matching =====

COLUMN_MAPPINGS = {
    "module": ["module", "component", "module_affected", "area", "module affected"],
    "task_description": ["task_description", "description", "task description", "work_item", "scope", "task"],
    "dev_points": ["dev_points", "dev points", "dev_effort", "development points", "story_points", "points"],
    "qa_points": ["qa_points", "qa points", "qa_effort", "testing effort", "qa effort"],
    "ticket_id": ["ticket_id", "ticket id", "jira_id", "story_id", "id"],
    "notes": ["notes", "comments", "remarks"],
}


# ===== Pydantic Models =====

class TaskEstimate(BaseModel):
    """Individual task estimation"""

    ticket_id: Optional[str] = Field(None, description="Ticket/Story ID if available")
    task_description: str = Field(..., description="Task description")
    dev_points: float = Field(0.0, description="Development effort in points")
    qa_points: float = Field(0.0, description="QA effort in points")
    total_points: float = Field(0.0, description="Total effort in points (when no DEV/QA split)")
    notes: Optional[str] = Field(None, description="Additional notes")
    module_affected: Optional[str] = Field(None, description="Module/component name")


class EstimationDocument(BaseModel):
    """Complete estimation document structure"""

    project_id: str = Field(..., description="Project ID")
    total_dev_points: float = Field(0.0, description="Total development points")
    total_qa_points: float = Field(0.0, description="Total QA points")
    total_points: float = Field(0.0, description="Total effort points (when no DEV/QA split)")
    task_breakdown: List[TaskEstimate] = Field(default_factory=list, description="Individual task estimates")
    estimate_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary data")
    assumptions_and_risks: List[str] = Field(default_factory=list, description="Assumptions and risks")
    sizing_guidelines: Dict[str, str] = Field(default_factory=dict, description="Sizing guidelines")
    budget_summary: Dict[str, Any] = Field(default_factory=dict, description="Budget information")
    all_sheets: Dict[str, Any] = Field(default_factory=dict, description="Complete sheet data for LLM")


# ===== Parser Class =====

class EstimationParser:
    """Parse estimation.xlsx into structured EstimationDocument"""

    async def parse(self, estimation_path: Path) -> EstimationDocument:
        """
        Parse estimation Excel file

        Supports two formats:
        1. NEW FORMAT: Single "Scope Estimation" sheet with two columns:
           - "Scope Item" (multi-line description)
           - "Effort in Points" (single effort value)

        2. LEGACY FORMAT: Multiple sheets (Task Breakdown, Dev Estimate, QA Estimate, etc.)
           with separate dev_points/qa_points columns

        Args:
            estimation_path: Path to estimation.xlsx file

        Returns:
            EstimationDocument with extracted data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If parsing fails
        """
        if not estimation_path.exists():
            raise FileNotFoundError(f"Estimation file not found: {estimation_path}")

        logger.info(f"Parsing estimation: {estimation_path.name}")

        # Load Excel file
        xl = pd.ExcelFile(estimation_path)
        logger.info(f"Found sheets: {xl.sheet_names}")

        # Extract project ID
        project_id = self._extract_project_id(estimation_path)

        # Detect format: Check for new "Scope Estimation" format first
        scope_sheet = self._find_sheet(xl.sheet_names, ["scope estimation", "scope"])
        if scope_sheet:
            logger.info(f"Detected NEW format: parsing 'Scope Estimation' sheet")
            return await self._parse_new_format(estimation_path, xl, project_id, scope_sheet)

        # Fall back to legacy format
        logger.info("Detected LEGACY format: parsing multiple sheets")
        return await self._parse_legacy_format(estimation_path, xl, project_id)

    async def _parse_new_format(
        self,
        estimation_path: Path,
        xl: pd.ExcelFile,
        project_id: str,
        scope_sheet: str,
    ) -> EstimationDocument:
        """
        Parse NEW format: Single "Scope Estimation" sheet with two columns.

        Columns:
        - "Scope Item": Multi-line task description (lines separated by \\n)
        - "Effort in Points": Total effort as single number

        Args:
            estimation_path: Path to Excel file
            xl: ExcelFile object
            project_id: Extracted project ID
            scope_sheet: Name of the scope estimation sheet

        Returns:
            EstimationDocument with parsed data
        """
        df = pd.read_excel(estimation_path, sheet_name=scope_sheet)
        logger.info(f"Parsing scope sheet with columns: {list(df.columns)}")

        # Normalize column names
        col_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if "scope" in col_lower or "item" in col_lower:
                col_mapping[col] = "scope_item"
            elif "effort" in col_lower or "point" in col_lower:
                col_mapping[col] = "effort_points"

        df = df.rename(columns=col_mapping)
        logger.info(f"Normalized columns: {col_mapping}")

        tasks: List[TaskEstimate] = []
        total_points = 0.0

        for _, row in df.iterrows():
            scope_item = row.get("scope_item", "")
            effort = row.get("effort_points", 0)

            # Skip empty rows
            if pd.isna(scope_item) or str(scope_item).strip() == "":
                continue

            # Parse effort
            try:
                effort_value = float(effort) if pd.notna(effort) else 0.0
            except (ValueError, TypeError):
                effort_value = 0.0

            total_points += effort_value

            # Parse scope item - first line is typically the main task/module
            scope_lines = str(scope_item).split("\n")
            main_task = scope_lines[0].strip() if scope_lines else str(scope_item)
            subtasks = [line.strip() for line in scope_lines[1:] if line.strip()]

            # Create task with full description
            task = TaskEstimate(
                ticket_id=None,
                task_description=main_task,
                dev_points=0.0,  # No DEV/QA split in new format
                qa_points=0.0,
                total_points=effort_value,
                notes="\n".join(subtasks) if subtasks else None,
                module_affected=main_task.split()[0] if main_task else None,  # First word as module hint
            )
            tasks.append(task)

        logger.info(f"Parsed {len(tasks)} scope items, Total Points: {total_points}")

        # Load all sheets as JSON for LLM
        all_sheets = self._load_all_sheets(estimation_path, xl)

        return EstimationDocument(
            project_id=project_id,
            total_dev_points=0.0,  # No DEV/QA split
            total_qa_points=0.0,
            total_points=total_points,
            task_breakdown=tasks,
            estimate_summary={"format": "scope_estimation", "total_scope_items": len(tasks)},
            assumptions_and_risks=[],
            sizing_guidelines={},
            budget_summary={},
            all_sheets=all_sheets,
        )

    async def _parse_legacy_format(
        self,
        estimation_path: Path,
        xl: pd.ExcelFile,
        project_id: str,
    ) -> EstimationDocument:
        """
        Parse LEGACY format: Multiple sheets with DEV/QA point separation.

        Expected sheets:
        - Task Breakdown: Individual tasks with dev_points, qa_points
        - Dev Estimate: Development effort details
        - QA Estimate: QA effort details
        - Assumptions and Risks
        - Sizing Guidelines

        Args:
            estimation_path: Path to Excel file
            xl: ExcelFile object
            project_id: Extracted project ID

        Returns:
            EstimationDocument with parsed data
        """
        task_breakdown: List[TaskEstimate] = []
        total_dev = 0.0
        total_qa = 0.0

        # Try to find and parse Task Breakdown sheet
        task_sheet_name = self._find_sheet(xl.sheet_names, ["task breakdown", "breakdown", "tasks", "task"])
        if task_sheet_name:
            logger.info(f"Parsing task breakdown from sheet: {task_sheet_name}")
            task_breakdown, total_dev, total_qa = self._parse_task_breakdown(
                estimation_path, task_sheet_name
            )

        # Try to extract totals from Dev/QA Estimates sheets if not found in breakdown
        if total_dev == 0:
            dev_sheet = self._find_sheet(xl.sheet_names, ["dev estimate", "development"])
            if dev_sheet:
                df = pd.read_excel(estimation_path, sheet_name=dev_sheet)
                total_dev = self._extract_total(df, "Total Dev Points:")

        if total_qa == 0:
            qa_sheet = self._find_sheet(xl.sheet_names, ["qa estimate", "testing"])
            if qa_sheet:
                df = pd.read_excel(estimation_path, sheet_name=qa_sheet)
                total_qa = self._extract_total(df, "Total QA Points:")

        # Parse other sections
        assumptions = self._parse_assumptions(xl, estimation_path)
        sizing_guidelines = self._parse_sizing_guidelines(xl, estimation_path)

        # Load all sheets as JSON for LLM
        all_sheets = self._load_all_sheets(estimation_path, xl)

        return EstimationDocument(
            project_id=project_id,
            total_dev_points=total_dev,
            total_qa_points=total_qa,
            total_points=total_dev + total_qa,
            task_breakdown=task_breakdown,
            estimate_summary={"format": "legacy", "total_tasks": len(task_breakdown)},
            assumptions_and_risks=assumptions,
            sizing_guidelines=sizing_guidelines,
            budget_summary={},
            all_sheets=all_sheets,
        )

    def _load_all_sheets(self, estimation_path: Path, xl: pd.ExcelFile) -> Dict[str, Any]:
        """Load all sheets as JSON for LLM context."""
        all_sheets: Dict[str, Any] = {}
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(estimation_path, sheet_name=sheet_name)
                # Convert to records, handling NaN
                all_sheets[sheet_name] = df.fillna("").to_dict(orient="records")
            except Exception as e:
                logger.warning(f"Failed to parse sheet {sheet_name}: {e}")
        return all_sheets

    def _extract_project_id(self, estimation_path: Path) -> str:
        """Extract project ID from file path"""
        folder_name = estimation_path.parent.name
        match = re.match(r"(PRJ-\d+)", folder_name)
        if match:
            return match.group(1)
        return folder_name

    def _find_sheet(self, sheet_names: List[str], keywords: List[str]) -> Optional[str]:
        """Find sheet by keywords (case insensitive)"""
        for sheet_name in sheet_names:
            sheet_lower = sheet_name.lower()
            if any(keyword in sheet_lower for keyword in keywords):
                return sheet_name
        return None

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names using fuzzy matching"""
        df = df.copy()
        actual_columns = [str(col).lower().strip() for col in df.columns]

        # Build mapping from actual columns to standard names
        column_rename = {}

        for standard_name, variations in COLUMN_MAPPINGS.items():
            for col_idx, actual_col in enumerate(actual_columns):
                original_col = df.columns[col_idx]

                # Check if any variation matches
                if any(var in actual_col for var in variations):
                    column_rename[original_col] = standard_name
                    break

        # Rename columns
        if column_rename:
            df = df.rename(columns=column_rename)
            logger.info(f"Normalized columns: {column_rename}")

        return df

    def _parse_task_breakdown(
        self, estimation_path: Path, sheet_name: str
    ) -> Tuple[List[TaskEstimate], float, float]:
        """
        Parse task breakdown sheet

        Returns:
            (tasks, total_dev_points, total_qa_points)
        """
        df = pd.read_excel(estimation_path, sheet_name=sheet_name)

        # Normalize columns
        df = self._normalize_columns(df)

        tasks = []
        total_dev = 0.0
        total_qa = 0.0

        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get("task_description")) or str(row.get("task_description", "")).strip() == "":
                continue

            # Parse story points from combined format
            dev_points = 0.0
            qa_points = 0.0

            # Check if there's a "Story Points" column with "DEV: X\nQA: Y" format
            has_story_points = "Story Points" in row or "story_points" in row.index or "points" in row.index

            if has_story_points:
                story_points_val = row.get("Story Points") or row.get("story_points") or row.get("points", "")
                story_points_str = str(story_points_val) if pd.notna(story_points_val) else ""

                # If it contains "DEV:" or "QA:", parse it
                if "DEV:" in story_points_str.upper() or "QA:" in story_points_str.upper():
                    dev_points, qa_points = self._parse_story_points(story_points_str)
                else:
                    # Try to convert as single number
                    try:
                        points = float(story_points_str)
                        dev_points = points  # Assume all points are dev if not split
                    except (ValueError, TypeError):
                        pass

            # Check for separate dev/qa columns if not found
            if dev_points == 0.0 and "dev_points" in row.index:
                try:
                    dev_val = row.get("dev_points", 0)
                    if pd.notna(dev_val):
                        dev_points = float(dev_val)
                except (ValueError, TypeError):
                    pass

            if qa_points == 0.0 and "qa_points" in row.index:
                try:
                    qa_val = row.get("qa_points", 0)
                    if pd.notna(qa_val):
                        qa_points = float(qa_val)
                except (ValueError, TypeError):
                    pass

            total_dev += dev_points
            total_qa += qa_points

            task = TaskEstimate(
                ticket_id=str(row.get("ticket_id", "")) if pd.notna(row.get("ticket_id")) else None,
                task_description=str(row.get("task_description", "")),
                dev_points=dev_points,
                qa_points=qa_points,
                total_points=dev_points + qa_points,
                notes=str(row.get("notes", "")) if pd.notna(row.get("notes")) else None,
                module_affected=str(row.get("module", "")) if pd.notna(row.get("module")) else None,
            )
            tasks.append(task)

        logger.info(f"Parsed {len(tasks)} tasks, Dev: {total_dev}, QA: {total_qa}")
        return tasks, total_dev, total_qa

    def _parse_story_points(self, points_str: str) -> Tuple[float, float]:
        """
        Parse story points from format: "DEV: 45 Points\nQA: 25 Points"

        Returns:
            (dev_points, qa_points)
        """
        dev_points = 0.0
        qa_points = 0.0

        if not points_str or pd.isna(points_str):
            return (dev_points, qa_points)

        lines = str(points_str).split("\n")
        for line in lines:
            line = line.upper()
            if "DEV" in line:
                # Extract number: "DEV: 45 Points" → 45.0
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    dev_points = float(match.group(1))
            elif "QA" in line:
                match = re.search(r"(\d+\.?\d*)", line)
                if match:
                    qa_points = float(match.group(1))

        return (dev_points, qa_points)

    def _extract_total(self, df: pd.DataFrame, label: str) -> float:
        """
        Extract total from sheet with pattern "Total Dev Points: 160.0"

        Args:
            df: DataFrame to search
            label: Label to look for (e.g., "Total Dev Points:")

        Returns:
            Extracted total value
        """
        for col in df.columns:
            for _, row in df.iterrows():
                cell_value = str(row[col])
                if label in cell_value:
                    # Try to extract number after label
                    match = re.search(r"(\d+\.?\d*)", cell_value)
                    if match:
                        return float(match.group(1))

                # Check if next cell has the value
                col_idx = df.columns.get_loc(col)
                if col_idx + 1 < len(df.columns):
                    next_col = df.columns[col_idx + 1]
                    if label.lower() in str(row[col]).lower():
                        try:
                            return float(row[next_col])
                        except (ValueError, TypeError):
                            pass

        return 0.0

    def _parse_assumptions(self, xl: pd.ExcelFile, estimation_path: Path) -> List[str]:
        """Parse Assumptions and Risks sheet"""
        assumptions = []

        sheet_name = self._find_sheet(
            xl.sheet_names, ["assumptions", "risks", "assumptions and risks"]
        )
        if not sheet_name:
            return assumptions

        df = pd.read_excel(estimation_path, sheet_name=sheet_name)

        # Extract text from first column
        for col in df.columns:
            for _, row in df.iterrows():
                cell_value = str(row[col]).strip()
                if cell_value and cell_value != "nan" and len(cell_value) > 10:
                    # Skip headers
                    if "assumption" in cell_value.lower() or "risk" in cell_value.lower():
                        if len(cell_value) < 50:  # Likely a header
                            continue
                    assumptions.append(cell_value)

        return assumptions

    def _parse_sizing_guidelines(self, xl: pd.ExcelFile, estimation_path: Path) -> Dict[str, str]:
        """Parse Sizing Guidelines sheet"""
        guidelines = {}

        sheet_name = self._find_sheet(xl.sheet_names, ["sizing", "guidelines"])
        if not sheet_name:
            return guidelines

        df = pd.read_excel(estimation_path, sheet_name=sheet_name)

        # Try to extract key-value pairs
        if len(df.columns) >= 2:
            for _, row in df.iterrows():
                key = str(row.iloc[0]).strip()
                value = str(row.iloc[1]).strip()

                if key and key != "nan" and value and value != "nan":
                    guidelines[key] = value

        return guidelines
