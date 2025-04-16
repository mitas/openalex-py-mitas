# src/domain/models/search_result.py
"""SearchResult model representing results of publication search."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.domain.enums.search_status import SearchStatus
from src.domain.enums.study_type import StudyType


class SearchResult(BaseModel):
    """Result of searching for a publication in OpenAlex."""

    study_id: str
    study_type: StudyType
    status: SearchStatus
    strategy: Optional[str] = None
    openalex_id: Optional[str] = None
    pdf_url: Optional[str] = None
    title: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    open_access: Optional[bool] = None
    citation_count: Optional[int] = None
    search_details: Optional[Dict[str, Any]] = None
    search_attempts: Optional[List[Dict[str, Any]]] = None
    original_reference: Optional[Dict[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        """Convert the SearchResult object to JSON output format."""
        # Use Pydantic's dict method with exclude_none=True
        # Exclude fields not relevant based on status
        exclude_fields = set()
        if self.status != SearchStatus.FOUND:
            exclude_fields.update([
                'strategy', 'openalex_id', 'pdf_url', 'title', 'journal',
                'year', 'doi', 'open_access', 'citation_count', 'search_details'
            ])
        # Always include attempts and original reference for debugging non-found cases
        # if self.status not in [SearchStatus.NOT_FOUND, SearchStatus.REJECTED]:
        #      exclude_fields.update(['search_attempts', 'original_reference'])

        if self.status == SearchStatus.SKIPPED:
             # Keep only minimal fields for skipped
             exclude_fields.update([
                 'strategy', 'openalex_id', 'pdf_url', 'title', 'journal',
                 'year', 'doi', 'open_access', 'citation_count', 'search_details',
                 'search_attempts', 'original_reference'
             ])


        # Convert enums to their values for JSON compatibility
        output_dict = self.dict(exclude_none=True, exclude=exclude_fields)
        output_dict['study_type'] = self.study_type.value
        output_dict['status'] = self.status.value

        return output_dict
