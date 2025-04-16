# src/application/services/matching_service.py
"""Matching service for coordinating the study-to-publication matching process."""

import importlib
from typing import Any, Dict, List, Tuple, Type

from loguru import logger

from src.domain.enums.search_status import SearchStatus
from src.domain.enums.search_strategy_type import SearchStrategyType
from src.domain.interfaces.publication_repository import PublicationRepository
from src.domain.interfaces.search_strategy import SearchStrategy
from src.domain.models.config import Config
from src.domain.models.search_result import SearchResult
from src.domain.models.study import Study
from src.infrastructure.repositories.openalex_repository import OpenAlexRepository
# Import new/updated strategies
from src.domain.strategies.identifier_strategy import IdentifierStrategy
from src.domain.strategies.title_authors_year_strategy import TitleAuthorsYearStrategy
from src.domain.strategies.title_authors_strategy import TitleAuthorsStrategy
from src.domain.strategies.title_year_strategy import TitleYearStrategy
from src.domain.strategies.title_only_strategy import TitleOnlyStrategy


class MatchingService:
    """
    Service that coordinates the matching of studies to publications.
    Initializes strategies and repository, and handles the matching process.
    """

    def __init__(self, config: Config):
        """Initialize the matching service with configuration."""
        self.repository: PublicationRepository = OpenAlexRepository(config)
        self.strategies: List[SearchStrategy] = self._initialize_strategies(config)
        self.config = config

    def _initialize_strategies(self, config: Config) -> List[SearchStrategy]:
        """Initialize all search strategies based on configuration."""
        disabled_strategies = {s.lower() for s in config.disable_strategies}
        strategies = []

        # Map strategy type enum to class and config requirements
        # Tuple: (StrategyClass, requires_config_object)
        strategy_map: Dict[SearchStrategyType, Tuple[Type[SearchStrategy], bool]] = {
            SearchStrategyType.IDENTIFIER: (IdentifierStrategy, False),
            SearchStrategyType.TITLE_AUTHORS_YEAR: (TitleAuthorsYearStrategy, True),
            SearchStrategyType.TITLE_AUTHORS: (TitleAuthorsStrategy, True),
            SearchStrategyType.TITLE_YEAR: (TitleYearStrategy, True),
            SearchStrategyType.TITLE_ONLY: (TitleOnlyStrategy, True),
        }

        # Iterate through defined strategy types in order
        for strategy_type in SearchStrategyType:
            if strategy_type not in strategy_map:
                logger.warning(f"Strategy type {strategy_type.value} not implemented in map, skipping.")
                continue

            if strategy_type.value in disabled_strategies:
                logger.info(f"Strategy {strategy_type.value} disabled by configuration.")
                continue

            strategy_class, requires_config = strategy_map[strategy_type]
            try:
                if requires_config:
                    strategy_instance = strategy_class(self.repository, config)
                else:
                    strategy_instance = strategy_class(self.repository)
                strategies.append(strategy_instance)
                logger.debug(f"Initialized strategy: {strategy_type.value} with priority {strategy_instance.priority}")

            except Exception as e:
                logger.error(f"Error initializing strategy {strategy_type.value}: {e}", exc_info=True)

        # Sort strategies by priority (lower number = higher priority)
        strategies.sort(key=lambda s: s.priority)
        logger.info(f"Initialized {len(strategies)} strategies in order: {[s.name for s in strategies]}")
        return strategies


    def match_study(self, study: Study) -> SearchResult:
        """Match a study to a publication using available strategies."""
        result = SearchResult(
            study_id=study.id,
            study_type=study.type,
            status=SearchStatus.NOT_FOUND, # Default
            search_attempts=[],
            original_reference=study.reference.to_dict(), # Zapisz oryginał w razie potrzeby
        )
        reference = study.reference

        # <<< --- DODANY LOG DEBUG --- >>>
        # Loguj dane wejściowe referencji na poziomie DEBUG
        # Używamy dict(exclude_none=True) dla czytelniejszego logu
        logger.debug(f"Study {study.id}: Processing reference data: {reference.dict(exclude_none=True)}")
        # <<< --- KONIEC DODANEGO LOGU --- >>>

        # Check minimal data using configured allowance for missing year
        if not reference.has_minimal_data(allow_missing_year=self.config.allow_missing_year):
            logger.warning(f"Study {study.id}: Insufficient data. Skipping search.")
            result.status = SearchStatus.SKIPPED
            # Zapisz oryginalną referencję, nawet jeśli pominięto
            result.original_reference = reference.to_dict()
            return result

        found_match = False
        final_rejection_reason = None # Track if any attempt was rejected

        for strategy in self.strategies:
            if found_match: # Skip remaining strategies if match found
                break

            if strategy.supported(reference):
                logger.info(f"Study {study.id}: Trying strategy '{strategy.name}'")
                publications: List[Dict[str, Any]] = []
                metadata: Dict[str, Any] = {}
                search_attempt: Dict[str, Any] = {"strategy": strategy.name} # Init attempt dict

                try:
                    # Execute strategy
                    publications, metadata = strategy.execute(reference)

                    # Update search_attempt with details from metadata
                    search_attempt["query_type"] = metadata.get("query_type", "unknown")
                    search_attempt["search_term"] = metadata.get("search_term", "")
                    if "error" in metadata:
                        search_attempt["error"] = metadata["error"]
                        # Check if the error indicates a rejection due to similarity
                        if "similarity below threshold" in metadata["error"]:
                            final_rejection_reason = metadata["error"] # Store rejection reason

                    result.search_attempts.append(search_attempt)

                    if publications:
                        # We found a match via this strategy
                        best_match = publications[0] # Strategies should return ranked results
                        logger.info(f"Study {study.id}: Match FOUND via strategy '{strategy.name}'")
                        result.status = SearchStatus.FOUND
                        result.strategy = strategy.name
                        self._extract_publication_data(result, best_match)
                        # Clear debug info if present
                        if result.search_details and "_debug" in result.search_details:
                             del result.search_details["_debug"]
                        if best_match and "_debug" in best_match: # Also clear from the source dict if needed elsewhere
                            del best_match["_debug"]

                        found_match = True # Set flag to stop trying more strategies

                except Exception as e:
                    # Catch unexpected errors during strategy execution
                    error_msg = f"Strategy execution error: {str(e)}"
                    logger.error(f"Study {study.id}: Error during strategy '{strategy.name}': {e}", exc_info=True)
                    search_attempt["query_type"] = search_attempt.get("query_type", "execution_error")
                    search_attempt["search_term"] = search_attempt.get("search_term", reference.title or "N/A")
                    search_attempt["error"] = error_msg
                    result.search_attempts.append(search_attempt)
                    # Continue to next strategy
            else:
                logger.debug(f"Study {study.id}: Strategy '{strategy.name}' not supported for this reference.")

        # Determine final status if no match was found
        if not found_match:
            if final_rejection_reason:
                result.status = SearchStatus.REJECTED
                logger.info(f"Study {study.id}: Final status REJECTED (Reason: {final_rejection_reason})")
            else:
                result.status = SearchStatus.NOT_FOUND
                logger.info(f"Study {study.id}: Final status NOT_FOUND after trying all supported strategies.")

        return result

    def _extract_publication_data(
        self, result: SearchResult, publication: Dict[str, Any]
    ) -> None:
        """Extract data from a publication and populate the SearchResult."""
        if not publication: return

        # Extract OpenAlex ID (handle potential variations)
        openalex_url = publication.get("id", "")
        if openalex_url and isinstance(openalex_url, str):
            result.openalex_id = openalex_url.split('/')[-1] if '/' in openalex_url else openalex_url

        result.title = publication.get("title")
        result.year = publication.get("publication_year")
        result.doi = publication.get("doi") # Store full DOI URL if present

        # Journal/Source
        primary_location = publication.get("primary_location")
        if isinstance(primary_location, dict):
            source = primary_location.get("source")
            if isinstance(source, dict):
                result.journal = source.get("display_name")

        # Open Access
        open_access_data = publication.get("open_access")
        if isinstance(open_access_data, dict):
            result.open_access = open_access_data.get("is_oa")
            # Extract PDF URL preferentially from oa_url if available
            result.pdf_url = open_access_data.get("oa_url")

        # Fallback PDF URL from primary location if not found in OA info
        if not result.pdf_url and isinstance(primary_location, dict):
             landing_page_url = primary_location.get("landing_page_url")
             # Simple check if landing page looks like a PDF link (crude)
             if landing_page_url and isinstance(landing_page_url, str) and landing_page_url.lower().endswith(".pdf"):
                  result.pdf_url = landing_page_url
             # Potentially add primary_location.pdf_url if that field exists? Check OpenAlex schema.
             # pdf_url_from_loc = primary_location.get("pdf_url")
             # if pdf_url_from_loc: result.pdf_url = pdf_url_from_loc


        result.citation_count = publication.get("cited_by_count")

        # Add search details from the publication itself for context
        result.search_details = {
            "openalex_url": openalex_url, # Keep full URL here
            "publication_type": publication.get("type"),
            "publication_date": publication.get("publication_date"),
            # Include similarity scores if they were added by the strategy
            **(publication.get("_debug", {}))
        }
