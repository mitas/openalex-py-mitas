"""Tests for the Config model."""
import os
from unittest.mock import patch

import pytest

from src.domain.models.config import Config


class TestConfig:
    """Tests for the Config model."""

    def test_default_values(self):
        """Test default values when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_env()
            
            assert config.openalex_email is None
            assert config.title_similarity_threshold == 0.85
            assert config.author_similarity_threshold == 0.9
            assert config.disable_strategies == []
            assert config.max_retries == 3
            assert config.retry_backoff_factor == 0.5
            assert config.retry_http_codes == [429, 500, 503]
            assert config.concurrency == 20
    
    def test_from_env_with_values(self):
        """Test loading values from environment variables."""
        env_vars = {
            "OPENALEX_EMAIL": "test@example.com",
            "TITLE_SIMILARITY_THRESHOLD": "0.75",
            "AUTHOR_SIMILARITY_THRESHOLD": "0.8",
            "DISABLE_STRATEGIES": "doi,pmid",
            "MAX_RETRIES": "5",
            "RETRY_BACKOFF_FACTOR": "1.0",
            "RETRY_HTTP_CODES": "429,503",
            "CONCURRENCY": "10"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            
            assert config.openalex_email == "test@example.com"
            assert config.title_similarity_threshold == 0.75
            assert config.author_similarity_threshold == 0.8
            assert config.disable_strategies == ["doi", "pmid"]
            assert config.max_retries == 5
            assert config.retry_backoff_factor == 1.0
            assert config.retry_http_codes == [429, 503]
            assert config.concurrency == 10
    
    def test_validate_corrects_thresholds(self):
        """Test that validate corrects invalid threshold values."""
        # Test with threshold values out of range
        config = Config(
            title_similarity_threshold=-0.1,
            author_similarity_threshold=1.5
        )
        config.validate()
        
        assert config.title_similarity_threshold == 0.85  # Reset to default
        assert config.author_similarity_threshold == 0.9  # Reset to default
    
    def test_validate_corrects_retries(self):
        """Test that validate corrects invalid retries values."""
        config = Config(max_retries=-1, retry_backoff_factor=-0.1)
        config.validate()
        
        assert config.max_retries == 3  # Reset to default
        assert config.retry_backoff_factor == 0.5  # Reset to default
    
    def test_validate_corrects_concurrency(self):
        """Test that validate corrects invalid concurrency values."""
        config = Config(concurrency=0)
        config.validate()
        
        assert config.concurrency == 20  # Reset to default
    
    def test_empty_disable_strategies(self):
        """Test that empty disable_strategies means all strategies are enabled."""
        with patch.dict(os.environ, {"DISABLE_STRATEGIES": ""}, clear=True):
            config = Config.from_env()
            
            assert config.disable_strategies == []