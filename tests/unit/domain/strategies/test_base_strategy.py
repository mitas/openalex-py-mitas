import pytest
from typing import Dict, List, Tuple, Any

from src.domain.models.reference import Reference
from src.domain.strategies.base_strategy import BaseStrategy


class ConcreteStrategy(BaseStrategy):
    """Concrete implementation of BaseStrategy for testing."""
    
    @property
    def name(self) -> str:
        return "test_strategy"
    
    @property
    def priority(self) -> int:
        return 999
    
    def supported(self, reference: Reference) -> bool:
        return self.validate_reference(reference)
    
    def validate_reference(self, reference: Reference) -> bool:
        if reference.title is None:
            return False
        return True
    
    def execute(self, reference: Reference) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        return [], {"strategy": "test_strategy"}


def test_normalize_text():
    """Test text normalization."""
    strategy = ConcreteStrategy()
    
    # Test with regular text
    assert strategy.normalize_text("Test Title!") == "test title"
    
    # Test with uppercase and special characters
    assert strategy.normalize_text("TEST@#$%^Title") == "test title"
    
    # Test with empty string
    assert strategy.normalize_text("") == ""
    
    # Test with None
    assert strategy.normalize_text(None) == ""
    
    # Test with whitespace
    assert strategy.normalize_text("  test  title  ") == "test title"
    
    # Test with mixed case and numbers
    assert strategy.normalize_text("Title 123 Test") == "title 123 test"
    
    # Test with punctuation that should be replaced with spaces
    assert strategy.normalize_text("title:with,punctuation") == "title with punctuation"
    
    # Test with multiple spaces that should be consolidated
    assert strategy.normalize_text("too    many   spaces") == "too many spaces"


def test_log_attempt(monkeypatch, caplog):
    """Test logging of search attempts."""
    strategy = ConcreteStrategy()
    reference = Reference(title="Test Study")
    
    # Test successful logging
    strategy.log_attempt(reference, 1)
    
    # Test with no title
    strategy.log_attempt(Reference(title=None), 0, "API Timeout")
    
    # Test with exception during logging (should not raise)
    def mock_info(*args, **kwargs):
        raise Exception("Logging error")
    
    # Patch the logger to raise exception
    monkeypatch.setattr("loguru.logger.info", mock_info)
    
    # This should not raise an exception
    strategy.log_attempt(reference, 1)


def test_validate_reference_abstract():
    """Test that validate_reference is abstract and must be implemented."""
    # Cannot instantiate BaseStrategy directly
    with pytest.raises(TypeError):
        BaseStrategy()


def test_concrete_strategy_implementation():
    """Test concrete implementation of BaseStrategy."""
    strategy = ConcreteStrategy()
    
    # Test properties
    assert strategy.name == "test_strategy"
    assert strategy.priority == 999
    
    # Test supported method
    assert strategy.supported(Reference(title="Test")) is True
    assert strategy.supported(Reference(title=None)) is False
    
    # Test execute method
    results, metadata = strategy.execute(Reference(title="Test"))
    assert results == []
    assert metadata == {"strategy": "test_strategy"}