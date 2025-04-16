"""Tests for the SearchResult model."""
import pytest

from src.domain.enums.search_status import SearchStatus
from src.domain.enums.study_type import StudyType
from src.domain.models.search_result import SearchResult


class TestSearchResult:
    """Tests for the SearchResult model."""

    def test_to_json_found(self):
        """Test to_json with a found search result."""
        search_result = SearchResult(
            study_id="STD-1",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.FOUND,
            strategy="doi",
            openalex_id="W123",
            pdf_url="https://example.com/paper.pdf",
            title="Test Paper",
            journal="Test Journal",
            year=2023,
            doi="https://doi.org/10.1234/test",
            open_access=True,
            citation_count=5,
            search_details={
                "query_type": "doi filter",
                "search_term": "10.1234/test",
                "strategy": "doi"
            }
        )
        result = search_result.to_json()
        
        assert result["study_id"] == "STD-1"
        assert result["study_type"] == "included"
        assert result["status"] == "found"
        assert result["strategy"] == "doi"
        assert result["openalex_id"] == "W123"
        assert result["pdf_url"] == "https://example.com/paper.pdf"
        assert result["title"] == "Test Paper"
        assert result["journal"] == "Test Journal"
        assert result["year"] == 2023
        assert result["doi"] == "https://doi.org/10.1234/test"
        assert result["open_access"] == True
        assert result["citation_count"] == 5
        assert result["search_details"]["query_type"] == "doi filter"
        assert result["search_details"]["search_term"] == "10.1234/test"
        assert result["search_details"]["strategy"] == "doi"
        assert "search_attempts" not in result
        assert "original_reference" not in result
    
    def test_to_json_not_found(self):
        """Test to_json with a not found search result."""
        search_result = SearchResult(
            study_id="STD-2",
            study_type=StudyType.EXCLUDED,
            status=SearchStatus.NOT_FOUND,
            search_attempts=[
                {
                    "strategy": "title_only",
                    "query_type": "title.search",
                    "search_term": "Test Paper"
                }
            ],
            original_reference={
                "title": "Test Paper",
                "year": 2022,
                "journal": "Unknown Journal"
            }
        )
        result = search_result.to_json()
        
        assert result["study_id"] == "STD-2"
        assert result["study_type"] == "excluded"
        assert result["status"] == "not_found"
        assert "strategy" not in result
        assert "openalex_id" not in result
        assert "pdf_url" not in result
        assert "search_details" not in result
        assert len(result["search_attempts"]) == 1
        assert result["search_attempts"][0]["strategy"] == "title_only"
        assert result["search_attempts"][0]["query_type"] == "title.search"
        assert result["search_attempts"][0]["search_term"] == "Test Paper"
        assert result["original_reference"]["title"] == "Test Paper"
        assert result["original_reference"]["year"] == 2022
        assert result["original_reference"]["journal"] == "Unknown Journal"
    
    def test_to_json_rejected(self):
        """Test to_json with a rejected search result."""
        search_result = SearchResult(
            study_id="STD-3",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.REJECTED,
            search_attempts=[
                {
                    "strategy": "title_only",
                    "query_type": "title.search",
                    "search_term": "Test Paper",
                    "error": "Low similarity score (0.65)"
                }
            ],
            original_reference={
                "title": "Test Paper",
                "year": 2021
            }
        )
        result = search_result.to_json()
        
        assert result["study_id"] == "STD-3"
        assert result["study_type"] == "included"
        assert result["status"] == "rejected"
        assert len(result["search_attempts"]) == 1
        assert result["search_attempts"][0]["strategy"] == "title_only"
        assert result["search_attempts"][0]["error"] == "Low similarity score (0.65)"
        assert result["original_reference"]["title"] == "Test Paper"
        assert result["original_reference"]["year"] == 2021
    
    def test_to_json_skipped(self):
        """Test to_json with a skipped search result."""
        search_result = SearchResult(
            study_id="STD-4",
            study_type=StudyType.INCLUDED,
            status=SearchStatus.SKIPPED
        )
        result = search_result.to_json()
        
        assert result["study_id"] == "STD-4"
        assert result["study_type"] == "included"
        assert result["status"] == "skipped"
        assert "strategy" not in result
        assert "openalex_id" not in result
        assert "search_attempts" not in result
        assert "original_reference" not in result