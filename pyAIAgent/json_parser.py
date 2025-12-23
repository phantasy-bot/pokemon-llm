import json
import re

from typing import Any, Optional


def parse_optional_fenced_json(text: str) -> Any:
    """
    Parses JSON from `text`.

    The JSON may be either:
      - Enclosed in triple-backtick fences
      - Plain JSON without fences

    Args:
        text: The text string to parse

    Returns:
        The deserialized Python object.
    """
    # Try to find a fenced JSON block first
    fence_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    m = re.search(fence_pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if m:
        json_str = m.group(1)
    else:
        # No fence: assume the entire text is JSON
        json_str = text.strip()

    try:
        j = json.loads(json_str)
        return j
    except json.JSONDecodeError:
        return {}
