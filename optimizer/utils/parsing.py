from __future__ import annotations

import re

DEFAULT_WIDTH = 0.5


def parse_width(value: str) -> float | None:
    """Parse a width string into a value in meters.

    Handles several input formats:
    - Plain numeric strings (in meters)
    - Ranges like "1.5 - 3.0" (returns the average)
    - Imperial feet values like "6 ft", "6 feet", "6 foot"
    - Imperial inch values like "12 in", "12 inch", "12 inches"

    Args:
        value: A string representing a width measurement.

    Returns:
        The parsed width in meters, or None if the string is empty
        or doesn't match any recognized format.
    """
    value = value.strip()
    if not value:
        return None

    # Try direct numeric parse (assumed meters)
    try:
        return float(value)
    except ValueError:
        pass

    # Range
    m = re.match(r"^(\d+\.?\d*)\s*-\s*(\d+\.?\d*)$", value)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2

    # Feet → meters
    m = re.match(r"^(\d+\.?\d*)\s*(feet|foot|ft)\b", value, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 0.3048

    # Inches → meters
    m = re.match(r"^(\d+\.?\d*)\s*(inch|inches|in)\b", value, re.IGNORECASE)
    if m:
        return float(m.group(1)) * 0.0254

    return None
