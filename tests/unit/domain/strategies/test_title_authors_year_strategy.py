import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.title_authors_year_strategy import TitleAuthorsYearStrategy
from src.domain.models.config import Config
from .mock_repository import MockRepository


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        title_similarity_threshold=0.85,
        author_similarity_threshold=0.90
    )


@pytest.fixture
def mock_repository():
    """Create mock repository with test data."""
    mock_data = {
        "title_authors_year": [
            {
                "id": "W123456789",
                "title": "Test Publication on Medical Research",
                "publication_year": 2023,
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W987654321",
                "title": "Different Publication with Similar Title",
                "publication_year": 2023,
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W111222333",
                "title": "Test Publication on Medical Research",
                "publication_year": 2022,  # Different year
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            }
        ]
    }
    return MockRepository(mock_data)


@pytest.fixture
def title_authors_year_strategy(mock_repository, config):
    """Create TitleAuthorsYear strategy with mock repository."""
    return TitleAuthorsYearStrategy(mock_repository, config)


def test_strategy_name(title_authors_year_strategy):
    """Test strategy name property."""
    assert title_authors_year_strategy.name == "title_authors_year"


def test_strategy_priority(title_authors_year_strategy):
    """Test strategy priority property."""
    assert title_authors_year_strategy.priority == 3  # Third highest priority


def test_supported(title_authors_year_strategy):
    """Test supported method."""
    # With title, authors, and year
    reference = Reference(title="Test Title", authors=["Smith, J.", "Johnson, A."], year=2023)
    assert title_authors_year_strategy.supported(reference) is True
    
    # Without title
    reference = Reference(title=None, authors=["Smith, J."], year=2023)
    assert title_authors_year_strategy.supported(reference) is False
    
    # Without authors
    reference = Reference(title="Test Title", authors=None, year=2023)
    assert title_authors_year_strategy.supported(reference) is False
    
    # With empty authors list
    reference = Reference(title="Test Title", authors=[], year=2023)
    assert title_authors_year_strategy.supported(reference) is False
    
    # Without year
    reference = Reference(title="Test Title", authors=["Smith, J."], year=None)
    assert title_authors_year_strategy.supported(reference) is False


def test_validate_reference(title_authors_year_strategy):
    """Test validate_reference method."""
    # Valid reference
    reference = Reference(title="Test Title", authors=["Smith, J."], year=2023)
    assert title_authors_year_strategy.validate_reference(reference) is True
    
    # Invalid reference - no title
    reference = Reference(title=None, authors=["Smith, J."], year=2023)
    assert title_authors_year_strategy.validate_reference(reference) is False
    
    # Invalid reference - no authors
    reference = Reference(title="Test Title", authors=None, year=2023)
    assert title_authors_year_strategy.validate_reference(reference) is False
    
    # Invalid reference - no year
    reference = Reference(title="Test Title", authors=["Smith, J."], year=None)
    assert title_authors_year_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty title
    reference = Reference(title="", authors=["Smith, J."], year=2023)
    assert title_authors_year_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty authors list
    reference = Reference(title="Test Title", authors=[], year=2023)
    assert title_authors_year_strategy.validate_reference(reference) is False


def test_execute_success(title_authors_year_strategy, mock_repository):
    """Test successful execution with high similarity."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Smith, J.", "Johnson, A."],
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    assert metadata["strategy"] == "title_authors_year"
    assert metadata["query_type"] == "title, authors, year search"
    assert metadata["search_term"] == reference.title
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "search_by_title_authors_year"
    assert mock_repository.last_query["title"] == "Test Publication on Medical Research"
    assert mock_repository.last_query["authors"] == ["Smith, J.", "Johnson, A."]
    assert mock_repository.last_query["year"] == 2023


def test_execute_with_similar_title(title_authors_year_strategy):
    """Test execution with similar but not exact title match."""
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        authors=["Smith, J.", "Johnson, A."],
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"  # Should still find the result


def test_execute_not_found(title_authors_year_strategy):
    """Test execution with no results."""
    reference = Reference(
        title="Completely Different Title", 
        authors=["Smith, J.", "Johnson, A."],
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_authors_year"
    assert metadata["error"] == "No results found"


def test_execute_below_threshold(title_authors_year_strategy, config):
    """Test execution with title similarity below threshold."""
    # Set a very high threshold that no result will pass
    config.title_similarity_threshold = 0.99
    
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        authors=["Smith, J.", "Johnson, A."],
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_authors_year"
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_year_mismatch(title_authors_year_strategy):
    """Test execution with matching title and authors but different year."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Smith, J.", "Johnson, A."],
        year=2020  # Different from both publications
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_authors_year"
    # The repository returns an empty list for year mismatches in our mock
    assert "No results found" in metadata.get("error", "")


def test_execute_author_mismatch(title_authors_year_strategy):
    """Test execution with matching title and year but different authors."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Different, Author"],  # Different authors
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 0
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_api_error(title_authors_year_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(
        title="Test Publication", 
        authors=["Smith, J."],
        year=2023
    )
    
    results, metadata = title_authors_year_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]