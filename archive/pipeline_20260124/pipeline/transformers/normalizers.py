"""
Data normalization utilities for transformers.

Provides functions to normalize various data types from
extracted document data to the formats required by target schemas.
"""

import json
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, List, Optional, Union


def date_normalizer(value: Any) -> Optional[date]:
    """
    Normalize various date formats to Python date object.

    Handles:
    - ISO format: 2025-01-15
    - US format: 1/15/2025, 01/15/2025
    - EU format: 15-01-2025, 15/01/2025
    - Written: Jan 15, 2025, January 15 2025
    - Excel serial dates (numeric)

    Args:
        value: Date value in various formats

    Returns:
        Python date object or None if parsing fails
    """
    if value is None:
        return None

    # Already a date
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    # datetime -> extract date
    if isinstance(value, datetime):
        return value.date()

    # Excel serial date (numeric)
    if isinstance(value, (int, float)):
        try:
            # Excel serial date: days since 1899-12-30
            # (Excel incorrectly treats 1900 as leap year)
            if 1 < value < 100000:  # Reasonable date range
                from datetime import timedelta

                base = date(1899, 12, 30)
                return base + timedelta(days=int(value))
        except Exception:
            pass
        return None

    # String parsing
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # Try ISO format first (most reliable)
        iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", value)
        if iso_match:
            try:
                return date(
                    int(iso_match.group(1)),
                    int(iso_match.group(2)),
                    int(iso_match.group(3)),
                )
            except ValueError:
                pass

        # US format: M/D/YYYY or MM/DD/YYYY
        us_match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", value)
        if us_match:
            try:
                year = int(us_match.group(3))
                if year < 100:
                    year += 2000 if year < 50 else 1900
                return date(year, int(us_match.group(1)), int(us_match.group(2)))
            except ValueError:
                pass

        # EU format: D-M-YYYY or DD-MM-YYYY
        eu_match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})$", value)
        if eu_match:
            try:
                year = int(eu_match.group(3))
                if year < 100:
                    year += 2000 if year < 50 else 1900
                return date(year, int(eu_match.group(2)), int(eu_match.group(1)))
            except ValueError:
                pass

        # Written format: Jan 15, 2025 or January 15 2025
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        written_match = re.match(
            r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", value
        )
        if written_match:
            month_str = written_match.group(1).lower()[:3]
            if month_str in months:
                try:
                    return date(
                        int(written_match.group(3)),
                        months[month_str],
                        int(written_match.group(2)),
                    )
                except ValueError:
                    pass

    return None


def datetime_normalizer(value: Any) -> Optional[datetime]:
    """
    Normalize various datetime formats to Python datetime with timezone.

    Handles same formats as date_normalizer plus time components.
    Always returns UTC timezone if none specified.

    Args:
        value: Datetime value in various formats

    Returns:
        Python datetime object with timezone or None
    """
    if value is None:
        return None

    # Already a datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    # Date -> datetime at midnight UTC
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)

    # String parsing
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        # Try ISO format with time
        try:
            # Handle 'Z' suffix
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

        # Fall back to date parsing + midnight
        d = date_normalizer(value)
        if d:
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)

    return None


def array_to_json_string(value: Any) -> str:
    """
    Convert various array representations to JSON string.

    Handles:
    - Python lists
    - Comma-separated strings
    - JSON strings (pass through)
    - Single values (wrap in array)

    Args:
        value: Array value in various formats

    Returns:
        JSON array string
    """
    if value is None:
        return "[]"

    # Already a JSON string
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                # Validate and re-serialize for consistency
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return json.dumps(parsed)
            except json.JSONDecodeError:
                pass

        # Comma-separated string
        if "," in value:
            items = [item.strip() for item in value.split(",") if item.strip()]
            return json.dumps(items)

        # Single value
        if value:
            return json.dumps([value])
        return "[]"

    # List
    if isinstance(value, list):
        return json.dumps(value)

    # Single value
    return json.dumps([str(value)])


def dict_to_json_string(value: Any) -> str:
    """
    Convert dictionary to JSON string.

    Handles:
    - Python dicts
    - JSON strings (pass through)
    - None (empty object)

    Args:
        value: Dictionary value

    Returns:
        JSON object string
    """
    if value is None:
        return "{}"

    # Already a JSON string
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return json.dumps(parsed)
            except json.JSONDecodeError:
                pass
        return "{}"

    # Dict
    if isinstance(value, dict):
        return json.dumps(value)

    return "{}"


def enum_normalizer(
    value: Any,
    allowed: List[str],
    default: Optional[str] = None,
    case_sensitive: bool = False,
) -> Optional[str]:
    """
    Normalize value to one of allowed enum values.

    Performs case-insensitive matching and fuzzy matching for
    common variations.

    Args:
        value: Value to normalize
        allowed: List of allowed enum values
        default: Default value if no match found
        case_sensitive: Whether matching is case-sensitive

    Returns:
        Matched enum value or default
    """
    if value is None:
        return default

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()
    if not value:
        return default

    # Exact match
    if value in allowed:
        return value

    # Case-insensitive match
    if not case_sensitive:
        value_lower = value.lower()
        for a in allowed:
            if a.lower() == value_lower:
                return a

    # Fuzzy matching for common variations
    # Handle "In Progress" vs "InProgress" vs "in_progress"
    value_normalized = re.sub(r"[_\-\s]+", "", value.lower())
    for a in allowed:
        a_normalized = re.sub(r"[_\-\s]+", "", a.lower())
        if a_normalized == value_normalized:
            return a

    # Partial match (value contains enum or enum contains value)
    for a in allowed:
        if value_lower in a.lower() or a.lower() in value_lower:
            return a

    return default


def email_normalizer(value: Any) -> Optional[str]:
    """
    Normalize and validate email address.

    Args:
        value: Email value

    Returns:
        Lowercase validated email or None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip().lower()
    if not value:
        return None

    # Basic email regex validation
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if re.match(email_pattern, value):
        return value

    # Try to extract email from text
    match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", value)
    if match:
        return match.group().lower()

    return None


def clean_text(value: Any) -> str:
    """
    Clean and normalize text content.

    - Strips whitespace
    - Normalizes unicode
    - Removes control characters
    - Normalizes line breaks

    Args:
        value: Text value

    Returns:
        Cleaned text string
    """
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    # Normalize unicode
    value = unicodedata.normalize("NFKC", value)

    # Remove control characters (except newlines and tabs)
    value = "".join(
        char for char in value
        if unicodedata.category(char) != "Cc" or char in "\n\t"
    )

    # Normalize line breaks
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    # Strip and collapse whitespace (preserve single spaces and newlines)
    lines = [" ".join(line.split()) for line in value.split("\n")]
    value = "\n".join(lines)

    return value.strip()


def number_normalizer(value: Any, default: float = 0.0) -> float:
    """
    Normalize various number representations to float.

    Args:
        value: Number value
        default: Default if parsing fails

    Returns:
        Float value
    """
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return default

        # Remove currency symbols and thousands separators
        value = re.sub(r"[$€£¥,]", "", value)

        try:
            return float(value)
        except ValueError:
            pass

    return default


def integer_normalizer(value: Any, default: int = 0) -> int:
    """
    Normalize various number representations to integer.

    Args:
        value: Number value
        default: Default if parsing fails

    Returns:
        Integer value
    """
    return int(number_normalizer(value, float(default)))
