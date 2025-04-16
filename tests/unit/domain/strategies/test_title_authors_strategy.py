import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.title_authors_strategy import TitleAuthorsStrategy
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
        "title_authors": [
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
                "title": "Different Publication Title",
                "publication_year": 2020,
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W111222333",
                "title": "Test Publication on Medical Research",
                "publication_year": 2022,
                "authorships": [
                    {"author": {"display_name": "Williams, B."}},  # Different authors
                    {"author": {"display_name": "Taylor, C."}}
                ]
            }
        ]
    }
    return MockRepository(mock_data)


@pytest.fixture
def title_authors_strategy(mock_repository, config):
    """Create TitleAuthors strategy with mock repository."""
    return TitleAuthorsStrategy(mock_repository, config)


def test_strategy_name(title_authors_strategy):
    """Test strategy name property."""
    assert title_authors_strategy.name == "title_authors"


def test_strategy_priority(title_authors_strategy):
    """Test strategy priority property."""
    assert title_authors_strategy.priority == 4  # Fourth priority


def test_supported(title_authors_strategy):
    """Test supported method."""
    # With title and authors
    reference = Reference(title="Test Title", authors=["Smith, J.", "Johnson, A."])
    assert title_authors_strategy.supported(reference) is True
    
    # Without title
    reference = Reference(title=None, authors=["Smith, J."])
    assert title_authors_strategy.supported(reference) is False
    
    # Without authors
    reference = Reference(title="Test Title", authors=None)
    assert title_authors_strategy.supported(reference) is False
    
    # With empty authors list
    reference = Reference(title="Test Title", authors=[])
    assert title_authors_strategy.supported(reference) is False
    
    # With year (should still be supported)
    reference = Reference(title="Test Title", authors=["Smith, J."], year=2023)
    assert title_authors_strategy.supported(reference) is True


def test_validate_reference(title_authors_strategy):
    """Test validate_reference method."""
    # Valid reference
    reference = Reference(title="Test Title", authors=["Smith, J."])
    assert title_authors_strategy.validate_reference(reference) is True
    
    # Invalid reference - no title
    reference = Reference(title=None, authors=["Smith, J."])
    assert title_authors_strategy.validate_reference(reference) is False
    
    # Invalid reference - no authors
    reference = Reference(title="Test Title", authors=None)
    assert title_authors_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty title
    reference = Reference(title="", authors=["Smith, J."])
    assert title_authors_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty authors list
    reference = Reference(title="Test Title", authors=[])
    assert title_authors_strategy.validate_reference(reference) is False


def test_execute_success(title_authors_strategy, mock_repository):
    """Test successful execution with high similarity."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Smith, J.", "Johnson, A."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    assert metadata["strategy"] == "title_authors"
    assert metadata["query_type"] == "title, authors search"
    assert metadata["search_term"] == reference.title
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "search_by_title_authors"
    assert mock_repository.last_query["title"] == "Test Publication on Medical Research"
    assert mock_repository.last_query["authors"] == ["Smith, J.", "Johnson, A."]


def test_execute_with_similar_title(title_authors_strategy):
    """Test execution with similar but not exact title match."""
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        authors=["Smith, J.", "Johnson, A."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"  # Should still find the result


def test_execute_not_found(title_authors_strategy):
    """Test execution with no results."""
    reference = Reference(
        title="Completely Different Title", 
        authors=["Smith, J.", "Johnson, A."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_authors"
    assert metadata["error"] == "No results found"


def test_execute_below_threshold(title_authors_strategy, config):
    """Test execution with title similarity below threshold."""
    # Set a very high threshold that no result will pass
    config.title_similarity_threshold = 0.99
    
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        authors=["Smith, J.", "Johnson, A."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_authors"
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_author_mismatch(title_authors_strategy):
    """Test execution with matching title but different authors."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Different, Author"]  # Different authors
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 0
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_multiple_matches(title_authors_strategy, mock_repository):
    """Test handling multiple matches with ranking."""
    # Add another similar result to test ranking
    mock_repository.mock_data["title_authors"].append({
        "id": "W444555666",
        "title": "Test Publication on Medical Research", # Exact same title
        "publication_year": 2023,
        "authorships": [
            {"author": {"display_name": "Smith, J."}},
            {"author": {"display_name": "Johnson, A."}}
        ]
    })
    
    reference = Reference(
        title="Test Publication on Medical Research", 
        authors=["Smith, J.", "Johnson, A."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    # Should find both matches and rank them
    assert len(results) == 2
    # Both should have high scores, but exact matches should be preferred
    assert "_debug" in results[0]
    assert results[0]["_debug"]["combined_score"] > 0.9


def test_execute_api_error(title_authors_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(
        title="Test Publication", 
        authors=["Smith, J."]
    )
    
    results, metadata = title_authors_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]