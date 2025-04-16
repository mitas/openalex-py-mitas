# src/domain/strategies/title_authors_year_strategy.py
from typing import Any, Dict, List, Tuple

from rapidfuzz import fuzz, process
from loguru import logger

from ..enums.search_strategy_type import SearchStrategyType
from ..interfaces.publication_repository import PublicationRepository
from ..models.config import Config
from ..models.reference import Reference
from .base_strategy import BaseStrategy


class TitleAuthorsYearStrategy(BaseStrategy):
    """Strategy for searching publications by title, authors, and year."""

    def __init__(self, publication_repository: PublicationRepository, config: Config):
        self.publication_repository = publication_repository
        self.config = config

    @property
    def name(self) -> str:
        return SearchStrategyType.TITLE_AUTHORS_YEAR.value

    @property
    def priority(self) -> int:
        # Updated priority
        return SearchStrategyType.TITLE_AUTHORS_YEAR.priority

    def supported(self, reference: Reference) -> bool:
        has_title = reference.title is not None and reference.title.strip() != ""
        has_authors = (
            reference.authors is not None
            and isinstance(reference.authors, list)
            and len(reference.authors) > 0
            and any(a and a.strip() for a in reference.authors) # Ensure authors are not just empty strings
        )
        has_year = reference.year is not None
        return has_title and has_authors and has_year

    def validate_reference(self, reference: Reference) -> bool:
        if not self.supported(reference):
             return False # Basic check failed
        if len(self.normalize_text(reference.title)) < 4:
             raise ValueError("Title too short for reliable matching")
        if reference.year <= 0:
             raise ValueError("Invalid publication year")
        # Add more specific validation if needed
        return True

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        norm_title1 = self.normalize_text(title1)
        norm_title2 = self.normalize_text(title2)
        # Using WRatio which handles various types of differences well
        return fuzz.WRatio(norm_title1, norm_title2) / 100.0

    def _calculate_authors_similarity(
        self, ref_authors: List[str], pub_authorships: List[Dict[str, Any]]
    ) -> float:
        if not ref_authors or not pub_authorships:
            return 0.0

        pub_author_names = [
            self.normalize_text(authorship.get("author", {}).get("display_name", ""))
            for authorship in pub_authorships
            if authorship.get("author", {}).get("display_name")
        ]
        if not pub_author_names:
            return 0.0

        normalized_ref_authors = [self.normalize_text(author) for author in ref_authors if author]
        if not normalized_ref_authors:
             return 0.0

        # Use process.extract to find best matches efficiently
        total_score = 0
        match_count = 0
        # Limit comparison to avoid excessive computation if lists are huge
        limit = min(len(normalized_ref_authors), len(pub_author_names), 10)

        # Compare first few authors using token_set_ratio for flexibility
        for ref_author in normalized_ref_authors[:limit]:
            best_match = process.extractOne(ref_author, pub_author_names, scorer=fuzz.token_set_ratio)
            if best_match:
                total_score += best_match[1] # Score is 0-100
                match_count += 1

        # Average score, normalized to 0-1
        return (total_score / match_count / 100.0) if match_count > 0 else 0.0


    def _filter_and_rank_results(
        self, reference: Reference, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not results:
            return []

        scored_results = []
        threshold_title = self.config.title_similarity_threshold
        threshold_author = self.config.author_similarity_threshold

        for result in results:
            # Year must match exactly
            if result.get("publication_year") != reference.year:
                continue

            title_similarity = self._calculate_title_similarity(
                reference.title or "", result.get("title", "")
            )
            if title_similarity < threshold_title:
                continue

            authors_similarity = self._calculate_authors_similarity(
                reference.authors or [], result.get("authorships", [])
            )
            if authors_similarity < threshold_author:
                continue

            # Combine scores (adjust weights as needed)
            combined_score = (
                title_similarity * 0.60 + authors_similarity * 0.40
            )

            result["_debug"] = {
                "title_similarity": title_similarity,
                "authors_similarity": authors_similarity,
                "year_match": True,
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
            "query_type": "title, authors, year search",
            "search_term": reference.title or "",
        }
        try:
            self.validate_reference(reference)
            results = self.publication_repository.search_by_title_authors_year(
                reference.title or "", reference.authors or [], reference.year or 0
            )
            initial_count = len(results)
            filtered_results = self._filter_and_rank_results(reference, results)

            if filtered_results:
                self.log_attempt(reference, len(filtered_results))
                return filtered_results, metadata
            else:
                error_msg = "No results found"
                if initial_count > 0:
                    error_msg = f"Results found but similarity below threshold (T>{threshold_title:.2f}, A>{threshold_author:.2f}) or year mismatch"
                self.log_attempt(reference, 0, error=error_msg)
                metadata["error"] = error_msg
                return [], metadata

        except ValueError as ve: # Catch validation errors
            self.log_attempt(reference, 0, error=str(ve))
            metadata["error"] = f"Validation error: {str(ve)}"
            return [], metadata
        except Exception as e:
            self.log_attempt(reference, 0, error=f"API error: {e}")
            metadata["error"] = f"API error: {str(e)}"
            return [], metadata
