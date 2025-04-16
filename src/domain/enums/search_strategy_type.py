# src/domain/enums/search_strategy_type.py
"""Enum for search strategy types (simplified)."""

from enum import Enum

class SearchStrategyType(str, Enum):
    """Enum for types of search strategies with priorities (simplified)."""

    IDENTIFIER = "identifier"  # Combined DOI & PMID
    TITLE_AUTHORS_YEAR = "title_authors_year"
    TITLE_AUTHORS = "title_authors"
    TITLE_YEAR = "title_year"
    TITLE_ONLY = "title_only" # Fallback

    @property
    def priority(self) -> int:
        """Return the priority of the search strategy."""
        priorities = {
            self.IDENTIFIER: 1, # Highest
            self.TITLE_AUTHORS_YEAR: 2,
            self.TITLE_AUTHORS: 3,
            self.TITLE_YEAR: 4,
            self.TITLE_ONLY: 5,  # Lowest
        }
        return priorities[self]

    @classmethod
    def from_string(cls, value: str) -> "SearchStrategyType":
        """Convert a string to a SearchStrategyType enum value."""
        try:
            return cls(value.lower())
        except ValueError as e:
            raise ValueError(f"Invalid search strategy type: {value}") from e
