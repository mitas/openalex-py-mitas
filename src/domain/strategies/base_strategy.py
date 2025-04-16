# src/domain/strategies/base_strategy.py
from abc import abstractmethod
from typing import Optional

from loguru import logger

from src.utils.text_normalizer import TextNormalizer
from ..interfaces.search_strategy import SearchStrategy
from ..models.reference import Reference


class BaseStrategy(SearchStrategy):
    """Base class for search strategies."""

    def normalize_text(self, text: Optional[str]) -> str:
        """Normalize text using the central TextNormalizer."""
        return TextNormalizer.normalize_text(text)

    def log_attempt(
        self, reference: Reference, result_count: int, error: Optional[str] = None
    ) -> None:
        """Log search attempt details."""
        try:
            # Use reference ID or Title for logging context
            ref_identifier = reference.doi or reference.pmid or reference.title or "Unknown Ref"
            error_msg = f", Error: {error}" if error else ""
            logger.info(
                f"Strategy: {self.name}, Ref: '{ref_identifier:.50}', "
                f"Results: {result_count}{error_msg}"
            )
        except Exception as e:
            logger.warning(f"Failed to log attempt for strategy {self.name}: {e}")
            # Fail silently to avoid stopping execution


    @abstractmethod
    def validate_reference(self, reference: Reference) -> bool:
        """Validate that the reference contains required data for this strategy."""
        pass
