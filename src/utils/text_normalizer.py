# src/utils/text_normalizer.py
"""Text normalization utilities."""

import re
from typing import Optional

# Pre-compile regex for efficiency
NON_ALPHANUM_SPACE_REGEX = re.compile(r"[^a-z0-9\s]")
MULTI_SPACE_REGEX = re.compile(r"\s+")

class TextNormalizer:
    """Utility class for text normalization operations."""

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """
        Normalize text: lowercase, remove special chars (keep space), consolidate spaces.

        Args:
            text: Text to normalize.

        Returns:
            Normalized text, or empty string if input is None or empty.
        """
        if not text or not isinstance(text, str):
            return ""

        # Convert to lowercase
        normalized = text.lower()

        # Remove special characters but preserve spaces and numbers
        normalized = NON_ALPHANUM_SPACE_REGEX.sub(" ", normalized)

        # Replace multiple spaces with a single space
        normalized = MULTI_SPACE_REGEX.sub(" ", normalized)

        # Trim leading/trailing spaces
        normalized = normalized.strip()

        return normalized
