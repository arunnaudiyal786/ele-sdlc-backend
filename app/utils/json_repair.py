"""JSON repair utilities for handling malformed LLM responses.

Local LLMs like phi3:mini often generate syntactically incorrect JSON with issues like:
- Unterminated strings (missing closing quotes)
- Truncated output (missing closing brackets)
- Unescaped special characters in strings
- Trailing commas before closing brackets
- Missing colons between keys and values

This module provides repair functions to handle these common issues.
"""

import json
import re
import logging
import os
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

# Debug mode: Set JSON_REPAIR_DISABLED=true to skip repair and see raw LLM output
JSON_REPAIR_DISABLED = os.environ.get("JSON_REPAIR_DISABLED", "false").lower() == "true"


def repair_json(raw: str) -> Tuple[Dict[str, Any], bool]:
    """
    Attempt to parse JSON, applying repairs if needed.

    Args:
        raw: Raw string that should contain JSON

    Returns:
        Tuple of (parsed_dict, was_repaired)

    Raises:
        json.JSONDecodeError: If JSON cannot be parsed even after repairs
    """
    # First, try parsing as-is
    try:
        return json.loads(raw), False
    except json.JSONDecodeError:
        pass

    # Apply repair strategies in order
    repaired = raw

    # Strategy 1: Extract JSON from surrounding text
    repaired = _extract_json_block(repaired)

    # Strategy 2: Fix missing colons between keys and values
    repaired = _fix_missing_colons(repaired)

    # Strategy 3: Fix unterminated strings
    repaired = _fix_unterminated_strings(repaired)

    # Strategy 4: Fix truncated objects inside arrays
    repaired = _fix_truncated_objects(repaired)

    # Strategy 5: Fix trailing commas
    repaired = _fix_trailing_commas(repaired)

    # Strategy 6: Balance brackets
    repaired = _balance_brackets(repaired)

    # Strategy 7: Fix unescaped characters
    repaired = _fix_unescaped_chars(repaired)

    # Try parsing the repaired JSON
    try:
        result = json.loads(repaired)
        logger.info("JSON repair successful")
        return result, True
    except json.JSONDecodeError as e:
        # Log what we tried for debugging
        logger.warning(f"JSON repair failed. Original: {raw[:200]}... Repaired: {repaired[:200]}...")
        raise


def _extract_json_block(text: str) -> str:
    """Extract JSON object from surrounding text or markdown."""
    # Remove markdown code blocks if present
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

    # Find the first { and last } to extract the JSON object
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    # Try array format
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')

    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return text[first_bracket:last_bracket + 1]

    return text.strip()


def _fix_missing_colons(text: str) -> str:
    """Fix missing colons between JSON keys and values.

    LLMs sometimes generate {"key" "value"} instead of {"key": "value"}.
    This detects key-value pairs where the colon is missing and inserts it.
    """
    # Pattern: quoted string followed by whitespace and then a value (without colon)
    # Value can be: another string, number, boolean, null, object, or array
    # We need to ensure we're in an object context (after { or ,) not array context

    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(text):
        char = text[i]

        # Handle escape sequences
        if escape_next:
            result.append(char)
            escape_next = False
            i += 1
            continue

        if char == '\\' and in_string:
            result.append(char)
            escape_next = True
            i += 1
            continue

        # Track string boundaries
        if char == '"':
            if not in_string:
                in_string = True
                result.append(char)
                i += 1
                continue
            else:
                # End of string - check if this might be a key missing its colon
                in_string = False
                result.append(char)
                i += 1

                # Look ahead for missing colon
                # Skip whitespace
                j = i
                while j < len(text) and text[j] in ' \t\n\r':
                    j += 1

                if j < len(text):
                    next_char = text[j]
                    # If next non-whitespace is a value start (not : or , or } or ])
                    # then we might need to insert a colon
                    if next_char in '"0123456789-tfn{[':
                        # Check it's not already properly followed by colon
                        # Look back to see if we're in object context (after { or ,)
                        lookback = ''.join(result).rstrip()
                        if lookback:
                            # Find the last structural character before this string
                            for k in range(len(lookback) - 1, -1, -1):
                                if lookback[k] in '{[:,':
                                    # After { or , = this is likely a key
                                    # After : = this is a value
                                    # After [ = array element
                                    if lookback[k] in '{,':
                                        # This was a key, insert colon
                                        result.append(':')
                                    break
                continue

        result.append(char)
        i += 1

    return ''.join(result)


