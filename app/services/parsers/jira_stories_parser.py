"""
Jira Stories Parser

Generic Excel text extractor for LLM context.
Extracts all text content from Jira stories Excel files without schema assumptions.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===== Pydantic Models =====


class SheetContent(BaseModel):
    """Extracted content from a single sheet"""

    sheet_name: str = Field(..., description="Name of the Excel sheet")
    text_content: str = Field("", description="Flat text extracted from the sheet")
    row_count: int = Field(0, description="Number of data rows")
    column_names: List[str] = Field(default_factory=list, description="Column headers")


class JiraStoriesDocument(BaseModel):
    """Generic extracted document structure"""

    project_id: str = Field(..., description="Project ID from folder name")
    file_name: str = Field(..., description="Source file name")
    sheet_count: int = Field(0, description="Number of sheets in workbook")
    sheets: List[SheetContent] = Field(default_factory=list, description="Content per sheet")
    full_text: str = Field("", description="All sheets combined as flat text for LLM")


# ===== Parser Class =====


class JiraStoriesParser:
    """Generic Excel parser - extracts all text without schema assumptions"""

    async def parse(self, jira_path: Path) -> JiraStoriesDocument:
        """
        Parse any Jira stories Excel file into flat text format.

        Args:
            jira_path: Path to Excel file (.xlsx, .xls)

        Returns:
            JiraStoriesDocument with extracted text from all sheets

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not jira_path.exists():
            raise FileNotFoundError(f"File not found: {jira_path}")

        logger.info(f"Parsing Jira stories file: {jira_path.name}")

        try:
            xl = pd.ExcelFile(jira_path)
        except Exception as e:
            raise ValueError(f"Failed to open Excel file: {e}")

        logger.info(f"Found {len(xl.sheet_names)} sheets: {xl.sheet_names}")

        project_id = self._extract_project_id(jira_path)
        sheets: List[SheetContent] = []
        all_text_parts: List[str] = []

        for sheet_name in xl.sheet_names:
            sheet_content = self._extract_sheet_text(jira_path, sheet_name)
            sheets.append(sheet_content)

            # Add to combined text with sheet header
            if sheet_content.text_content.strip():
                all_text_parts.append(f"=== {sheet_name} ===\n{sheet_content.text_content}")

        full_text = "\n\n".join(all_text_parts)

        logger.info(
            f"Extracted {len(sheets)} sheets, "
            f"total {len(full_text)} characters"
        )

        return JiraStoriesDocument(
            project_id=project_id,
            file_name=jira_path.name,
            sheet_count=len(sheets),
            sheets=sheets,
            full_text=full_text,
        )

    def _extract_sheet_text(self, file_path: Path, sheet_name: str) -> SheetContent:
        """
        Extract all text from a single sheet as flat text.

        Each row becomes a line with cell values separated by " | ".
        Empty cells are skipped.
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        except Exception as e:
            logger.warning(f"Failed to read sheet '{sheet_name}': {e}")
            return SheetContent(sheet_name=sheet_name)

        if df.empty:
            return SheetContent(sheet_name=sheet_name)

        # Extract column names from first row (if it looks like headers)
        first_row = df.iloc[0] if len(df) > 0 else pd.Series()
        column_names = [str(v) for v in first_row.values if pd.notna(v) and str(v).strip()]

        # Convert all cells to text, row by row
        text_lines: List[str] = []

        for _, row in df.iterrows():
            # Get non-empty cell values
            cell_values = []
            for val in row.values:
                if pd.notna(val):
                    text = str(val).strip()
                    if text and text.lower() != "nan":
                        cell_values.append(text)

            if cell_values:
                text_lines.append(" | ".join(cell_values))

        return SheetContent(
            sheet_name=sheet_name,
            text_content="\n".join(text_lines),
            row_count=len(text_lines),
            column_names=column_names,
        )

    def _extract_project_id(self, file_path: Path) -> str:
        """Extract project ID from folder name or file name"""
        # Try folder name first (e.g., PRJ-001)
        folder_name = file_path.parent.name
        match = re.match(r"(PRJ-\d+)", folder_name)
        if match:
            return match.group(1)

        # Try file name
        file_stem = file_path.stem
        match = re.match(r"(PRJ-\d+)", file_stem)
        if match:
            return match.group(1)

        # Fall back to folder name
        return folder_name
