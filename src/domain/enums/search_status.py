# src/domain/enums/search_status.py
"""Enum for search status."""

from enum import Enum


class SearchStatus(str, Enum):
    """Enum for the status of a search operation."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    REJECTED = "rejected"
    SKIPPED = "skipped"

    @classmethod
    def from_string(cls, value: str) -> "SearchStatus":
        """Convert a string to a SearchStatus enum value."""
        try:
            return cls(value.lower())
        except ValueError as e:
            raise ValueError(f"Invalid search status: {value}") from e
