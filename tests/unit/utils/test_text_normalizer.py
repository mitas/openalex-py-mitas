"""Tests for text normalization utilities."""
import pytest

from src.utils.text_normalizer import TextNormalizer


def test_normalize_text():
    """Test text normalization."""
    # Test with regular text
    assert TextNormalizer.normalize_text("Test Title!") == "test title"
    
    # Test with uppercase and special characters
    assert TextNormalizer.normalize_text("TEST@#$%^Title") == "test title"
    
    # Test with empty string
    assert TextNormalizer.normalize_text("") == ""
    
    # Test with None
    assert TextNormalizer.normalize_text(None) == ""
    
    # Test with whitespace
    assert TextNormalizer.normalize_text("  test  title  ") == "test title"
    
    # Test with mixed case and numbers
    assert TextNormalizer.normalize_text("Title 123 Test") == "title 123 test"
    
    # Test with punctuation that should be replaced with spaces
    assert TextNormalizer.normalize_text("title:with,punctuation") == "title with punctuation"
    
    # Test with multiple spaces that should be consolidated
    assert TextNormalizer.normalize_text("too    many   spaces") == "too many spaces"