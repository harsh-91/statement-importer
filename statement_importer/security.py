# Created by Harsh (@harsh-91) | Made in India
from __future__ import annotations

from typing import Any


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def safe_spreadsheet_cell(value: Any) -> Any:
    """Prevent exported text from being interpreted as a spreadsheet formula."""
    if not isinstance(value, str):
        return value
    if value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def safe_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: safe_spreadsheet_cell(value) for key, value in row.items()}
