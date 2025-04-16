# src/domain/strategies/__init__.py
from .base_strategy import BaseStrategy
# Import new and updated strategies
from .identifier_strategy import IdentifierStrategy
from .title_authors_year_strategy import TitleAuthorsYearStrategy
from .title_authors_strategy import TitleAuthorsStrategy
from .title_year_strategy import TitleYearStrategy
from .title_only_strategy import TitleOnlyStrategy

# Expose strategies for potential dynamic loading or type checking
__all__ = [
    "BaseStrategy",
    "IdentifierStrategy",
    "TitleAuthorsYearStrategy",
    "TitleAuthorsStrategy",
    "TitleYearStrategy",
    "TitleOnlyStrategy",
]
