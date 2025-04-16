import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.title_only_strategy import TitleOnlyStrategy
from src.domain.models.config import Config
from .mock_repository import MockRepository


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        title_similarity_threshold=0.85
    )


@pytest.fixture
def mock_repository():
    """Create mock repository with test data."""
    mock_data = {
        "title": [
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
                "publication_year": 2023,
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W111222333",
                "title": "Another Test Publication on Medical Research",
                "publication_year": 2022,
                "authorships": [
                    {"author": {"display_name": "Williams, B."}},
                    {"author": {"display_name": "Taylor, C."}}
                ]
            }
        ]
    }
    return MockRepository(mock_data)


@pytest.fixture
def title_only_strategy(mock_repository, config):
    """Create TitleOnly strategy with mock repository."""
    return TitleOnlyStrategy(mock_repository, config)


def test_strategy_name(title_only_strategy):
    """Test strategy name property."""
    assert title_only_strategy.name == "title_only"


def test_strategy_priority(title_only_strategy):
    """Test strategy priority property."""
    assert title_only_strategy.priority == 7  # Lowest priority


def test_supported(title_only_strategy):
    """Test supported method."""
    # With title
    reference = Reference(title="Test Title")
    assert title_only_strategy.supported(reference) is True
    
    # Without title
    reference = Reference(title=None)
    assert title_only_strategy.supported(reference) is False
    
    # With empty title
    reference = Reference(title="")
    assert title_only_strategy.supported(reference) is False
    
    # With other fields (should still be supported)
    reference = Reference(title="Test Title", year=2023, authors=["Smith, J."], journal="Journal")
    assert title_only_strategy.supported(reference) is True


def test_validate_reference(title_only_strategy):
    """Test validate_reference method."""
    # Valid reference
    reference = Reference(title="Test Title")
    assert title_only_strategy.validate_reference(reference) is True
    
    # Invalid reference - no title
    reference = Reference(title=None)
    assert title_only_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty title
    reference = Reference(title="")
    assert title_only_strategy.validate_reference(reference) is False


def test_execute_success(title_only_strategy, mock_repository):
    """Test successful execution with high similarity."""
    # Clear other titles for this test
    mock_repository.mock_data["title"] = [
        {
            "id": "W123456789",
            "title": "Test Publication on Medical Research",
            "publication_year": 2023,
            "authorships": [
                {"author": {"display_name": "Smith, J."}},
                {"author": {"display_name": "Johnson, A."}}
            ]
        }
    ]
    
    reference = Reference(
        title="Test Publication on Medical Research"
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    assert metadata["strategy"] == "title_only"
    assert metadata["query_type"] == "title search"
    assert metadata["search_term"] == reference.title
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "search_by_title"
    assert mock_repository.last_query["title"] == "Test Publication on Medical Research"


def test_execute_with_similar_title(title_only_strategy, mock_repository):
    """Test execution with similar but not exact title match."""
    # Clear other titles for this test
    mock_repository.mock_data["title"] = [
        {
            "id": "W123456789",
            "title": "Test Publication on Medical Research",
            "publication_year": 2023,
            "authorships": [
                {"author": {"display_name": "Smith, J."}},
                {"author": {"display_name": "Johnson, A."}}
            ]
        }
    ]
    
    reference = Reference(
        title="Test Publications in Medical Research"  # Similar but not exact
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"  # Should still find the result


def test_execute_not_found(title_only_strategy):
    """Test execution with no results."""
    reference = Reference(
        title="Completely Different Title"
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_only"
    assert metadata["error"] == "No results found"


def test_execute_below_threshold(title_only_strategy, config):
    """Test execution with title similarity below threshold."""
    # Set a very high threshold that no result will pass
    config.title_similarity_threshold = 0.99
    
    reference = Reference(
        title="Test Publications in Medical Research"  # Similar but not exact
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_only"
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_multiple_matches(title_only_strategy, mock_repository):
    """Test handling multiple matches with ranking."""
    # Use all three test titles
    reference = Reference(
        title="Test Publication on Medical Research"
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    # Should find multiple matches
    assert len(results) > 1
    # They should all have high similarity scores
    assert "_debug" in results[0]
    assert results[0]["_debug"]["title_similarity"] > 0.9
    
    # Results should be sorted by similarity (highest first)
    for i in range(len(results) - 1):
        current_score = results[i]["_debug"]["title_similarity"]
        next_score = results[i + 1]["_debug"]["title_similarity"]
        assert current_score >= next_score


def test_execute_api_error(title_only_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(
        title="Test Publication"
    )
    
    results, metadata = title_only_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]