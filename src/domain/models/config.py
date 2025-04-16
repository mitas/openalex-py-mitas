# src/domain/models/config.py
"""Configuration model for the OpenAlex publication matching system."""

import os
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Config(BaseModel):
    """
    Configuration settings for the system.
    Loads from environment variables with sensible defaults.
    """

    openalex_email: Optional[str] = Field(default=None, env="OPENALEX_EMAIL")
    title_similarity_threshold: float = Field(default=0.85, env="TITLE_SIMILARITY_THRESHOLD")
    author_similarity_threshold: float = Field(default=0.90, env="AUTHOR_SIMILARITY_THRESHOLD")
    disable_strategies: List[str] = Field(default_factory=list, env="DISABLE_STRATEGIES")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_backoff_factor: float = Field(default=0.5, env="RETRY_BACKOFF_FACTOR")
    retry_http_codes: List[int] = Field(default_factory=lambda: [429, 500, 503], env="RETRY_HTTP_CODES")
    concurrency: int = Field(default=20, env="CONCURRENCY")
    allow_missing_year: bool = Field(default=False, env="ALLOW_MISSING_YEAR") # Added for has_minimal_data

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        # Allow reading env vars case-insensitively for convenience
        case_sensitive = False
        # Needed to properly parse list from env var string
        json_loads = lambda v: [s.strip().lower() for s in v.split(',')] if isinstance(v, str) else v


    # Validators to ensure values are within reasonable bounds
    @validator('title_similarity_threshold', 'author_similarity_threshold')
    def check_similarity_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Similarity threshold must be between 0.0 and 1.0')
        return v

    @validator('max_retries', 'concurrency')
    def check_positive_integer(cls, v):
        if v < 0:
            raise ValueError('Value must be a non-negative integer')
        return v

    @validator('retry_backoff_factor')
    def check_positive_float(cls, v):
        if v < 0.0:
            raise ValueError('Value must be a non-negative float')
        return v

    @validator('disable_strategies', pre=True, always=True)
    def parse_disable_strategies(cls, v):
        if isinstance(v, str):
            return [s.strip().lower() for s in v.split(',') if s.strip()]
        return v if v else []

    @validator('retry_http_codes', pre=True, always=True)
    def parse_retry_codes(cls, v):
         if isinstance(v, str):
             codes = []
             for code_str in v.split(','):
                 try:
                     codes.append(int(code_str.strip()))
                 except ValueError:
                     # Log warning or ignore invalid codes
                     pass
             return codes if codes else [429, 500, 503]
         return v if v else [429, 500, 503]

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config from environment variables using Pydantic's built-in handling."""
        # Pydantic v2 automatically reads from environment variables if 'env' is set in Field
        # and Config.case_sensitive = False helps find vars like OPENALEX_EMAIL
        return cls()
