"""Tests for the OpenAlex repository implementation."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.domain.models.config import Config
from src.infrastructure.repositories.openalex_repository import OpenAlexRepository


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        openalex_email="test@example.com",
        max_retries=3,
        retry_backoff_factor=0.5,
        title_similarity_threshold=0.85,
        author_similarity_threshold=0.9,
        disable_strategies=[],
        concurrency=20
    )


@pytest.fixture
def repository(config):
    """Create a repository with config."""
    # Setup pyalex.config mock as a dictionary-like object
    config_mock = {}
    
    with patch("pyalex.config", config_mock):
        # Create the repository
        repo = OpenAlexRepository(config)
        return repo


class TestOpenAlexRepositoryConfiguration:
    """Tests for repository configuration."""

    def test_init_with_email(self):
        """Test that email is set in pyalex.config."""
        config_mock = {}
        with patch("pyalex.config", config_mock):
            config = Config(openalex_email="test@example.com")
            OpenAlexRepository(config)
            assert config_mock["email"] == "test@example.com"

    def test_init_without_email(self):
        """Test initialization without email."""
        config_mock = {}
        with patch("pyalex.config", config_mock):
            config = Config(openalex_email=None)
            OpenAlexRepository(config)
            assert config_mock["email"] is None

    def test_init_sets_retry_parameters(self):
        """Test that retry parameters are set correctly."""
        config_mock = {}
        with patch("pyalex.config", config_mock):
            config = Config(
                max_retries=5,
                retry_backoff_factor=0.7,
                retry_http_codes=[429, 500, 503],
            )
            OpenAlexRepository(config)
            assert config_mock["max_retries"] == 5
            assert config_mock["retry_backoff_factor"] == 0.7
            assert config_mock["retry_http_codes"] == [429, 500, 503]


class TestGetByDoi:
    """Tests for get_by_doi method."""

    def test_get_by_doi_success(self, repository):
        """Test successful DOI lookup."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = [{"id": "W123", "title": "Example"}]
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_doi("10.1234/test")
            
            # Assertions
            mock_works_instance.filter.assert_called_once_with(doi="10.1234/test")
            mock_filter.get.assert_called_once()
            assert result == {"id": "W123", "title": "Example"}

    def test_get_by_doi_not_found(self, repository):
        """Test DOI not found."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = []
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_doi("10.1234/nonexistent")
            
            # Assertions
            assert result is None

    def test_get_by_doi_empty(self, repository):
        """Test empty DOI."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_doi("")
            
            # Assertions
            mock_works.assert_not_called()
            assert result is None

    def test_get_by_doi_normalizes_whitespace(self, repository):
        """Test DOI normalization."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = [{"id": "W123"}]
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_doi(" 10.1234/test ")
            
            # Assertions
            mock_works_instance.filter.assert_called_once_with(doi="10.1234/test")
            assert result == {"id": "W123"}

    def test_get_by_doi_api_error(self, repository):
        """Test API error handling."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.side_effect = Exception("API error")
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_doi("10.1234/test")
            
            # Assertions
            assert result is None


class TestGetByPmid:
    """Tests for get_by_pmid method."""

    def test_get_by_pmid_success(self, repository):
        """Test successful PMID lookup."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = [{"id": "W123", "pmid": "12345678"}]
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_pmid("12345678")
            
            # Assertions
            mock_works_instance.filter.assert_called_once_with(pmid="12345678")
            mock_filter.get.assert_called_once()
            assert result == {"id": "W123", "pmid": "12345678"}

    def test_get_by_pmid_not_found(self, repository):
        """Test PMID not found."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = []
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_pmid("99999999")
            
            # Assertions
            assert result is None

    def test_get_by_pmid_empty(self, repository):
        """Test empty PMID."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_pmid("")
            
            # Assertions
            mock_works.assert_not_called()
            assert result is None

    def test_get_by_pmid_normalizes_whitespace(self, repository):
        """Test PMID normalization."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.return_value = [{"id": "W123"}]
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_pmid(" 12345678 ")
            
            # Assertions
            mock_works_instance.filter.assert_called_once_with(pmid="12345678")
            assert result == {"id": "W123"}

    def test_get_by_pmid_api_error(self, repository):
        """Test API error handling."""
        # Setup mock chain
        mock_filter = MagicMock()
        mock_filter.get.side_effect = Exception("API error")
        
        mock_works_instance = MagicMock()
        mock_works_instance.filter.return_value = mock_filter
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.get_by_pmid("12345678")
            
            # Assertions
            assert result is None


