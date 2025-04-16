# src/domain/enums/study_type.py
"""Enum for study types."""

from enum import Enum


class StudyType(str, Enum):
    """Enum for types of studies in a systematic review."""

    INCLUDED = "included"
    EXCLUDED = "excluded"

    @classmethod
    def from_string(cls, value: str) -> "StudyType":
        """Convert a string to a StudyType enum value."""
        try:
            return cls(value.lower())
        except ValueError as e:
            raise ValueError(f"Invalid study type: {value}") from e