def _fix_unterminated_strings(text: str) -> str:
    """Fix strings that are missing closing quotes."""
    # This handles the common case where LLM truncates mid-string
    # Pattern: "key": "value without closing quote

    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        # Check if line has an odd number of unescaped quotes
        quote_count = len(re.findall(r'(?<!\\)"', line))

        if quote_count % 2 == 1:
            # Odd number of quotes - likely unterminated string
            stripped = line.rstrip()
            # Add closing quote if line doesn't end with common JSON endings
            if stripped and not stripped.endswith(('"', ',', '{', '}', '[', ']', ':')):
                line = stripped + '"'
            elif stripped and stripped.endswith(','):
                # Case: "value,  -> should be "value",
                line = stripped[:-1] + '",'

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def _fix_truncated_objects(text: str) -> str:
    """Fix objects inside arrays that were truncated.

    This handles the case where an LLM cuts off mid-object inside an array,
    leaving something like: [{"name": "value" ] where the inner } is missing.
    """
    # Pattern: string followed by whitespace and ] without closing }
    # This regex finds cases like: "value" followed by ] without a } in between
    pattern = r'("(?:[^"\\]|\\.)*")\s*(\])'

    def check_and_fix(match):
        string_part = match.group(1)
        bracket = match.group(2)

        # Get text before this match to check context
        start = match.start()
        prefix = text[:start]

        # Count unclosed braces before this point
        open_count = prefix.count('{') - prefix.count('}')

        if open_count > 0:
            # There's an unclosed brace - we need to close it
            return string_part + '}' + bracket
        return match.group(0)

    return re.sub(pattern, check_and_fix, text)


def _fix_trailing_commas(text: str) -> str:
    """Remove trailing commas before closing brackets."""
    # Remove comma before } or ]
    text = re.sub(r',\s*([\}\]])', r'\1', text)
    return text


def _balance_brackets(text: str) -> str:
    """Add missing closing brackets in the correct order."""
    # Track bracket order as we scan
    stack = []
    in_string = False
    i = 0

    while i < len(text):
        char = text[i]

        # Handle string boundaries (skip escaped quotes)
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
        elif not in_string:
            if char in '{[':
                stack.append(char)
            elif char == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif char == ']':
                if stack and stack[-1] == '[':
                    stack.pop()
        i += 1

    # Build closing brackets in reverse order
    if stack:
        text = text.rstrip()
        # Remove trailing comma if present
        if text.endswith(','):
            text = text[:-1]

        closers = {'[': ']', '{': '}'}
        for opener in reversed(stack):
            text += closers[opener]

    return text


def _fix_unescaped_chars(text: str) -> str:
    """Fix common unescaped characters in JSON strings."""
    # Fix unescaped newlines within strings (not between JSON elements)
    # This is tricky - we need to be careful not to break valid JSON

    # Fix control characters that should be escaped
    result = []
    in_string = False
    i = 0

    while i < len(text):
        char = text[i]

        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            result.append(char)
        elif in_string and char == '\n':
            # Replace literal newline in string with escaped version
            result.append('\\n')
        elif in_string and char == '\t':
            result.append('\\t')
        elif in_string and char == '\r':
            result.append('\\r')
        else:
            result.append(char)

        i += 1

    return ''.join(result)


def parse_llm_json(raw: str, component_name: str = "unknown") -> Dict[str, Any]:
    """
    Parse JSON from LLM response with automatic repair.

    This is the main entry point for parsing LLM JSON responses.
    It attempts repair and provides detailed logging.

    Args:
        raw: Raw LLM response string
        component_name: Name of the component for logging

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If JSON cannot be parsed even after repairs
    """
    if not raw or not raw.strip():
        raise json.JSONDecodeError("Empty response", raw or "", 0)

    # Always log raw output for debugging
    logger.info(f"[{component_name}] RAW LLM OUTPUT:\n{raw[:1000]}{'...' if len(raw) > 1000 else ''}")

    # Debug mode: skip repair to see raw parsing results
    if JSON_REPAIR_DISABLED:
        logger.warning(f"[{component_name}] JSON_REPAIR_DISABLED=true - attempting direct parse without repair")
        return json.loads(raw)

    try:
        result, was_repaired = repair_json(raw)
        if was_repaired:
            logger.info(f"[{component_name}] JSON was repaired before parsing")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[{component_name}] Failed to parse JSON even after repair: {e}")
        logger.debug(f"[{component_name}] Raw response: {raw[:500]}")
        raise
