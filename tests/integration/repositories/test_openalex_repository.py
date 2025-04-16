"""Integration tests for OpenAlexRepository."""
import json
import os
from unittest import mock

import pytest
from loguru import logger

from src.domain.models.config import Config
from src.infrastructure.repositories.openalex_repository import OpenAlexRepository
from src.utils.text_normalizer import TextNormalizer


class TestOpenAlexRepository:
    """Integration tests for OpenAlexRepository with real data."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config(
            openalex_email="test@example.com",
            title_similarity_threshold=0.8,
            author_similarity_threshold=0.7,
            disable_strategies=[],
            max_retries=2,
            retry_backoff_factor=0.1,
            retry_http_codes=[429, 500, 503],
            concurrency=3,
        )
    
    @pytest.fixture
    def sample_data(self):
        """Load the sample data file."""
        # Start from the project root (one directory up from tests)
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        file_path = os.path.join(script_dir, "data", "antibiotics-for-sore-throat.json")
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    @pytest.fixture
    def repository(self, config):
        """Create an OpenAlexRepository instance."""
        return OpenAlexRepository(config)
    
    def _check_author_query(self, author_query, authors):
        """Check that the author query contains all expected author parts."""
        # Using | as separator, the query should contain all author combinations
        query_parts = author_query.split("|")
        
        # Check that original authors are included
        for author in authors:
            normalized = TextNormalizer.normalize_text(author)
            assert normalized in query_parts, f"Original author '{normalized}' not found in query"
            
            # For authors with space, check variations
            if " " in normalized:
                first_last = normalized.split()
                if len(first_last) == 2:
                    # Check reversed name
                    reversed_name = f"{first_last[1]} {first_last[0]}"
                    assert reversed_name in query_parts, f"Reversed name '{reversed_name}' not found in query"
                    
                    # Check initial with last name
                    initial_last = f"{first_last[0][0]} {first_last[1]}"
                    assert initial_last in query_parts, f"Initial last '{initial_last}' not found in query"
            
        # Log the full query for analysis
        logger.debug(f"Author query: {author_query}")
        logger.debug(f"Query parts: {query_parts}")
        
        return query_parts
        
    def test_author_name_variations(self, repository):
        """Test the author name variations generated during searches."""
        # Test cases with different author formats
        test_cases = [
            # Single author with first and last name
            {
                "authors": ["John Smith"],
                "expected_variations": [
                    "john smith", 
                    "smith john", 
                    "j smith",
                    "j s"
                ]
            },
            # Single author with comma
            {
                "authors": ["Smith, John"],
                "expected_variations": [
                    "smith john", 
                    "john smith", 
                    "s john",
                    "s j"
                ]
            },
            # Multiple authors
            {
                "authors": ["John Smith", "Jane Doe"],
                "expected_variations": [
                    "john smith", 
                    "smith john", 
                    "j smith",
                    "j s",
                    "jane doe",
                    "doe jane",
                    "j doe",
                    "j d"
                ]
            },
            # Author with middle initial
            {
                "authors": ["John B Smith"],
                "expected_variations": [
                    "john b smith", 
                    "smith b john" 
                ]
            }
        ]
        
        for test_case in test_cases:
            # Create a mock to capture the query
            mock_works = mock.MagicMock()
            mock_search_filter = mock.MagicMock()
            mock_filter = mock.MagicMock()
            mock_sort = mock.MagicMock()
            mock_get = mock.MagicMock()
            
            with mock.patch("pyalex.Works", return_value=mock_works):
                mock_works.search_filter.return_value = mock_search_filter
                mock_search_filter.filter.return_value = mock_filter
                mock_filter.sort.return_value = mock_sort
                mock_sort.get.return_value = []
                
                # Call the search method with the test authors
                repository.search_by_title_authors("Test Title", test_case["authors"])
                
                # Extract the author query
                args, kwargs = mock_search_filter.filter.call_args
                author_query = kwargs["raw_author_name"]["search"]
                query_parts = author_query.split("|")
                
                # Verify all expected variations are present
                for variation in test_case["expected_variations"]:
                    assert variation in query_parts, f"Expected variation '{variation}' not found in query parts for authors {test_case['authors']}"
                
                logger.info(f"Authors: {test_case['authors']}")
                logger.info(f"Generated variations: {query_parts}")
                logger.info(f"Expected variations: {test_case['expected_variations']}")
    
    def test_search_by_title_authors_year_parameters(self, repository, sample_data, monkeypatch):
        """Test search_by_title_authors_year with sample data references to verify query parameters."""
        # Mock the pyalex.Works class to capture filter parameters
        mock_works = mock.MagicMock()
        mock_search_filter = mock.MagicMock()
        mock_filter1 = mock.MagicMock()
        mock_filter2 = mock.MagicMock()
        mock_sort = mock.MagicMock()
        mock_get = mock.MagicMock()
        
        # Chain the mocks
        mock_works.return_value = mock_works
        mock_works.search_filter.return_value = mock_search_filter
        mock_search_filter.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.sort.return_value = mock_sort
        mock_sort.get.return_value = []
        
        # Apply the mock
        monkeypatch.setattr("pyalex.Works", mock_works)
        
        # Get a reference from the sample data
        reference = sample_data["studies"]["included"][0]["reference"]
        title = reference["title"]
        authors = reference["authors_list"]
        year = reference["year"]
        
        # Log the test data
        logger.info(f"Using reference: {reference}")
        logger.info(f"Title: {title}")
        logger.info(f"Authors: {authors}")
        logger.info(f"Year: {year}")
        
        # Call the method
        repository.search_by_title_authors_year(title, authors, year)
        
        # Verify that the method was called with the expected parameters
        normalized_title = TextNormalizer.normalize_text(title)
        mock_works.search_filter.assert_called_once_with(title=normalized_title)
        
        # Check that raw_author_name.search was called with the correctly formatted author string
        args, kwargs = mock_search_filter.filter.call_args
        assert "raw_author_name" in kwargs
        assert "search" in kwargs["raw_author_name"]
        
        # Check the author query is properly formatted and contains all expected parts
        self._check_author_query(kwargs["raw_author_name"]["search"], authors)
        
        # Check that publication_year was passed correctly
        args, kwargs = mock_filter1.filter.call_args
        assert "publication_year" in kwargs
        assert kwargs["publication_year"] == year
        
        # Check that sort was called with relevance_score="desc"
        args, kwargs = mock_filter2.sort.call_args
        assert "relevance_score" in kwargs
        assert kwargs["relevance_score"] == "desc"
        
        # Check that get was called with per_page=25
        args, kwargs = mock_sort.get.call_args
        assert "per_page" in kwargs
        assert kwargs["per_page"] == 25
    
    def test_search_by_title_authors_parameters(self, repository, sample_data, monkeypatch):
        """Test search_by_title_authors with sample data references to verify query parameters."""
        # Mock the pyalex.Works class to capture filter parameters
        mock_works = mock.MagicMock()
        mock_search_filter = mock.MagicMock()
        mock_filter = mock.MagicMock()
        mock_sort = mock.MagicMock()
        mock_get = mock.MagicMock()
        
        # Chain the mocks
        mock_works.return_value = mock_works
        mock_works.search_filter.return_value = mock_search_filter
        mock_search_filter.filter.return_value = mock_filter
        mock_filter.sort.return_value = mock_sort
        mock_sort.get.return_value = []
        
        # Apply the mock
        monkeypatch.setattr("pyalex.Works", mock_works)
        
        # Get a reference from the sample data
        reference = sample_data["studies"]["included"][0]["reference"]
        title = reference["title"]
        authors = reference["authors_list"]
        
        # Log the test data
        logger.info(f"Using reference: {reference}")
        logger.info(f"Title: {title}")
        logger.info(f"Authors: {authors}")
        
        # Call the method
        repository.search_by_title_authors(title, authors)
        
        # Verify that the method was called with the expected parameters
        normalized_title = TextNormalizer.normalize_text(title)
        mock_works.search_filter.assert_called_once_with(title=normalized_title)
        
        # Check that raw_author_name.search was called with the correctly formatted author string
        args, kwargs = mock_search_filter.filter.call_args
        assert "raw_author_name" in kwargs
        assert "search" in kwargs["raw_author_name"]
        
        # Check the author query is properly formatted and contains all expected parts
        self._check_author_query(kwargs["raw_author_name"]["search"], authors)
        
        # Check that sort was called with relevance_score="desc"
        args, kwargs = mock_filter.sort.call_args
        assert "relevance_score" in kwargs
        assert kwargs["relevance_score"] == "desc"
        
        # Check that get was called with per_page=25
        args, kwargs = mock_sort.get.call_args
        assert "per_page" in kwargs
        assert kwargs["per_page"] == 25
    
    def test_search_by_title_year_parameters(self, repository, sample_data, monkeypatch):
        """Test search_by_title_year with sample data references to verify query parameters."""
        # Mock the pyalex.Works class to capture filter parameters
        mock_works = mock.MagicMock()
        mock_search_filter = mock.MagicMock()
        mock_filter = mock.MagicMock()
        mock_sort = mock.MagicMock()
        mock_get = mock.MagicMock()
        
        # Chain the mocks
        mock_works.return_value = mock_works
        mock_works.search_filter.return_value = mock_search_filter
        mock_search_filter.filter.return_value = mock_filter
        mock_filter.sort.return_value = mock_sort
        mock_sort.get.return_value = []
        
        # Apply the mock
        monkeypatch.setattr("pyalex.Works", mock_works)
        
        # Get a reference from the sample data
        reference = sample_data["studies"]["included"][0]["reference"]
        title = reference["title"]
        year = reference["year"]
        
        # Call the method
        repository.search_by_title_year(title, year)
        
        # Verify that the method was called with the expected parameters
        normalized_title = TextNormalizer.normalize_text(title)
        mock_works.search_filter.assert_called_once_with(title=normalized_title)
        
        # Check that publication_year was passed correctly
        args, kwargs = mock_search_filter.filter.call_args
        assert "publication_year" in kwargs
        assert kwargs["publication_year"] == year
        
        # Check that sort was called with relevance_score="desc"
        args, kwargs = mock_filter.sort.call_args
        assert "relevance_score" in kwargs
        assert kwargs["relevance_score"] == "desc"
        
        # Check that get was called with per_page=25
        args, kwargs = mock_sort.get.call_args
        assert "per_page" in kwargs
        assert kwargs["per_page"] == 25
    
    def test_search_by_title_journal_parameters(self, repository, sample_data, monkeypatch):
        """Test search_by_title_journal with sample data references to verify query parameters."""
        # Mock the pyalex.Works class to capture filter parameters
        mock_works = mock.MagicMock()
        mock_search_filter = mock.MagicMock()
        mock_filter = mock.MagicMock()
        mock_sort = mock.MagicMock()
        mock_get = mock.MagicMock()
        
        # Chain the mocks
        mock_works.return_value = mock_works
        mock_works.search_filter.return_value = mock_search_filter
        mock_search_filter.filter.return_value = mock_filter
        mock_filter.sort.return_value = mock_sort
        mock_sort.get.return_value = []
        
        # Apply the mock
        monkeypatch.setattr("pyalex.Works", mock_works)
        
        # Get a reference from the sample data
        reference = sample_data["studies"]["included"][0]["reference"]
        title = reference["title"]
        journal = reference["source"]
        
        # Call the method
        repository.search_by_title_journal(title, journal)
        
        # Verify that the method was called with the expected parameters
        normalized_title = TextNormalizer.normalize_text(title)
        normalized_journal = TextNormalizer.normalize_text(journal)
        mock_works.search_filter.assert_called_once_with(title=normalized_title)
        
        # Check that primary_location.source.display_name was passed correctly
        args, kwargs = mock_search_filter.filter.call_args
        assert "primary_location" in kwargs
        assert "source" in kwargs["primary_location"]
        assert "display_name" in kwargs["primary_location"]["source"]
        assert kwargs["primary_location"]["source"]["display_name"] == normalized_journal
        
        # Check that sort was called with relevance_score="desc"
        args, kwargs = mock_filter.sort.call_args
        assert "relevance_score" in kwargs
        assert kwargs["relevance_score"] == "desc"
        
        # Check that get was called with per_page=25
        args, kwargs = mock_sort.get.call_args
        assert "per_page" in kwargs
        assert kwargs["per_page"] == 25
    
    def test_search_by_title_parameters(self, repository, sample_data, monkeypatch):
        """Test search_by_title with sample data references to verify query parameters."""
        # Mock the pyalex.Works class to capture filter parameters
        mock_works = mock.MagicMock()
        mock_search_filter = mock.MagicMock()
        mock_sort = mock.MagicMock()
        mock_get = mock.MagicMock()
        
        # Chain the mocks
        mock_works.return_value = mock_works
        mock_works.search_filter.return_value = mock_search_filter
        mock_search_filter.sort.return_value = mock_sort
        mock_sort.get.return_value = []
        
        # Apply the mock
        monkeypatch.setattr("pyalex.Works", mock_works)
        
        # Get a reference from the sample data
        reference = sample_data["studies"]["included"][0]["reference"]
        title = reference["title"]
        
        # Log the test data
        logger.info(f"Using reference title: {title}")
        
        # Call the method
        repository.search_by_title(title)
        
        # Verify that the method was called with the expected parameters
        normalized_title = TextNormalizer.normalize_text(title)
        mock_works.search_filter.assert_called_once_with(title=normalized_title)
        
        # Check that sort was called with relevance_score="desc"
        args, kwargs = mock_search_filter.sort.call_args
        assert "relevance_score" in kwargs
        assert kwargs["relevance_score"] == "desc"
        
        # Check that get was called with per_page=25
        args, kwargs = mock_sort.get.call_args
        assert "per_page" in kwargs
        assert kwargs["per_page"] == 25
        
    def test_get_by_doi_parameters(self, repository, monkeypatch):
        """Test get_by_doi with various inputs to verify parameters."""
        # Test cases with different DOI formats
        test_cases = [
            {
                "doi": "10.1234/abcd.5678",
                "expected": "10.1234/abcd.5678"
            },
            {
                "doi": "  10.1234/abcd.5678  ",  # With whitespace
                "expected": "10.1234/abcd.5678"
            },
            {
                "doi": "https://doi.org/10.1234/abcd.5678",  # With URL prefix
                "expected": "https://doi.org/10.1234/abcd.5678" 
            }
        ]
        
        for test_case in test_cases:
            # Create mock for Works
            mock_works = mock.MagicMock()
            mock_filter = mock.MagicMock()
            mock_get = mock.MagicMock()
            
            # Configure mocks
            mock_works.return_value = mock_works
            mock_works.filter.return_value = mock_filter
            mock_filter.get.return_value = []
            
            # Apply the mock
            monkeypatch.setattr("pyalex.Works", mock_works)
            
            # Call the method
            repository.get_by_doi(test_case["doi"])
            
            # Verify that the proper parameters were used
            args, kwargs = mock_works.filter.call_args
            assert "doi" in kwargs
            normalized_doi = test_case["doi"].strip()
            assert kwargs["doi"] == normalized_doi
            
            logger.info(f"DOI input: {test_case['doi']}")
            logger.info(f"Normalized DOI used: {kwargs['doi']}")
            
    def test_get_by_pmid_parameters(self, repository, monkeypatch):
        """Test get_by_pmid with various inputs to verify parameters."""
        # Test cases with different PMID formats
        test_cases = [
            {
                "pmid": "12345678",
                "expected": "12345678",
                "should_call_api": True
            },
            {
                "pmid": "  12345678  ",  # With whitespace
                "expected": "12345678",
                "should_call_api": True
            },
            {
                "pmid": "PMID12345678",  # Invalid format
                "expected": None,
                "should_call_api": False
            }
        ]
        
        for test_case in test_cases:
            # Create mock for Works
            mock_works = mock.MagicMock()
            mock_filter = mock.MagicMock()
            mock_get = mock.MagicMock()
            
            # Configure mocks
            mock_works.return_value = mock_works
            mock_works.filter.return_value = mock_filter
            mock_filter.get.return_value = []
            
            # Apply the mock
            monkeypatch.setattr("pyalex.Works", mock_works)
            
            # Call the method
            repository.get_by_pmid(test_case["pmid"])
            
            # Verify the behavior based on the test case
            if test_case["should_call_api"]:
                # Check that the API was called with correct parameters
                args, kwargs = mock_works.filter.call_args
                assert "pmid" in kwargs
                assert kwargs["pmid"] == test_case["expected"]
            else:
                # Check that the API was not called for invalid PMIDs
                mock_works.filter.assert_not_called()
            
            logger.info(f"PMID input: {test_case['pmid']}")
            if test_case["should_call_api"]:
                logger.info(f"Normalized PMID used: {kwargs['pmid']}")
            else:
                logger.info("API call not made due to invalid PMID format")