"""Tests for dictionary helper functions."""
import pytest
from unittest.mock import patch

from src.utils.dict_helpers import add_optional_field


class TestDictHelpers:
    """Tests for dictionary helper functions."""
    
    def test_add_optional_field_with_value(self):
        """Test adding a field with a non-None value."""
        # Arrange
        test_dict = {}
        
        # Act
        result = add_optional_field(test_dict, "key", "value")
        
        # Assert
        assert "key" in test_dict
        assert test_dict["key"] == "value"
        assert result is test_dict  # Returns the same dict object
    
    def test_add_optional_field_with_none(self):
        """Test adding a field with None value (should not add)."""
        # Arrange
        test_dict = {}
        
        # Act
        result = add_optional_field(test_dict, "key", None)
        
        # Assert
        assert "key" not in test_dict
        assert result is test_dict
    
    def test_add_optional_field_with_empty_string_value(self):
        """Test adding a field with empty string value (should add)."""
        # Arrange
        test_dict = {}
        
        # Act
        result = add_optional_field(test_dict, "key", "")
        
        # Assert
        assert "key" in test_dict
        assert test_dict["key"] == ""
        assert result is test_dict
    
    def test_add_optional_field_with_zero_value(self):
        """Test adding a field with zero value (should add)."""
        # Arrange
        test_dict = {}
        
        # Act
        result = add_optional_field(test_dict, "key", 0)
        
        # Assert
        assert "key" in test_dict
        assert test_dict["key"] == 0
        assert result is test_dict
    
    def test_add_optional_field_with_false_value(self):
        """Test adding a field with False value (should add)."""
        # Arrange
        test_dict = {}
        
        # Act
        result = add_optional_field(test_dict, "key", False)
        
        # Assert
        assert "key" in test_dict
        assert test_dict["key"] is False
        assert result is test_dict
    
    def test_add_optional_field_with_empty_key(self):
        """Test adding a field with empty key (should log warning and not add)."""
        # Arrange
        test_dict = {}
        
        # Act
        with patch("src.utils.dict_helpers.logger.warning") as mock_warning:
            result = add_optional_field(test_dict, "", "value")
            
            # Assert
            mock_warning.assert_called_once()
            assert len(test_dict) == 0  # No field added
            assert result is test_dict
    
    def test_add_optional_field_with_existing_key(self):
        """Test adding a field with an existing key (should update)."""
        # Arrange
        test_dict = {"key": "old_value"}
        
        # Act
        result = add_optional_field(test_dict, "key", "new_value")
        
        # Assert
        assert test_dict["key"] == "new_value"
        assert result is test_dict