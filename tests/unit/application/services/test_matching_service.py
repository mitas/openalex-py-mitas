"""Tests for the MatchingService."""
import pytest
from unittest.mock import MagicMock, patch

from src.application.services.matching_service import MatchingService
from src.domain.enums.search_status import SearchStatus
from src.domain.enums.study_type import StudyType
from src.domain.models.config import Config
from src.domain.models.reference import Reference
from src.domain.models.study import Study
from src.domain.strategies.doi_strategy import DoiStrategy
from src.domain.strategies.pmid_strategy import PmidStrategy
from src.domain.strategies.title_authors_year_strategy import TitleAuthorsYearStrategy
from src.domain.strategies.title_authors_strategy import TitleAuthorsStrategy
from src.domain.strategies.title_year_strategy import TitleYearStrategy
from src.domain.strategies.title_journal_strategy import TitleJournalStrategy
from src.domain.strategies.title_only_strategy import TitleOnlyStrategy
from src.infrastructure.repositories.openalex_repository import OpenAlexRepository


class TestMatchingService:
    """Tests for the MatchingService."""

    @pytest.fixture
    def config(self):
        """Create a config fixture."""
        return Config(
            title_similarity_threshold=0.85,
            author_similarity_threshold=0.9,
            openalex_email="test@example.com"
        )
    
    @pytest.fixture
    def service(self, config):
        """Create a matching service fixture."""
        return MatchingService(config)
    
    def test_initialization_with_default_config(self, config):
        """Test service initialization with default config."""
        # Arrange & Act
        service = MatchingService(config)
        
        # Assert
        assert isinstance(service.repository, OpenAlexRepository)
        assert len(service.strategies) == 7  # All 7 strategies
        
        # Verify strategies are sorted by priority
        for i in range(len(service.strategies) - 1):
            assert service.strategies[i].priority <= service.strategies[i + 1].priority
            
        # Check for specific strategies
        strategy_types = [type(strategy) for strategy in service.strategies]
        assert DoiStrategy in strategy_types
        assert PmidStrategy in strategy_types
        assert TitleAuthorsYearStrategy in strategy_types
        assert TitleAuthorsStrategy in strategy_types
        assert TitleYearStrategy in strategy_types
        assert TitleJournalStrategy in strategy_types
        assert TitleOnlyStrategy in strategy_types
    
    def test_initialization_with_disabled_strategies(self):
        """Test service initialization with disabled strategies."""
        # Arrange
        config = Config(disable_strategies=["doi", "pmid"])
        
        # Act
        service = MatchingService(config)
        
        # Assert
        assert isinstance(service.repository, OpenAlexRepository)
        assert len(service.strategies) == 5  # Only 5 strategies (2 disabled)
        
        # Verify DOI and PMID strategies are not present
        strategy_types = [type(strategy) for strategy in service.strategies]
        assert DoiStrategy not in strategy_types
        assert PmidStrategy not in strategy_types
    
    def test_match_study_without_minimal_data(self, service):
        """Test matching a study that doesn't have minimal data."""
        # Arrange
        reference = Reference(title="", authors=[], year=None)
        study = Study(id="123", type=StudyType.INCLUDED, reference=reference)
        
        # Act
        result = service.match_study(study)
        
        # Assert
        assert result.study_id == "123"
        assert result.study_type == StudyType.INCLUDED
        assert result.status == SearchStatus.SKIPPED
        assert result.original_reference == reference.to_dict()
    
    def test_match_study_with_successful_doi_strategy(self, service):
        """Test matching a study with a successful DOI strategy."""
        # Arrange
        reference = Reference(
            title="Test Study", 
            authors=["Author One"], 
            year=2020,
            doi="10.1234/test"
        )
        study = Study(id="123", type=StudyType.INCLUDED, reference=reference)
        
        # Create a mock doi_strategy that will be successful
        mock_doi_strategy = MagicMock()
        mock_doi_strategy.name = "doi"
        mock_doi_strategy.priority = 1
        mock_doi_strategy.supported.return_value = True
        
        # Publication data that will be returned by the strategy
        publication_data = {
            "id": "https://openalex.org/W123456789",
            "title": "Test Study",
            "authorships": [{"author": {"display_name": "Author One"}}],
            "publication_year": 2020,
            "doi": "10.1234/test",
            "primary_location": {"source": {"display_name": "Test Journal"}},
            "open_access": {"is_oa": True},
            "cited_by_count": 10
        }
        
        # Mock strategy execution to return the publication data
        mock_doi_strategy.execute.return_value = (
            [publication_data], 
            {"strategy": "doi", "query_type": "doi filter", "search_term": "10.1234/test"}
        )
        
        # Replace the strategies with our mock
        service.strategies = [mock_doi_strategy]
        
        # Act
        result = service.match_study(study)
        
        # Assert
        assert result.study_id == "123"
        assert result.study_type == StudyType.INCLUDED
        assert result.status == SearchStatus.FOUND
        assert result.strategy == "doi"
        assert result.openalex_id == "W123456789"
        assert result.title == "Test Study"
        assert result.journal == "Test Journal"
        assert result.year == 2020
        assert result.doi == "10.1234/test"
        assert result.open_access is True
        assert result.citation_count == 10
        mock_doi_strategy.supported.assert_called_once_with(reference)
        mock_doi_strategy.execute.assert_called_once_with(reference)
    
    def test_match_study_with_all_strategies_failing(self, service):
        """Test matching a study where all strategies fail."""
        # Arrange
        reference = Reference(
            title="Test Study", 
            authors=["Author One"], 
            year=2020
        )
        study = Study(id="123", type=StudyType.INCLUDED, reference=reference)
        
        # Create mock strategies that will all fail
        mock_strategies = []
        for i, name in enumerate(["title_authors_year", "title_authors", "title_only"]):
            mock_strategy = MagicMock()
            mock_strategy.name = name
            mock_strategy.priority = i + 1
            mock_strategy.supported.return_value = True
            mock_strategy.execute.return_value = (
                [], 
                {"strategy": name, "query_type": "mock", "search_term": "test", "error": "No results found"}
            )
            mock_strategies.append(mock_strategy)
        
        # Replace the strategies with our mocks
        service.strategies = mock_strategies
        
        # Act
        result = service.match_study(study)
        
        # Assert
        assert result.study_id == "123"
        assert result.study_type == StudyType.INCLUDED
        assert result.status == SearchStatus.NOT_FOUND
        assert result.search_attempts is not None
        assert len(result.search_attempts) == 3  # All three strategies attempted
        assert result.original_reference == reference.to_dict()
        
        # Verify each strategy was called
        for mock_strategy in mock_strategies:
            mock_strategy.supported.assert_called_once_with(reference)
            mock_strategy.execute.assert_called_once_with(reference)
    
    def test_match_study_with_results_below_threshold(self, service):
        """Test matching a study where results are found but rejected due to low similarity."""
        # Arrange
        reference = Reference(
            title="Test Study", 
            authors=["Author One"], 
            year=2020
        )
        study = Study(id="123", type=StudyType.INCLUDED, reference=reference)
        
        # Create a mock strategy that returns results but will be rejected
        mock_strategy = MagicMock()
        mock_strategy.name = "title_only"
        mock_strategy.priority = 7
        mock_strategy.supported.return_value = True
        
        # Publication data that will be returned by the strategy but with low similarity
        publication_data = {
            "id": "https://openalex.org/W123456789",
            "title": "Similar but Different Study",  # This title is different enough to be rejected
            "authorships": [{"author": {"display_name": "Author One"}}],
            "publication_year": 2020,
            "_debug": {"title_similarity": 0.75}  # Below threshold (0.85)
        }
        
        # Mock strategy execution to return the publication data
        mock_strategy.execute.return_value = (
            [publication_data], 
            {"strategy": "title_only", "query_type": "title search", "search_term": "Test Study"}
        )
        
        # Replace the strategies with our mock
        service.strategies = [mock_strategy]
        
        # Act
        result = service.match_study(study)
        
        # Assert
        assert result.study_id == "123"
        assert result.study_type == StudyType.INCLUDED
        assert result.status == SearchStatus.REJECTED
        assert result.search_attempts is not None
        assert len(result.search_attempts) == 1
        assert result.original_reference == reference.to_dict()
        assert "Low similarity" in result.search_attempts[0].get("error", "")
    
    def test_match_study_api_error(self, service):
        """Test handling of API errors during matching."""
        # Arrange
        reference = Reference(
            title="Test Study", 
            authors=["Author One"], 
            year=2020,
            doi="10.1234/test"
        )
        study = Study(id="123", type=StudyType.INCLUDED, reference=reference)
        
        # Create a mock strategy that raises an API error
        mock_strategy = MagicMock()
        mock_strategy.name = "doi"
        mock_strategy.priority = 1
        mock_strategy.supported.return_value = True
        
        # Mock execution to return an API error
        mock_strategy.execute.return_value = (
            [], 
            {"strategy": "doi", "error": "API timeout error", "query_type": "doi filter", "search_term": "10.1234/test"}
        )
        
        # Replace the strategies with our mock
        service.strategies = [mock_strategy]
        
        # Act
        result = service.match_study(study)
        
        # Assert
        assert result.study_id == "123"
        assert result.study_type == StudyType.INCLUDED
        assert result.status == SearchStatus.NOT_FOUND
        assert result.search_attempts is not None
        assert len(result.search_attempts) == 1
        assert "API timeout error" in result.search_attempts[0].get("error", "")