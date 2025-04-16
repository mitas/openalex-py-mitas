"""Tests for the Reference model."""
import pytest

from src.domain.models.reference import Reference


class TestReference:
    """Tests for the Reference model."""

    def test_deserialize_complete_json(self):
        """Test deserializing complete JSON data."""
        data = {
            "title": "Test",
            "year": 2023,
            "authors_list": ["Smith"],
            "source": "Journal",
            "volume": "10",
            "issue": "2",
            "pages": "123-145",
            "doi": "10.1234/test",
            "pmid": "12345678"
        }
        reference = Reference.from_json(data)
        
        assert reference.title == "Test"
        assert reference.year == 2023
        assert reference.authors == ["Smith"]
        assert reference.journal == "Journal"
        assert reference.volume == "10"
        assert reference.issue == "2"
        assert reference.pages == "123-145"
        assert reference.doi == "10.1234/test"
        assert reference.pmid == "12345678"
    
    def test_deserialize_null_values(self):
        """Test deserializing JSON with null values."""
        data = {"title": None}
        reference = Reference.from_json(data)
        
        assert reference.title is None
    
    def test_deserialize_empty_json(self):
        """Test deserializing an empty JSON."""
        reference = Reference.from_json({})
        
        assert reference.title is None
        assert reference.year is None
        assert reference.authors is None
        assert reference.journal is None
        assert reference.doi is None
        assert reference.pmid is None
    
    def test_deserialize_none_json(self):
        """Test deserializing None instead of JSON."""
        reference = Reference.from_json(None)
        
        assert reference.title is None
        assert reference.year is None
        assert reference.authors is None
        assert reference.journal is None
        assert reference.doi is None
        assert reference.pmid is None
    
    def test_deserialize_invalid_year(self):
        """Test deserializing JSON with invalid year."""
        data = {"year": "invalid"}
        reference = Reference.from_json(data)
        
        assert reference.year is None
    
    def test_deserialize_authors_list_as_string(self):
        """Test deserializing JSON with authors_list as string."""
        data = {"authors_list": "Smith"}
        reference = Reference.from_json(data)
        
        assert reference.authors == ["Smith"]
    
    def test_has_minimal_data_with_title(self):
        """Test has_minimal_data with only title."""
        reference = Reference(title="Test")
        
        assert reference.has_minimal_data(allow_missing_year=True)
        assert not reference.has_minimal_data(allow_missing_year=False)
    
    def test_has_minimal_data_with_title_and_year(self):
        """Test has_minimal_data with title and year."""
        reference = Reference(title="Test", year=2023)
        
        assert reference.has_minimal_data(allow_missing_year=True)
        assert reference.has_minimal_data(allow_missing_year=False)
    
    def test_has_minimal_data_with_doi(self):
        """Test has_minimal_data with only DOI."""
        reference = Reference(doi="10.1234/test")
        
        assert reference.has_minimal_data(allow_missing_year=True)
        assert reference.has_minimal_data(allow_missing_year=False)
    
    def test_has_minimal_data_with_pmid(self):
        """Test has_minimal_data with only PMID."""
        reference = Reference(pmid="12345678")
        
        assert reference.has_minimal_data(allow_missing_year=True)
        assert reference.has_minimal_data(allow_missing_year=False)
    
    def test_has_minimal_data_empty(self):
        """Test has_minimal_data with empty reference."""
        reference = Reference()
        
        assert not reference.has_minimal_data(allow_missing_year=True)
        assert not reference.has_minimal_data(allow_missing_year=False)
    
    def test_to_dict_complete(self):
        """Test to_dict with complete reference."""
        reference = Reference(
            title="Test",
            year=2023,
            authors=["Smith"],
            journal="Journal",
            volume="10",
            issue="2",
            pages="123-145",
            doi="10.1234/test",
            pmid="12345678"
        )
        result = reference.to_dict()
        
        assert result == {
            "title": "Test",
            "year": 2023,
            "authors": ["Smith"],
            "journal": "Journal",
            "volume": "10",
            "issue": "2",
            "pages": "123-145",
            "doi": "10.1234/test",
            "pmid": "12345678"
        }
    
    def test_to_dict_partial(self):
        """Test to_dict with partial reference."""
        reference = Reference(title="Test")
        result = reference.to_dict()
        
        assert result == {"title": "Test"}
    
    def test_to_dict_empty(self):
        """Test to_dict with empty reference."""
        reference = Reference()
        result = reference.to_dict()
        
        assert result == {}