class TestSearchByTitleAuthorsYear:
    """Tests for search_by_title_authors_year method."""

    def test_search_by_title_authors_year_success(self, repository):
        """Test successful title-authors-year search."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study", "publication_year": 2023}
        ]
        
        mock_filter2 = MagicMock()
        mock_filter2.sort.return_value = mock_sort
        
        mock_filter = MagicMock()
        mock_filter.filter.return_value = mock_filter2
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors_year(
                "Example Study", ["Adam Unikon"], 2023
            )
            
            # Assertions
            assert len(result) == 1
            assert result[0]["id"] == "W123"
            assert result[0]["title"] == "Example Study"
            assert result[0]["publication_year"] == 2023

    def test_search_by_title_authors_year_with_initials(self, repository):
        """Test author name matching with initials."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study", "publication_year": 2023}
        ]
        
        mock_filter2 = MagicMock()
        mock_filter2.sort.return_value = mock_sort
        
        mock_filter = MagicMock()
        mock_filter.filter.return_value = mock_filter2
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method with initials
            result = repository.search_by_title_authors_year(
                "Example Study", ["A Unikon"], 2023
            )
            
            # Verify filter contains name variations
            call_args = mock_search.filter.call_args[1]
            author_query = call_args["raw_author_name"]
            name_variations = author_query["search"]
            
            # Check if name variations include expected patterns
            assert "a unikon" in name_variations
            assert "unikon a" in name_variations
            
            # Assertions on result
            assert len(result) == 1
            assert result[0]["id"] == "W123"

    def test_search_by_title_authors_year_with_reversed_name(self, repository):
        """Test author name matching with reversed order."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study", "publication_year": 2023}
        ]
        
        mock_filter2 = MagicMock()
        mock_filter2.sort.return_value = mock_sort
        
        mock_filter = MagicMock()
        mock_filter.filter.return_value = mock_filter2
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method with reversed name
            result = repository.search_by_title_authors_year(
                "Example Study", ["Unikon Adam"], 2023
            )
            
            # Verify filter contains name variations
            call_args = mock_search.filter.call_args[1]
            author_query = call_args["raw_author_name"]
            name_variations = author_query["search"]
            
            # Check if name variations include expected patterns
            assert "unikon adam" in name_variations
            assert "adam unikon" in name_variations
            
            # Assertions on result
            assert len(result) == 1
            assert result[0]["id"] == "W123"

    def test_search_by_title_authors_year_empty_title(self, repository):
        """Test empty title."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors_year(
                "", ["Adam Unikon"], 2023
            )
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []

    def test_search_by_title_authors_year_empty_authors(self, repository):
        """Test empty authors list."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors_year(
                "Example Study", [], 2023
            )
            
            # Check correct behavior
            assert result == []

    def test_search_by_title_authors_year_empty_author_name(self, repository):
        """Test empty author name."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors_year(
                "Example Study", [""], 2023
            )
            
            # Check correct behavior
            assert result == []

    def test_search_by_title_authors_year_api_error(self, repository):
        """Test API error handling."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.side_effect = Exception("API error")
        
        mock_filter2 = MagicMock()
        mock_filter2.sort.return_value = mock_sort
        
        mock_filter = MagicMock()
        mock_filter.filter.return_value = mock_filter2
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors_year(
                "Example Study", ["Adam Unikon"], 2023
            )
            
            # Assertions
            assert result == []


class TestSearchByTitleAuthors:
    """Tests for search_by_title_authors method."""

    def test_search_by_title_authors_success(self, repository):
        """Test successful title-authors search."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study"}
        ]
        
        mock_filter = MagicMock()
        mock_filter.sort.return_value = mock_sort
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors(
                "Example Study", ["Adam Unikon"]
            )
            
            # Assertions
            assert len(result) == 1
            assert result[0]["id"] == "W123"
            assert result[0]["title"] == "Example Study"

    def test_search_by_title_authors_empty_title(self, repository):
        """Test empty title."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_authors("", ["Adam Unikon"])
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []


class TestSearchByTitleYear:
    """Tests for search_by_title_year method."""

    def test_search_by_title_year_success(self, repository):
        """Test successful title-year search."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study", "publication_year": 2023}
        ]
        
        mock_filter = MagicMock()
        mock_filter.sort.return_value = mock_sort
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_year("Example Study", 2023)
            
            # Assertions
            assert len(result) == 1
            assert result[0]["id"] == "W123"
            assert result[0]["title"] == "Example Study"
            assert result[0]["publication_year"] == 2023

    def test_search_by_title_year_empty_title(self, repository):
        """Test empty title."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_year("", 2023)
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []


class TestSearchByTitleJournal:
    """Tests for search_by_title_journal method."""

    def test_search_by_title_journal_success(self, repository):
        """Test successful title-journal search."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study"}
        ]
        
        mock_filter = MagicMock()
        mock_filter.sort.return_value = mock_sort
        
        mock_search = MagicMock()
        mock_search.filter.return_value = mock_filter
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_journal(
                "Example Study", "Journal of Examples"
            )
            
            # Assertions
            assert len(result) == 1
            assert result[0]["id"] == "W123"
            assert result[0]["title"] == "Example Study"

    def test_search_by_title_journal_empty_title(self, repository):
        """Test empty title."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_journal("", "Journal of Examples")
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []

    def test_search_by_title_journal_empty_journal(self, repository):
        """Test empty journal."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title_journal("Example Study", "")
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []


class TestSearchByTitle:
    """Tests for search_by_title method."""

    def test_search_by_title_success(self, repository):
        """Test successful title-only search."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study"}
        ]
        
        mock_search = MagicMock()
        mock_search.sort.return_value = mock_sort
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title("Example Study")
            
            # Assertions
            assert len(result) == 1
            assert result[0]["id"] == "W123"
            assert result[0]["title"] == "Example Study"

    def test_search_by_title_empty_title(self, repository):
        """Test empty title."""
        # Setup mock
        mock_works = MagicMock()
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method
            result = repository.search_by_title("")
            
            # Assertions
            mock_works.assert_not_called()
            assert result == []

    def test_search_by_title_special_characters(self, repository):
        """Test title with special characters."""
        # Setup mock chain
        mock_sort = MagicMock()
        mock_sort.get.return_value = [
            {"id": "W123", "title": "Example Study"}
        ]
        
        mock_search = MagicMock()
        mock_search.sort.return_value = mock_sort
        
        mock_works_instance = MagicMock()
        mock_works_instance.search_filter.return_value = mock_search
        
        mock_works = MagicMock()
        mock_works.return_value = mock_works_instance
        
        # Apply the mock
        with patch("pyalex.Works", mock_works):
            # Call method with special characters
            result = repository.search_by_title("Example Study!")
            
            # Check normalized title is used in search
            mock_works_instance.search_filter.assert_called_once_with(title="example study")
            
            # Assertions on result
            assert len(result) == 1
            assert result[0]["id"] == "W123"