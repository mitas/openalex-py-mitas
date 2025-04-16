import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.doi_strategy import DoiStrategy
from .mock_repository import MockRepository


@pytest.fixture
def mock_repository():
    """Create mock repository with test data."""
    mock_data = {
        "doi": {
            "10.1234/test": {
                "id": "W123456789",
                "title": "Test Publication",
                "doi": "10.1234/test"
            }
        }
    }
    return MockRepository(mock_data)


@pytest.fixture
def doi_strategy(mock_repository):
    """Create DOI strategy with mock repository."""
    return DoiStrategy(mock_repository)


def test_strategy_name(doi_strategy):
    """Test strategy name property."""
    assert doi_strategy.name == "doi"


def test_strategy_priority(doi_strategy):
    """Test strategy priority property."""
    assert doi_strategy.priority == 1  # Highest priority


def test_supported(doi_strategy):
    """Test supported method."""
    # With DOI
    reference = Reference(doi="10.1234/test")
    assert doi_strategy.supported(reference) is True
    
    # Without DOI
    reference = Reference(doi=None)
    assert doi_strategy.supported(reference) is False
    
    # With empty DOI
    reference = Reference(doi="")
    assert doi_strategy.supported(reference) is False


def test_validate_reference(doi_strategy):
    """Test validate_reference method."""
    # Valid DOI
    reference = Reference(doi="10.1234/test")
    assert doi_strategy.validate_reference(reference) is True
    
    # Invalid DOI format
    reference = Reference(doi="invalid-doi")
    with pytest.raises(ValueError, match="Invalid DOI format"):
        doi_strategy.validate_reference(reference)
    
    # Valid DOI with special characters
    reference = Reference(doi="10.1234/test-123_456:789")
    assert doi_strategy.validate_reference(reference) is True


def test_execute_success(doi_strategy, mock_repository):
    """Test successful execution."""
    reference = Reference(doi="10.1234/test", title="Test Title")
    results, metadata = doi_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    assert results[0]["title"] == "Test Publication"
    
    assert metadata["strategy"] == "doi"
    assert metadata["query_type"] == "doi filter"
    assert metadata["search_term"] == "10.1234/test"
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "get_by_doi"
    assert mock_repository.last_query["doi"] == "10.1234/test"  # normalized


def test_execute_not_found(doi_strategy):
    """Test execution with no results."""
    reference = Reference(doi="10.1234/nonexistent", title="Nonexistent Title")
    results, metadata = doi_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "doi"
    assert metadata["error"] == "No results found"


def test_execute_with_whitespace(doi_strategy, mock_repository):
    """Test execution with whitespace in DOI."""
    # DOI with spaces that should be normalized
    reference = Reference(doi=" 10.1234/test ", title="Test Title With Spaces")
    results, metadata = doi_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    # Check that spaces were removed in the repository query
    assert mock_repository.last_query["doi"] == "10.1234/test"


def test_execute_invalid_doi(doi_strategy):
    """Test execution with invalid DOI format."""
    reference = Reference(doi="invalid-doi", title="Invalid DOI")
    results, metadata = doi_strategy.execute(reference)
    
    assert len(results) == 0
    assert "Validation error" in metadata["error"]
    assert "Invalid DOI format" in metadata["error"]


def test_execute_api_error(doi_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(doi="10.1234/test", title="Test Title")
    results, metadata = doi_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]