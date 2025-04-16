"""Tests for the Study model."""
import pytest

from src.domain.enums.study_type import StudyType
from src.domain.models.reference import Reference
from src.domain.models.study import Study


class TestStudy:
    """Tests for the Study model."""

    def test_from_json_included_complete(self):
        """Test from_json with a complete included study."""
        data = {
            "study_id": "STD-1",
            "reference": {
                "title": "Test",
                "year": 2023,
                "authors_list": ["Smith"],
                "source": "Journal",
                "doi": "10.1234/test",
                "pmid": "12345678"
            },
            "characteristics": {
                "key": "value"
            }
        }
        study = Study.from_json(data, StudyType.INCLUDED)
        
        assert study.id == "STD-1"
        assert study.type == StudyType.INCLUDED
        assert study.reference.title == "Test"
        assert study.reference.year == 2023
        assert study.reference.authors == ["Smith"]
        assert study.reference.journal == "Journal"
        assert study.reference.doi == "10.1234/test"
        assert study.reference.pmid == "12345678"
        assert study.characteristics == {"key": "value"}
        assert study.exclusion_reason is None
    
    def test_from_json_excluded_complete(self):
        """Test from_json with a complete excluded study."""
        data = {
            "study_id": "STD-2",
            "reference": {
                "title": "Excluded Test",
                "year": 2022
            },
            "reason_for_exclusion": "Did not meet criteria"
        }
        study = Study.from_json(data, StudyType.EXCLUDED)
        
        assert study.id == "STD-2"
        assert study.type == StudyType.EXCLUDED
        assert study.reference.title == "Excluded Test"
        assert study.reference.year == 2022
        assert study.characteristics is None
        assert study.exclusion_reason == "Did not meet criteria"
    
    def test_from_json_empty_study_id(self):
        """Test from_json with an empty study_id."""
        data = {
            "reference": {
                "title": "Test"
            }
        }
        study = Study.from_json(data, StudyType.INCLUDED)
        
        assert study.id == ""
        assert study.reference.title == "Test"
    
    def test_from_json_no_reference(self):
        """Test from_json with no reference."""
        data = {
            "study_id": "STD-3"
        }
        study = Study.from_json(data, StudyType.INCLUDED)
        
        assert study.id == "STD-3"
        assert study.reference.title is None
        assert study.reference.year is None
    
    def test_from_json_included_with_exclusion_reason(self):
        """Test from_json for included study with exclusion_reason (should be ignored)."""
        data = {
            "study_id": "STD-4",
            "reference": {
                "title": "Test"
            },
            "reason_for_exclusion": "Should be ignored"
        }
        study = Study.from_json(data, StudyType.INCLUDED)
        
        assert study.id == "STD-4"
        assert study.type == StudyType.INCLUDED
        assert study.reference.title == "Test"
        assert study.exclusion_reason is None
    
    def test_to_dict_included_complete(self):
        """Test to_dict with a complete included study."""
        study = Study(
            id="STD-1",
            type=StudyType.INCLUDED,
            reference=Reference(
                title="Test",
                year=2023,
                authors=["Smith"],
                journal="Journal",
                doi="10.1234/test",
                pmid="12345678"
            ),
            characteristics={"key": "value"}
        )
        result = study.to_dict()
        
        assert result["id"] == "STD-1"
        assert result["type"] == "included"
        assert result["reference"]["title"] == "Test"
        assert result["reference"]["year"] == 2023
        assert result["reference"]["authors"] == ["Smith"]
        assert result["reference"]["journal"] == "Journal"
        assert result["reference"]["doi"] == "10.1234/test"
        assert result["reference"]["pmid"] == "12345678"
        assert result["characteristics"] == {"key": "value"}
        assert "exclusion_reason" not in result
    
    def test_to_dict_excluded_complete(self):
        """Test to_dict with a complete excluded study."""
        study = Study(
            id="STD-2",
            type=StudyType.EXCLUDED,
            reference=Reference(
                title="Excluded Test",
                year=2022
            ),
            exclusion_reason="Did not meet criteria"
        )
        result = study.to_dict()
        
        assert result["id"] == "STD-2"
        assert result["type"] == "excluded"
        assert result["reference"]["title"] == "Excluded Test"
        assert result["reference"]["year"] == 2022
        assert "characteristics" not in result
        assert result["exclusion_reason"] == "Did not meet criteria"
    
    def test_to_dict_minimal(self):
        """Test to_dict with minimal data."""
        study = Study(
            id="",
            type=StudyType.INCLUDED,
            reference=Reference()
        )
        result = study.to_dict()
        
        assert result["id"] == ""
        assert result["type"] == "included"
        assert result["reference"] == {}