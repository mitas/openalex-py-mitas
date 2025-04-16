# src/domain/models/study.py
"""Study model representing a study in a systematic review."""

from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.domain.enums.study_type import StudyType
from src.domain.models.reference import Reference


class Study(BaseModel):
    """A study in a systematic review."""

    id: str = ""
    type: StudyType
    reference: Reference
    characteristics: Optional[Dict[str, Any]] = None
    exclusion_reason: Optional[str] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any], study_type: StudyType) -> "Study":
        """Create a Study object from JSON data."""
        reference_data = data.get("reference") # Allow None
        reference = Reference.from_json(reference_data)

        # Extract optional fields based on type
        characteristics = data.get("characteristics") if study_type == StudyType.INCLUDED else None
        exclusion_reason = data.get("reason_for_exclusion") if study_type == StudyType.EXCLUDED else None

        return cls(
            id=data.get("study_id", ""),
            type=study_type,
            reference=reference,
            characteristics=characteristics,
            exclusion_reason=exclusion_reason,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Study object to a dictionary."""
        # Use Pydantic's dict method
        output_dict = self.dict(exclude_none=True)
        # Ensure enums are converted to values
        output_dict['type'] = self.type.value
        # Ensure reference is also converted
        output_dict['reference'] = self.reference.to_dict()
        return output_dict
