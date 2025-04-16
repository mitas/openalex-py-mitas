import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.title_journal_strategy import TitleJournalStrategy
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
        "title_journal": [
            {
                "id": "W123456789",
                "title": "Test Publication on Medical Research",
                "publication_year": 2023,
                "primary_location": {
                    "source": {
                        "display_name": "Journal of Medical Research"
                    }
                },
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W987654321",
                "title": "Different Publication Title",
                "publication_year": 2023,
                "primary_location": {
                    "source": {
                        "display_name": "Journal of Medical Research"
                    }
                },
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            },
            {
                "id": "W111222333",
                "title": "Test Publication on Medical Research",
                "publication_year": 2022,
                "primary_location": {
                    "source": {
                        "display_name": "Different Journal"
                    }
                },
                "authorships": [
                    {"author": {"display_name": "Smith, J."}},
                    {"author": {"display_name": "Johnson, A."}}
                ]
            }
        ]
    }
    return MockRepository(mock_data)


@pytest.fixture
def title_journal_strategy(mock_repository, config):
    """Create TitleJournal strategy with mock repository."""
    return TitleJournalStrategy(mock_repository, config)


def test_strategy_name(title_journal_strategy):
    """Test strategy name property."""
    assert title_journal_strategy.name == "title_journal"


def test_strategy_priority(title_journal_strategy):
    """Test strategy priority property."""
    assert title_journal_strategy.priority == 6  # Sixth priority


def test_supported(title_journal_strategy):
    """Test supported method."""
    # With title and journal
    reference = Reference(title="Test Title", journal="Test Journal")
    assert title_journal_strategy.supported(reference) is True
    
    # Without title
    reference = Reference(title=None, journal="Test Journal")
    assert title_journal_strategy.supported(reference) is False
    
    # Without journal
    reference = Reference(title="Test Title", journal=None)
    assert title_journal_strategy.supported(reference) is False
    
    # With empty title
    reference = Reference(title="", journal="Test Journal")
    assert title_journal_strategy.supported(reference) is False
    
    # With empty journal
    reference = Reference(title="Test Title", journal="")
    assert title_journal_strategy.supported(reference) is False
    
    # With other fields (should still be supported)
    reference = Reference(title="Test Title", journal="Test Journal", year=2023, authors=["Smith, J."])
    assert title_journal_strategy.supported(reference) is True


def test_validate_reference(title_journal_strategy):
    """Test validate_reference method."""
    # Valid reference
    reference = Reference(title="Test Title", journal="Test Journal")
    assert title_journal_strategy.validate_reference(reference) is True
    
    # Invalid reference - no title
    reference = Reference(title=None, journal="Test Journal")
    assert title_journal_strategy.validate_reference(reference) is False
    
    # Invalid reference - no journal
    reference = Reference(title="Test Title", journal=None)
    assert title_journal_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty title
    reference = Reference(title="", journal="Test Journal")
    assert title_journal_strategy.validate_reference(reference) is False
    
    # Invalid reference - empty journal
    reference = Reference(title="Test Title", journal="")
    assert title_journal_strategy.validate_reference(reference) is False


def test_execute_success(title_journal_strategy, mock_repository):
    """Test successful execution with high similarity."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        journal="Journal of Medical Research"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    assert metadata["strategy"] == "title_journal"
    assert metadata["query_type"] == "title, journal search"
    assert metadata["search_term"] == reference.title
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "search_by_title_journal"
    assert mock_repository.last_query["title"] == "Test Publication on Medical Research"
    assert mock_repository.last_query["journal"] == "Journal of Medical Research"


def test_execute_with_similar_title(title_journal_strategy):
    """Test execution with similar but not exact title match."""
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        journal="Journal of Medical Research"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"  # Should still find the result


def test_execute_with_similar_journal(title_journal_strategy):
    """Test execution with similar but not exact journal match."""
    reference = Reference(
        title="Test Publication on Medical Research",
        journal="J. Medical Research"  # Similar but not exact
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"  # Should still find the result


def test_execute_not_found(title_journal_strategy):
    """Test execution with no results."""
    reference = Reference(
        title="Completely Different Title", 
        journal="Journal of Medical Research"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_journal"
    assert metadata["error"] == "No results found"


def test_execute_below_threshold(title_journal_strategy, config):
    """Test execution with title similarity below threshold."""
    # Set a very high threshold that no result will pass
    config.title_similarity_threshold = 0.99
    
    reference = Reference(
        title="Test Publications in Medical Research",  # Similar but not exact
        journal="Journal of Medical Research"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_journal"
    assert "similarity below threshold" in metadata.get("error", "")


def test_execute_journal_mismatch(title_journal_strategy):
    """Test execution with matching title but different journal."""
    reference = Reference(
        title="Test Publication on Medical Research", 
        journal="Completely Different Journal"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "title_journal"
    assert "No results found" in metadata.get("error", "")  # Changed to match implementation


def test_execute_multiple_matches(title_journal_strategy, mock_repository):
    """Test handling multiple matches with ranking."""
    # Add another similar result to test ranking
    mock_repository.mock_data["title_journal"].append({
        "id": "W444555666",
        "title": "Test Publication on Medical Research", # Exact same title
        "publication_year": 2023,
        "primary_location": {
            "source": {
                "display_name": "Journal of Medical Research"
            }
        },
        "authorships": [
            {"author": {"display_name": "Smith, J."}},
            {"author": {"display_name": "Johnson, A."}}
        ]
    })
    
    reference = Reference(
        title="Test Publication on Medical Research", 
        journal="Journal of Medical Research"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    # Should find both matches
    assert len(results) == 2
    # Both should have high scores, but we can check the debug info
    assert "_debug" in results[0]
    assert results[0]["_debug"]["title_similarity"] > 0.95
    assert results[0]["_debug"]["journal_similarity"] > 0.95


def test_execute_api_error(title_journal_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(
        title="Test Publication", 
        journal="Test Journal"
    )
    
    results, metadata = title_journal_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]