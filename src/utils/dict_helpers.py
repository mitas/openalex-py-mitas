# src/utils/dict_helpers.py
"""Helper functions for dictionary operations."""

from typing import Any, Dict, Optional

from loguru import logger


def add_optional_field(
    result_dict: Dict[str, Any], field_name: str, value: Optional[Any]
) -> Dict[str, Any]:
    """
    Add a field to a dictionary only if the value is not None.

    Args:
        result_dict: The dictionary to add the field to.
        field_name: The name of the field.
        value: The value to add.

    Returns:
        The modified dictionary (for convenience).
    """
    if not field_name:
        logger.warning("Empty field name provided to add_optional_field, ignoring.")
        return result_dict

    if value is not None:
        result_dict[field_name] = value

    return result_dict
