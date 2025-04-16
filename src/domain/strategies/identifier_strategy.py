# src/domain/strategies/identifier_strategy.py
import re
from typing import Any, Dict, List, Tuple, Optional

from ..enums.search_strategy_type import SearchStrategyType
from ..interfaces.publication_repository import PublicationRepository
from ..models.reference import Reference
from .base_strategy import BaseStrategy


class IdentifierStrategy(BaseStrategy):
    """Strategy for searching publications by DOI or PMID."""

    def __init__(self, publication_repository: PublicationRepository):
        self.publication_repository = publication_repository

    @property
    def name(self) -> str:
        return SearchStrategyType.IDENTIFIER.value

    @property
    def priority(self) -> int:
        return SearchStrategyType.IDENTIFIER.priority

    def supported(self, reference: Reference) -> bool:
        has_doi = reference.doi is not None and reference.doi.strip() != ""
        has_pmid = reference.pmid is not None and reference.pmid.strip() != ""
        return has_doi or has_pmid

    def _validate_doi(self, doi: Optional[str]) -> bool:
        if not doi or not doi.strip():
            return False
        # Basic DOI pattern, may need refinement for edge cases
        doi_pattern = r"^10\.\d{4,}/[-._;()/:A-Za-z0-9]+$"
        return bool(re.match(doi_pattern, doi.strip()))

    def _validate_pmid(self, pmid: Optional[str]) -> bool:
        if not pmid or not pmid.strip():
            return False
        pmid_pattern = r"^\d+$"
        return bool(re.match(pmid_pattern, pmid.strip()))

    def validate_reference(self, reference: Reference) -> bool:
        """Validate DOI or PMID format if present."""
        doi_valid = not reference.doi or self._validate_doi(reference.doi)
        pmid_valid = not reference.pmid or self._validate_pmid(reference.pmid)

        if not doi_valid:
            raise ValueError(f"Invalid DOI format: {reference.doi}")
        if not pmid_valid:
            raise ValueError(f"Invalid PMID format: {reference.pmid}")

        # At least one must be present and valid if supported is true
        return self.supported(reference) and (doi_valid or pmid_valid)

    def execute(
        self, reference: Reference
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Execute DOI search, then PMID search if DOI fails."""
        results: List[Dict[str, Any]] = []
        metadata: Dict[str, Any] = {"strategy": self.name}
        error_log: List[str] = []

        # 1. Attempt DOI
        if reference.doi and self._validate_doi(reference.doi):
            normalized_doi = reference.doi.strip()
            metadata["query_type"] = "doi filter"
            metadata["search_term"] = normalized_doi
            try:
                result = self.publication_repository.get_by_doi(normalized_doi)
                if result:
                    self.log_attempt(reference, 1)
                    return [result], metadata  # Success with DOI
                else:
                    error_log.append("DOI not found")
                    self.log_attempt(reference, 0, error="DOI not found")
            except Exception as e:
                error_log.append(f"DOI API error: {str(e)}")
                self.log_attempt(reference, 0, error=f"DOI API error: {e}")
                # Don't set metadata error yet, try PMID

        # 2. Attempt PMID (if DOI failed or was absent)
        if not results and reference.pmid and self._validate_pmid(reference.pmid):
            normalized_pmid = reference.pmid.strip()
            # Update metadata for PMID attempt
            metadata["query_type"] = "pmid filter"
            metadata["search_term"] = normalized_pmid
            try:
                result = self.publication_repository.get_by_pmid(normalized_pmid)
                if result:
                    self.log_attempt(reference, 1)
                    return [result], metadata  # Success with PMID
                else:
                    error_log.append("PMID not found")
                    self.log_attempt(reference, 0, error="PMID not found")
            except Exception as e:
                error_log.append(f"PMID API error: {str(e)}")
                self.log_attempt(reference, 0, error=f"PMID API error: {e}")

        # If we reach here, neither DOI nor PMID succeeded
        metadata["error"] = "; ".join(error_log) if error_log else "No identifier matched"
        # Ensure search term reflects what was tried
        if not reference.doi and reference.pmid:
             metadata["search_term"] = reference.pmid.strip()
        elif reference.doi and not reference.pmid:
             metadata["search_term"] = reference.doi.strip()
        else:
             metadata["search_term"] = f"DOI: {reference.doi}, PMID: {reference.pmid}"

        return [], metadata
