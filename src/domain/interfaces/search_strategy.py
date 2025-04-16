# src/domain/interfaces/search_strategy.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

from ..models.reference import Reference


class SearchStrategy(ABC):
    """Interface for search strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the strategy."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Return the priority of the strategy."""
        pass

    @abstractmethod
    def supported(self, reference: Reference) -> bool:
        """Check if the strategy can be used for the given reference."""
        pass

    @abstractmethod
    def execute(
        self, reference: Reference
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Execute the search strategy for the given reference."""
        pass
