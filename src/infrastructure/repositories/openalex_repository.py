# src/infrastructure/repositories/openalex_repository.py
"""OpenAlex repository implementation using pyalex library."""

from typing import Any, Dict, List, Optional

import pyalex
from loguru import logger

from src.domain.interfaces.publication_repository import PublicationRepository
from src.domain.models.config import Config
from src.utils.text_normalizer import TextNormalizer


class OpenAlexRepository(PublicationRepository):
    """Repository for accessing the OpenAlex database using pyalex."""

    def __init__(self, config: Config):
        """Initialize the OpenAlex repository."""
        # Set email for "polite pool" if available
        pyalex.config.email = (
            config.openalex_email or None
        )  # Ensure None if empty string
        logger.info(
            f"Setting OpenAlex email for polite pool: {pyalex.config.email}"
        )

        # Configure retry parameters
        pyalex.config.max_retries = config.max_retries
        pyalex.config.retry_backoff_factor = config.retry_backoff_factor
        pyalex.config.retry_http_codes = config.retry_http_codes or [
            429,
            500,
            503,
        ]
        logger.info(
            f"Retry settings: max={config.max_retries}, factor={config.retry_backoff_factor}, codes={config.retry_http_codes}"
        )

        self.config = config

    def _log_api_call(
        self,
        method: str,
        params: Dict,
        result_count: Optional[int] = None,
        error: Optional[Exception] = None,
    ):
        """Helper to log API calls."""
        status = "SUCCESS" if error is None else "ERROR"
        count_str = (
            f", Results: {result_count}" if result_count is not None else ""
        )
        error_str = f", Error: {error}" if error else ""
        param_str = ", ".join(f"{k}={repr(v)}" for k, v in params.items())
        logger.debug(
            f"API Call ({status}): {method}({param_str}){count_str}{error_str}"
        )

    def get_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get publication by DOI."""
        if not doi or not doi.strip():
            logger.warning("Attempted get_by_doi with empty DOI.")
            return None
        normalized_doi = doi.strip()
        params = {"doi": normalized_doi}
        try:
            # Use get(return_meta=False) if you only need the first item
            results = pyalex.Works().filter(doi=normalized_doi).get(per_page=1)
            result = results[0] if results else None
            self._log_api_call(
                "get_by_doi",
                params,
                result_count=len(results) if results else 0,
            )
            return result
        except Exception as e:
            self._log_api_call("get_by_doi", params, error=e)
            logger.error(
                f"Error searching for DOI {normalized_doi}: {e}", exc_info=True
            )
            return None

    def get_by_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Get publication by PubMed ID."""
        if not pmid or not pmid.strip():
            logger.warning("Attempted get_by_pmid with empty PMID.")
            return None
        normalized_pmid = pmid.strip()
        if not normalized_pmid.isdigit():
            logger.warning(f"Invalid PMID format provided: {pmid}")
            return None
        params = {"pmid": normalized_pmid}
        try:
            results = (
                pyalex.Works().filter(pmid=normalized_pmid).get(per_page=1)
            )
            result = results[0] if results else None
            self._log_api_call(
                "get_by_pmid",
                params,
                result_count=len(results) if results else 0,
            )
            return result
        except Exception as e:
            self._log_api_call("get_by_pmid", params, error=e)
            logger.error(
                f"Error searching for PMID {normalized_pmid}: {e}",
                exc_info=True,
            )
            return None

    def _generate_author_query(self, authors: List[str]) -> Optional[str]:
        """Normalize authors and generate OR'd query string for pyalex."""
        # <<< --- DODANY LOG WEJŚCIA --- >>>
        logger.debug(f"_generate_author_query input authors: {authors}")
        # <<< -------------------------- >>>
        if not authors:
            logger.debug(
                "_generate_author_query returning None due to empty input list."
            )
            return None

        author_combinations = set()  # Use set to avoid duplicates
        for author_name in authors:
            if not author_name or not author_name.strip():
                logger.debug(
                    f"Skipping empty author name in input list: '{author_name}'"
                )
                continue

            normalized_author = TextNormalizer.normalize_text(author_name)
            if not normalized_author:
                logger.debug(
                    f"Author name '{author_name}' normalized to empty string, skipping."
                )
                continue

            # <<< --- DODANY LOG NORMALIZACJI --- >>>
            logger.debug(
                f"Processing normalized author: '{normalized_author}' (from '{author_name}')"
            )
            # <<< ----------------------------- >>>

            author_combinations.add(normalized_author)
            parts = normalized_author.split()

            # <<< --- DODANY LOG CZĘŚCI --- >>>
            logger.debug(f"Split '{normalized_author}' into parts: {parts}")
            # <<< ------------------------ >>>

            if len(parts) >= 2:
                # Reversed order (e.g., "Last First")
                reversed_name = " ".join(parts[::-1])
                author_combinations.add(reversed_name)
                logger.trace(
                    f"  Added reversed: '{reversed_name}'"
                )  # Trace dla mniej ważnych wariantów

                # First initial + Last Name(s) (e.g., "J Smith" or "J R R Tolkien")
                initial = parts[0][0]
                last_names = " ".join(parts[1:])
                if last_names:  # Ensure last name part exists
                    initial_last = f"{initial} {last_names}"
                    author_combinations.add(initial_last)
                    logger.trace(f"  Added initial+last: '{initial_last}'")

                    # Initials only if exactly two parts (e.g., "J S" from "John Smith")
                    if len(parts) == 2 and len(parts[1]) > 0:
                        # Make sure second part is not just a single initial already
                        if len(parts[1]) > 1:
                            initials_only = f"{initial} {parts[1][0]}"
                            author_combinations.add(initials_only)
                            logger.trace(
                                f"  Added initials only: '{initials_only}'"
                            )
                        else:
                            logger.trace(
                                f"  Skipping initials only for '{normalized_author}' as second part is already an initial."
                            )

        if not author_combinations:
            logger.warning(
                f"Could not generate valid author variations from input: {authors}"
            )
            return None

        # <<< --- DODANY LOG WYNIKOWYCH KOMBINACJI --- >>>
        logger.debug(
            f"Generated author combinations (set): {author_combinations}"
        )
        # <<< --------------------------------------- >>>

        # Join non-empty, unique combinations with OR operator
        final_query = "|".join(filter(None, sorted(list(author_combinations))))

        # <<< --- DODANY LOG FINALNEGO ZAPYTANIA --- >>>
        logger.debug(f"_generate_author_query output query: '{final_query}'")
        # <<< ------------------------------------- >>>
        return final_query

    def search_by_title_authors_year(
        self, title: str, authors: List[str], year: int
    ) -> List[Dict[str, Any]]:
        """Search by title, authors (with variations), and year."""
        logger.debug(
            f"Executing search_by_title_authors_year with title='{title}', authors={authors}, year={year}"
        )  # Log wejścia do metody
        if not title or not title.strip():
            logger.warning(
                "Attempted search_by_title_authors_year with empty title."
            )
            return []
        normalized_title = TextNormalizer.normalize_text(title)
        if len(normalized_title) < 4:  # Basic sanity check
            logger.warning(
                f"Title too short for search: '{title}' -> '{normalized_title}'"
            )
            return []

        author_query = self._generate_author_query(
            authors
        )  # Wywołanie z logowaniem w środku
        if not author_query:
            logger.warning(
                "Attempted search_by_title_authors_year with invalid/empty authors list after processing."
            )
            return []
        if year <= 0:
            logger.warning(f"Invalid year provided: {year}")
            return []

        params = {
            "title": normalized_title,
            "author_query": author_query,
            "year": year,
        }
        try:
            works_query = pyalex.Works().search_filter(title=normalized_title)
            works_query = works_query.filter(
                raw_author_name={"search": author_query}
            )
            works_query = works_query.filter(publication_year=year)
            logger.debug(
                f"Constructed pyalex query: Works().search_filter(title=...).filter(raw_author_name={{'search': ...}}).filter(publication_year={year})"
            )
            results = works_query.sort(relevance_score="desc").get(per_page=25)

            self._log_api_call(
                "search_by_title_authors_year",
                params,
                result_count=len(results),
            )
            # <<< --- DODANY LOG WYNIKU API --- >>>
            logger.trace(
                f"API raw results for TAY KUTAS ({title[:20]}...): {results}"
            )  # Trace bo może być dużo danych
            # <<< ----------------------------- >>>
            return results
        except Exception as e:
            self._log_api_call("search_by_title_authors_year", params, error=e)
            logger.error(
                f"Error in title-authors-year search for '{normalized_title}': {e}",
                exc_info=True,
            )
            return []

    def search_by_title_authors(
        self, title: str, authors: List[str]
    ) -> List[Dict[str, Any]]:
        """Search by title and authors (with variations)."""
        logger.debug(
            f"Executing search_by_title_authors with title='{title}', authors={authors}"
        )
        if not title or not title.strip():
            logger.warning(
                "Attempted search_by_title_authors with empty title."
            )
            return []
        normalized_title = TextNormalizer.normalize_text(title)
        if len(normalized_title) < 4:
            logger.warning(
                f"Title too short for search: '{title}' -> '{normalized_title}'"
            )
            return []

        author_query = self._generate_author_query(authors)
        if not author_query:
            logger.warning(
                "Attempted search_by_title_authors with invalid/empty authors list after processing."
            )
            return []

        params = {"title": normalized_title, "author_query": author_query}
        try:
            works_query = pyalex.Works().search_filter(title=normalized_title)
            works_query = works_query.filter(
                raw_author_name={"search": author_query}
            )
            logger.debug(
                "Constructed pyalex query: Works().search_filter(title=...).filter(raw_author_name={'search': ...})"
            )
            results = works_query.sort(relevance_score="desc").get(per_page=25)

            self._log_api_call(
                "search_by_title_authors", params, result_count=len(results)
            )
            # <<< --- DODANY LOG WYNIKU API --- >>>
            logger.trace(
                f"API raw results for TA ({title[:20]}...): {results}"
            )
            # <<< ----------------------------- >>>
            return results
        except Exception as e:
            self._log_api_call("search_by_title_authors", params, error=e)
            logger.error(
                f"Error in title-authors search for '{normalized_title}': {e}",
                exc_info=True,
            )
            return []

    def search_by_title_year(
        self, title: str, year: int
    ) -> List[Dict[str, Any]]:
        """Search by title and year."""
        logger.debug(
            f"Executing search_by_title_year with title='{title}', year={year}"
        )
        if not title or not title.strip():
            logger.warning("Attempted search_by_title_year with empty title.")
            return []
        normalized_title = TextNormalizer.normalize_text(title)
        if len(normalized_title) < 4:
            logger.warning(
                f"Title too short for search: '{title}' -> '{normalized_title}'"
            )
            return []
        if year <= 0:
            logger.warning(f"Invalid year provided: {year}")
            return []

        params = {"title": normalized_title, "year": year}
        try:
            works_query = pyalex.Works().search_filter(title=normalized_title)
            works_query = works_query.filter(publication_year=year)
            logger.debug(
                f"Constructed pyalex query: Works().search_filter(title=...).filter(publication_year={year})"
            )
            results = works_query.sort(relevance_score="desc").get(per_page=25)

            self._log_api_call(
                "search_by_title_year", params, result_count=len(results)
            )
            logger.trace(
                f"API raw results for TY ({title[:20]}...): {results}"
            )
            return results
        except Exception as e:
            self._log_api_call("search_by_title_year", params, error=e)
            logger.error(
                f"Error in title-year search for '{normalized_title}': {e}",
                exc_info=True,
            )
            return []

    # Removed search_by_title_journal method

    def search_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Search by title only."""
        logger.debug(f"Executing search_by_title with title='{title}'")
        if not title or not title.strip():
            logger.warning("Attempted search_by_title with empty title.")
            return []
        normalized_title = TextNormalizer.normalize_text(title)
        if len(normalized_title) < 4:
            logger.warning(
                f"Title too short for search: '{title}' -> '{normalized_title}'"
            )
            return []

        params = {"title": normalized_title}
        try:
            works_query = pyalex.Works().search_filter(title=normalized_title)
            logger.debug(
                "Constructed pyalex query: Works().search_filter(title=...)"
            )
            results = works_query.sort(relevance_score="desc").get(per_page=25)

            self._log_api_call(
                "search_by_title", params, result_count=len(results)
            )
            logger.trace(
                f"API raw results for TO ({title[:20]}...): {results}"
            )
            return results
        except Exception as e:
            self._log_api_call("search_by_title", params, error=e)
            logger.error(
                f"Error in title-only search for '{normalized_title}': {e}",
                exc_info=True,
            )
            return []
