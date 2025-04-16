import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.pmid_strategy import PmidStrategy
from .mock_repository import MockRepository


@pytest.fixture
def mock_repository():
    """Create mock repository with test data."""
    mock_data = {
        "pmid": {
            "12345678": {
                "id": "W123456789",
                "title": "Test Publication",
                "pmid": "12345678"
            }
        }
    }
    return MockRepository(mock_data)


@pytest.fixture
def pmid_strategy(mock_repository):
    """Create PMID strategy with mock repository."""
    return PmidStrategy(mock_repository)


def test_strategy_name(pmid_strategy):
    """Test strategy name property."""
    assert pmid_strategy.name == "pmid"


def test_strategy_priority(pmid_strategy):
    """Test strategy priority property."""
    assert pmid_strategy.priority == 2  # Second highest priority


def test_supported(pmid_strategy):
    """Test supported method."""
    # With PMID
    reference = Reference(pmid="12345678")
    assert pmid_strategy.supported(reference) is True
    
    # Without PMID
    reference = Reference(pmid=None)
    assert pmid_strategy.supported(reference) is False
    
    # With empty PMID
    reference = Reference(pmid="")
    assert pmid_strategy.supported(reference) is False


def test_validate_reference(pmid_strategy):
    """Test validate_reference method."""
    # Valid PMID
    reference = Reference(pmid="12345678")
    assert pmid_strategy.validate_reference(reference) is True
    
    # Invalid PMID format (non-numeric)
    reference = Reference(pmid="invalid-pmid")
    with pytest.raises(ValueError, match="Invalid PMID format"):
        pmid_strategy.validate_reference(reference)
    
    # PMID with letters
    reference = Reference(pmid="123ABC")
    with pytest.raises(ValueError, match="Invalid PMID format"):
        pmid_strategy.validate_reference(reference)


def test_execute_success(pmid_strategy, mock_repository):
    """Test successful execution."""
    reference = Reference(pmid="12345678", title="Test Title")
    results, metadata = pmid_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    assert results[0]["title"] == "Test Publication"
    
    assert metadata["strategy"] == "pmid"
    assert metadata["query_type"] == "pmid filter"
    assert metadata["search_term"] == "12345678"
    
    # Check that the correct repository method was called
    assert mock_repository.last_query["method"] == "get_by_pmid"
    assert mock_repository.last_query["pmid"] == "12345678"  # normalized


def test_execute_not_found(pmid_strategy):
    """Test execution with no results."""
    reference = Reference(pmid="99999999", title="Nonexistent Title")
    results, metadata = pmid_strategy.execute(reference)
    
    assert len(results) == 0
    assert metadata["strategy"] == "pmid"
    assert metadata["error"] == "No results found"


def test_execute_with_whitespace(pmid_strategy, mock_repository):
    """Test execution with whitespace in PMID."""
    # PMID with spaces that should be normalized
    reference = Reference(pmid=" 12345678 ", title="Test Title With Spaces")
    results, metadata = pmid_strategy.execute(reference)
    
    assert len(results) == 1
    assert results[0]["id"] == "W123456789"
    
    # Check that spaces were removed in the repository query
    assert mock_repository.last_query["pmid"] == "12345678"


def test_execute_invalid_pmid(pmid_strategy):
    """Test execution with invalid PMID format."""
    reference = Reference(pmid="invalid-pmid", title="Invalid PMID")
    results, metadata = pmid_strategy.execute(reference)
    
    assert len(results) == 0
    assert "Validation error" in metadata["error"]
    assert "Invalid PMID format" in metadata["error"]


def test_execute_api_error(pmid_strategy, mock_repository):
    """Test execution with API error."""
    # Set up repository to raise exception
    mock_repository.raise_exception(Exception("API timeout"))
    
    reference = Reference(pmid="12345678", title="Test Title")
    results, metadata = pmid_strategy.execute(reference)
    
    assert len(results) == 0
    assert "API error" in metadata["error"]
    assert "API timeout" in metadata["error"]