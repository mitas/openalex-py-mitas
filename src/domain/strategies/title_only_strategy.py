# src/domain/strategies/title_only_strategy.py
from typing import Any, Dict, List, Tuple

from rapidfuzz import fuzz
from loguru import logger

from ..enums.search_strategy_type import SearchStrategyType
from ..interfaces.publication_repository import PublicationRepository
from ..models.config import Config
from ..models.reference import Reference
from .base_strategy import BaseStrategy


class TitleOnlyStrategy(BaseStrategy):
    """Strategy for searching publications by title only (Fallback)."""

    def __init__(self, publication_repository: PublicationRepository, config: Config):
        self.publication_repository = publication_repository
        self.config = config
        # Determine the effective threshold for this strategy (higher)
        self.effective_title_threshold = getattr(
            config,
            'title_only_similarity_threshold', # Check if specific threshold exists in config
            min(config.title_similarity_threshold + 0.10, 1.0) # Otherwise, significantly higher than base
        )
        logger.debug(f"{self.name}: Effective title threshold set to {self.effective_title_threshold:.2f}")


    @property
    def name(self) -> str:
        return SearchStrategyType.TITLE_ONLY.value

    @property
    def priority(self) -> int:
        # Updated priority
        return SearchStrategyType.TITLE_ONLY.priority

    def supported(self, reference: Reference) -> bool:
        return reference.title is not None and reference.title.strip() != ""

    def validate_reference(self, reference: Reference) -> bool:
        if not self.supported(reference): return False
        if len(self.normalize_text(reference.title)) < 4:
             raise ValueError("Title too short for reliable matching")
        return True

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        norm_title1 = self.normalize_text(title1)
        norm_title2 = self.normalize_text(title2)
        return fuzz.WRatio(norm_title1, norm_title2) / 100.0

    def _filter_and_rank_results(
        self, reference: Reference, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not results: return []
        scored_results = []

        for result in results:
            title_similarity = self._calculate_title_similarity(reference.title or "", result.get("title", ""))
            # Use the adjusted (higher) threshold
            if title_similarity < self.effective_title_threshold:
                continue

            # Ranking only by title similarity
            combined_score = title_similarity
            result["_debug"] = {
                "title_similarity": title_similarity,
                "combined_score": combined_score,
            }
            scored_results.append((result, combined_score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [result for result, _ in scored_results]

    def execute(
        self, reference: Reference
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        metadata = {
            "strategy": self.name,
            "query_type": "title search",
            "search_term": reference.title or "",
        }
        try:
            self.validate_reference(reference)
            results = self.publication_repository.search_by_title(reference.title or "")
            initial_count = len(results)
            filtered_results = self._filter_and_rank_results(reference, results)

            if filtered_results:
                self.log_attempt(reference, len(filtered_results))
                return filtered_results, metadata
            else:
                error_msg = "No results found"
                if initial_count > 0:
                    error_msg = f"Results found but similarity below threshold ({self.effective_title_threshold:.2f})"
                self.log_attempt(reference, 0, error=error_msg)
                metadata["error"] = error_msg
                return [], metadata

        except ValueError as ve:
            self.log_attempt(reference, 0, error=str(ve))
            metadata["error"] = f"Validation error: {str(ve)}"
            return [], metadata
        except Exception as e:
            self.log_attempt(reference, 0, error=f"API error: {e}")
            metadata["error"] = f"API error: {str(e)}"
            return [], metadata
