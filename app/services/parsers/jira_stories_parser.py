"""
Jira Stories Parser

Parses jira_stories.xlsx files for reference stories.
Extracts existing Jira stories to use as templates.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===== Pydantic Models =====

class JiraStory(BaseModel):
    """Individual Jira story"""

    jira_id: str = Field(..., description="Jira story ID (e.g., INV-1001)")
    description: str = Field(..., description="User story description")
    story_points: Optional[int] = Field(None, description="Story points if available")
    priority: Optional[str] = Field(None, description="Priority (High, Medium, Low)")
    status: Optional[str] = Field(None, description="Status (To Do, In Progress, Done)")


class JiraStoriesDocument(BaseModel):
    """Complete Jira stories document"""

    project_id: str = Field(..., description="Project ID")
    stories: List[JiraStory] = Field(default_factory=list, description="List of existing stories")


# ===== Parser Class =====

class JiraStoriesParser:
    """Parse jira_stories.xlsx into structured JiraStoriesDocument"""

    async def parse(self, jira_path: Path) -> JiraStoriesDocument:
        """
        Parse Jira stories Excel file

        Args:
            jira_path: Path to jira_stories.xlsx file

        Returns:
            JiraStoriesDocument with extracted stories

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If parsing fails
        """
        if not jira_path.exists():
            raise FileNotFoundError(f"Jira stories file not found: {jira_path}")

        logger.info(f"Parsing jira stories: {jira_path.name}")

        # Extract project ID
        project_id = self._extract_project_id(jira_path)

        # Load Excel file
        # Try "Jira Stories" sheet first, fallback to first sheet
        try:
            df = pd.read_excel(jira_path, sheet_name="Jira Stories")
        except Exception:
            logger.warning("'Jira Stories' sheet not found, using first sheet")
            df = pd.read_excel(jira_path, sheet_name=0)

        # Parse stories
        stories = self._parse_stories(df)

        logger.info(f"Parsed {len(stories)} Jira stories")

        return JiraStoriesDocument(
            project_id=project_id,
            stories=stories,
        )

    def _extract_project_id(self, jira_path: Path) -> str:
        """Extract project ID from file path"""
        folder_name = jira_path.parent.name
        match = re.match(r"(PRJ-\d+)", folder_name)
        if match:
            return match.group(1)
        return folder_name

    def _parse_stories(self, df: pd.DataFrame) -> List[JiraStory]:
        """Parse stories from DataFrame"""
        stories = []

        # Normalize column names to lowercase
        df.columns = [str(col).lower().strip() for col in df.columns]

        # Find key columns
        id_col = self._find_column(df, ["jiraid", "jira_id", "story_id", "id", "key"])
        desc_col = self._find_column(df, ["jira_description", "description", "summary", "story"])
        points_col = self._find_column(df, ["story_points", "story points", "points"])
        priority_col = self._find_column(df, ["priority"])
        status_col = self._find_column(df, ["status"])

        if not id_col or not desc_col:
            logger.warning("Could not find ID or description columns in Jira stories")
            return stories

        # Parse each row
        for _, row in df.iterrows():
            jira_id = str(row[id_col]).strip()
            description = str(row[desc_col]).strip()

            # Skip empty rows
            if not jira_id or jira_id == "nan" or not description or description == "nan":
                continue

            # Extract optional fields
            story_points = None
            if points_col:
                try:
                    points_val = row[points_col]
                    if pd.notna(points_val):
                        story_points = int(float(points_val))
                except (ValueError, TypeError):
                    pass

            priority = None
            if priority_col:
                priority = str(row[priority_col]).strip()
                if priority == "nan":
                    priority = None

            status = None
            if status_col:
                status = str(row[status_col]).strip()
                if status == "nan":
                    status = None

            story = JiraStory(
                jira_id=jira_id,
                description=description,
                story_points=story_points,
                priority=priority,
                status=status,
            )
            stories.append(story)

        return stories

    def _find_column(self, df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """Find column by keywords (case insensitive)"""
        df_cols = [str(col).lower() for col in df.columns]

        for keyword in keywords:
            for col in df_cols:
                if keyword in col:
                    # Return original column name
                    col_idx = df_cols.index(col)
                    return df.columns[col_idx]

        return None
