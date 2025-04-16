"""Tests for the report formatter."""
import pytest
from unittest.mock import patch, MagicMock
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.utils.report_formatter import ReportFormatter, EMOJI, STATUS_COLORS, STRATEGY_NAMES
from src.domain.models.config import Config
from src.domain.models.search_result import SearchResult
from src.domain.enums.search_status import SearchStatus
from src.domain.enums.study_type import StudyType


class TestReportFormatter:
    """Tests for the ReportFormatter class."""
    
    @pytest.fixture
    def config(self):
        """Create a test config."""
        return Config(
            title_similarity_threshold=0.9,
            author_similarity_threshold=0.85,
            openalex_email="test@example.com",
            max_retries=3,
            retry_backoff_factor=0.5,
            concurrency=20
        )
    
    @pytest.fixture
    def found_result(self):
        """Create a test search result with status FOUND."""
        return SearchResult(
            study_id="STD-Example-2023",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.FOUND,
            strategy="doi",
            openalex_id="W1234567890",
            pdf_url="https://example.com/paper.pdf",
            title="Example study title",
            journal="Journal of Examples",
            year=2023,
            doi="10.1234/example.2023",
            open_access=True,
            citation_count=5,
            search_details={
                "strategy": "doi",
                "query_type": "doi filter",
                "search_term": "10.1234/example.2023"
            }
        )
    
    @pytest.fixture
    def not_found_result(self):
        """Create a test search result with status NOT_FOUND."""
        return SearchResult(
            study_id="STD-NotFound-2023",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.NOT_FOUND,
            search_attempts=[
                {
                    "strategy": "title_only",
                    "query_type": "title search",
                    "search_term": "Not found study title",
                    "error": "No results found"
                }
            ],
            original_reference={
                "title": "Not found study title",
                "authors": ["Author One"],
                "year": 2022
            }
        )
    
    @pytest.fixture
    def rejected_result(self):
        """Create a test search result with status REJECTED."""
        return SearchResult(
            study_id="STD-Rejected-2023",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.REJECTED,
            search_attempts=[
                {
                    "strategy": "title_authors",
                    "query_type": "title authors search",
                    "search_term": "Rejected study title",
                    "error": "Low similarity: title similarity 0.70 < threshold 0.85"
                }
            ],
            original_reference={
                "title": "Rejected study title",
                "authors": ["Author Two"],
                "year": 2021
            }
        )
    
    @pytest.fixture
    def skipped_result(self):
        """Create a test search result with status SKIPPED."""
        return SearchResult(
            study_id="STD-Skipped-2023",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.SKIPPED,
            original_reference={
                "title": "",
                "authors": [],
                "year": None
            }
        )
    
    def test_init(self, config):
        """Test initialization of ReportFormatter."""
        # Act
        formatter = ReportFormatter(config)
        
        # Assert
        assert formatter.config == config
        assert isinstance(formatter.console, Console)
        assert formatter.results == []
        assert formatter.start_time is not None
    
    def test_generate_config_panel(self, config):
        """Test generation of configuration panel."""
        # Arrange
        formatter = ReportFormatter(config)
        
        # Act
        with patch.object(formatter, 'console') as mock_console:
            formatter.generate_config_panel()
            
            # Assert
            mock_console.print.assert_called_once()
            # Verify the first argument to print is a Panel
            args, _ = mock_console.print.call_args
            assert isinstance(args[0], Panel)
            panel_text = args[0].renderable
            
            # Check that panel contains expected configuration values
            assert f"Title Similarity: {config.title_similarity_threshold:.2f}" in panel_text
            assert f"Author Similarity: {config.author_similarity_threshold:.2f}" in panel_text
            assert f"Email: {config.openalex_email}" in panel_text
            assert f"Max Retries: {config.max_retries}" in panel_text
    
    def test_generate_study_panel_found(self, config, found_result):
        """Test generation of study panel for a FOUND result."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = [found_result]
        
        # Act
        with patch.object(formatter, 'console') as mock_console:
            formatter.generate_study_panels()
            
            # Assert
            assert mock_console.print.call_count > 0
            
            # Verify the arguments to at least one print call
            found_panel = False
            for call in mock_console.print.call_args_list:
                args, _ = call
                if isinstance(args[0], Panel) and "FOUND: STD-Example-2023" in args[0].title:
                    found_panel = True
                    panel_text = args[0].renderable
                    assert "OpenAlex ID: W1234567890" in panel_text
                    assert "Title: Example study title" in panel_text
                    assert "DOI: 10.1234/example.2023" in panel_text
                    assert "Strategy: doi" in panel_text
                    assert "Query Type: doi filter" in panel_text
                    
            assert found_panel, "No panel found for the FOUND result"
    
    def test_generate_study_panel_not_found(self, config, not_found_result):
        """Test generation of study panel for a NOT_FOUND result."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = [not_found_result]
        
        # Act
        with patch.object(formatter, 'console') as mock_console:
            formatter.generate_study_panels()
            
            # Assert
            assert mock_console.print.call_count > 0
            
            # Verify the arguments to at least one print call
            not_found_panel = False
            for call in mock_console.print.call_args_list:
                args, _ = call
                if isinstance(args[0], Panel) and "NOT_FOUND: STD-NotFound-2023" in args[0].title:
                    not_found_panel = True
                    panel_text = args[0].renderable
                    assert "Original Reference:" in panel_text
                    assert "Title: Not found study title" in panel_text
                    assert "Strategy: title_only" in panel_text
                    assert "Error: No results found" in panel_text
                    
            assert not_found_panel, "No panel found for the NOT_FOUND result"
    
    def test_generate_strategy_flow_table(self, config, found_result):
        """Test generation of strategy flow table."""
        # Arrange
        formatter = ReportFormatter(config)
        
        # Act
        table = formatter.generate_strategy_flow_table(found_result)
        
        # Assert
        assert isinstance(table, Table)
        assert "Strategy Flow" in table.title
        assert len(table.columns) == 2
    
    def test_generate_statistics_panel(self, config, found_result, not_found_result, rejected_result, skipped_result):
        """Test generation of statistics panel."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = [found_result, not_found_result, rejected_result, skipped_result]
        
        # Act
        with patch.object(formatter, 'console') as mock_console:
            formatter.generate_statistics_panel()
            
            # Assert
            mock_console.print.assert_called_once()
            # Verify the first argument to print is a Panel
            args, _ = mock_console.print.call_args
            assert isinstance(args[0], Panel)
            panel_text = args[0].renderable
            
            # Check that panel contains expected statistics
            assert "Total Studies Processed: 4" in panel_text
            assert "Success Rate: 25.0%" in panel_text
            assert "Found: 1" in panel_text
            assert "Not Found: 1" in panel_text
            assert "Rejected: 1" in panel_text
            assert "Skipped: 1" in panel_text
            assert "With PDF URL: 1" in panel_text
            assert "Open Access: 1" in panel_text
            assert "With DOI: 1" in panel_text
    
    def test_report_with_all_status_types(self, config, found_result, not_found_result, rejected_result, skipped_result):
        """Test generating a complete report with all status types."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = [found_result, not_found_result, rejected_result, skipped_result]
        
        # Mock the methods to verify they're called
        with patch.object(formatter, 'generate_config_panel') as mock_config, \
             patch.object(formatter, 'generate_study_panels') as mock_studies, \
             patch.object(formatter, 'generate_statistics_panel') as mock_stats:
                
            # Act
            formatter.generate_report()
                
            # Assert
            mock_config.assert_called_once()
            mock_studies.assert_called_once()
            mock_stats.assert_called_once()
    
    def test_report_with_empty_results(self, config):
        """Test generating a report with empty results."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = []
        
        # Act
        with patch.object(formatter, 'console') as mock_console:
            formatter.generate_statistics_panel()
            
            # Assert
            mock_console.print.assert_called_once()
            args, _ = mock_console.print.call_args
            assert isinstance(args[0], Panel)
            panel_text = args[0].renderable
            
            # Check that panel reports zero studies
            assert "Total Studies Processed: 0" in panel_text
            assert "Success Rate: 0.0%" in panel_text
    
    def test_truncate_long_title(self, config):
        """Test that long titles are truncated."""
        # Arrange
        formatter = ReportFormatter(config)
        very_long_title = "A" * 150  # 150 characters
        
        # Act
        truncated = formatter.truncate_text(very_long_title)
        
        # Assert
        assert len(truncated) < 150
        assert truncated.endswith("...")
    
    def test_format_field_value(self, config):
        """Test formatting of field values."""
        # Arrange
        formatter = ReportFormatter(config)
        
        # Act & Assert - Boolean values
        assert "Yes" in formatter.format_field_value(True)
        assert "No" in formatter.format_field_value(False)
        
        # Act & Assert - None values
        assert "Not set" in formatter.format_field_value(None)
        
        # Act & Assert - Numeric values
        assert "42" == formatter.format_field_value(42)
        
        # Act & Assert - String values
        assert "Test string" == formatter.format_field_value("Test string")
    
    def test_generate_improvement_suggestions(self, config, not_found_result, rejected_result):
        """Test generation of improvement suggestions."""
        # Arrange
        formatter = ReportFormatter(config)
        
        # Act - Not found result
        not_found_suggestions = formatter.generate_improvement_suggestions(not_found_result)
        
        # Assert - Not found result
        assert isinstance(not_found_suggestions, list)
        assert any("required fields" in suggestion for suggestion in not_found_suggestions)
        
        # Act - Rejected result
        rejected_suggestions = formatter.generate_improvement_suggestions(rejected_result)
        
        # Assert - Rejected result
        assert isinstance(rejected_suggestions, list)
        assert any("similarity threshold" in suggestion for suggestion in rejected_suggestions)
    
    def test_render_method(self, config, found_result):
        """Test the render method."""
        # Arrange
        formatter = ReportFormatter(config)
        formatter.results = [found_result]
        
        # Mock generate_report to avoid calling it
        with patch.object(formatter, 'generate_report') as mock_generate:
            # Act
            formatter.render()
            
            # Assert
            mock_generate.assert_called_once()