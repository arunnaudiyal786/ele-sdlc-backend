"""
Parser Factory

Returns appropriate parser based on filename.
"""

from typing import Union

from .tdd_parser import TDDParser
from .estimation_parser import EstimationParser
from .jira_stories_parser import JiraStoriesParser


class ParserFactory:
    """Factory for creating document parsers"""

    @staticmethod
    def get_parser(
        filename: str,
    ) -> Union[TDDParser, EstimationParser, JiraStoriesParser]:
        """
        Return appropriate parser based on filename

        Args:
            filename: Name of file to parse (e.g., "tdd.docx", "estimation.xlsx")

        Returns:
            Parser instance for the file type

        Raises:
            ValueError: If file type is not recognized
        """
        filename_lower = filename.lower()

        # TDD documents
        if "tdd" in filename_lower or filename_lower.endswith(".docx"):
            return TDDParser()

        # Estimation spreadsheets
        elif "estimation" in filename_lower or "estimate" in filename_lower:
            return EstimationParser()

        # Jira stories
        elif "jira" in filename_lower or "stories" in filename_lower or "story" in filename_lower:
            return JiraStoriesParser()

        else:
            raise ValueError(f"Unknown file type: {filename}")
