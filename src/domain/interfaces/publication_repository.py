# src/domain/interfaces/publication_repository.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PublicationRepository(ABC):
    """Interface for publication repositories."""

    @abstractmethod
    def get_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Get publication by DOI."""
        pass

    @abstractmethod
    def get_by_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Get publication by PubMed ID."""
        pass

    @abstractmethod
    def search_by_title_authors_year(
        self, title: str, authors: List[str], year: int
    ) -> List[Dict[str, Any]]:
        """Search for publications by title, authors and year."""
        pass

    @abstractmethod
    def search_by_title_authors(
        self, title: str, authors: List[str]
    ) -> List[Dict[str, Any]]:
        """Search for publications by title and authors."""
        pass

    @abstractmethod
    def search_by_title_year(self, title: str, year: int) -> List[Dict[str, Any]]:
        """Search for publications by title and year."""
        pass

    # Removed search_by_title_journal method

    @abstractmethod
    def search_by_title(self, title: str) -> List[Dict[str, Any]]:
        """Search for publications by title only."""
        pass
