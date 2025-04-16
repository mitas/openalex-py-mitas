import pytest
from typing import Dict, List, Tuple, Any

from src.domain.interfaces.search_strategy import SearchStrategy
from src.domain.models.reference import Reference


def test_search_strategy_cannot_be_instantiated():
    """Test that SearchStrategy cannot be instantiated directly."""
    with pytest.raises(TypeError):
        SearchStrategy()


class PartialSearchStrategy(SearchStrategy):
    """Partial implementation of SearchStrategy for testing."""
    
    @property
    def name(self) -> str:
        return "partial"
    
    # Missing other methods


def test_partial_implementation_raises_error():
    """Test that partial implementation raises TypeError."""
    with pytest.raises(TypeError):
        PartialSearchStrategy()


class PriorityOnlySearchStrategy(SearchStrategy):
    """Implementation with only priority method."""
    
    @property
    def priority(self) -> int:
        return 100
    
    # Missing other methods


def test_priority_only_implementation_raises_error():
    """Test that implementation with only priority raises TypeError."""
    with pytest.raises(TypeError):
        PriorityOnlySearchStrategy()


class SupportedOnlySearchStrategy(SearchStrategy):
    """Implementation with only supported method."""
    
    def supported(self, reference: Reference) -> bool:
        return False
    
    # Missing other methods


def test_supported_only_implementation_raises_error():
    """Test that implementation with only supported raises TypeError."""
    with pytest.raises(TypeError):
        SupportedOnlySearchStrategy()


class ExecuteOnlySearchStrategy(SearchStrategy):
    """Implementation with only execute method."""
    
    def execute(self, reference: Reference) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return [], {}
    
    # Missing other methods


def test_execute_only_implementation_raises_error():
    """Test that implementation with only execute raises TypeError."""
    with pytest.raises(TypeError):
        ExecuteOnlySearchStrategy()


class TestConcreteSearchStrategy(SearchStrategy):
    """Concrete implementation of SearchStrategy for testing."""
    
    @property
    def name(self) -> str:
        """Return the name of the strategy."""
        return "test_strategy"
    
    @property
    def priority(self) -> int:
        """Return the priority of the strategy."""
        return 999
    
    def supported(self, reference: Reference) -> bool:
        """Check if the strategy can be used for the given reference."""
        return reference.title is not None
    
    def execute(self, reference: Reference) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Execute the search strategy for the given reference."""
        results = [{"id": "W123", "title": reference.title or "Unknown"}]
        metadata = {
            "strategy": self.name,
            "query_type": "test_query",
            "search_term": reference.title or ""
        }
        return results, metadata


def test_search_strategy_can_be_implemented():
    """Test that SearchStrategy can be implemented."""
    strategy = TestConcreteSearchStrategy()
    assert strategy.name == "test_strategy"
    assert strategy.priority == 999
    
    # Test supported method with valid reference
    reference_with_title = Reference(title="Test Title")
    assert strategy.supported(reference_with_title) is True
    
    # Test supported method with invalid reference
    reference_without_title = Reference(title=None)
    assert strategy.supported(reference_without_title) is False
    
    # Test execute method with valid reference
    results, metadata = strategy.execute(reference_with_title)
    assert len(results) == 1
    assert results[0]["title"] == "Test Title"
    assert metadata["strategy"] == "test_strategy"
    assert metadata["query_type"] == "test_query"
    assert metadata["search_term"] == "Test Title"
    
    # Test execute method with invalid reference
    results, metadata = strategy.execute(reference_without_title)
    assert len(results) == 1
    assert results[0]["title"] == "Unknown"
    assert metadata["strategy"] == "test_strategy"
    assert metadata["search_term"] == ""