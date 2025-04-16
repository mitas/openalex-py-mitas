# src/domain/models/reference.py
"""Reference model representing a bibliographic reference."""

import re
from typing import Any, Dict, List, Optional

from loguru import logger
# Używamy tylko podstawowych importów Pydantic v2
from pydantic import BaseModel, Field, field_validator

# Import pomocnika nie jest już potrzebny w tym pliku


class Reference(BaseModel):
    """A bibliographic reference."""

    title: Optional[str] = None
    year: Optional[int] = None
    # Nadal używamy aliasu, aby Pydantic wiedział, skąd brać dane
    authors: Optional[List[str]] = Field(default=None, alias="authors_list")
    journal: Optional[str] = Field(default=None, alias="source")
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None

    class Config:
        allow_population_by_field_name = True # Pozwala na użycie 'authors' i 'journal'
        # W Pydantic v2 konfiguracja może wyglądać inaczej, ale 'alias' w Field działa

    # Walidator dla roku (może pozostać lub użyć nowej składni)
    @field_validator('year', mode='before')
    @classmethod
    def year_must_be_int(cls, v):
        if v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            logger.warning(f"Invalid year format '{v}', setting to None.")
            return None

    # Usunęliśmy walidator dla 'authors', ponieważ logika jest w from_json

    @classmethod
    def from_json(cls, data: Optional[Dict[str, Any]]) -> "Reference":
        """
        Create a Reference object from JSON data, pre-processing authors_list.
        """
        if data is None:
            logger.debug("Reference.from_json called with None data.")
            # Zwracamy pusty obiekt, który przejdzie walidację Pydantic
            try:
                return cls.model_validate({})
            except Exception as e:
                 logger.error(f"Failed to validate empty Reference object: {e}")
                 # This path is unlikely but handle defensively
                 return cls() # Return default empty object


        logger.debug(f"Reference.from_json raw input data before processing authors: {data}")

        # --- Logika parsowania i dzielenia autorów PRZED walidacją Pydantic ---
        # Kopiujemy słownik, aby nie modyfikować oryginału przekazanego do funkcji
        data_copy = data.copy()
        authors_list_value = data_copy.get("authors_list")
        processed_authors_value: Optional[List[str]] = None # Wartość po przetworzeniu

        if isinstance(authors_list_value, list):
            # Jeśli już jest listą, tylko czyścimy elementy
            cleaned_list = [str(author).strip() for author in authors_list_value if str(author).strip()]
            processed_authors_value = cleaned_list if cleaned_list else None
            # <<< --- LOG 1 (dla listy) --- >>>
            logger.debug(f"AUTH_DEBUG: Input was list. Processed to: {processed_authors_value}")
            data_copy["authors_list"] = processed_authors_value # Update copy

        elif isinstance(authors_list_value, str) and authors_list_value.strip():
            # Jeśli jest stringiem, próbujemy podzielić
            v = authors_list_value # Dla czytelności
            # <<< --- LOG 2 (wejście do bloku string) --- >>>
            logger.debug(f"AUTH_DEBUG: Input is string: '{v}'")
            try:
                delimiters = r",\s*|;\s*|\s+and\s+"
                # <<< --- LOG 3 (użyte delimitery) --- >>>
                logger.debug(f"AUTH_DEBUG: Using delimiters: {delimiters}")
                split_authors = re.split(delimiters, v)
                # <<< --- LOG 4 (wynik re.split) --- >>>
                logger.debug(f"AUTH_DEBUG: Result of re.split: {split_authors}")

                # Usuwamy puste stringi po podziale i czyścimy białe znaki
                parsed_authors = [author.strip() for author in split_authors if author and author.strip()]
                # <<< --- LOG 5 (wynik po oczyszczeniu) --- >>>
                logger.debug(f"AUTH_DEBUG: Result after stripping and filtering empty: {parsed_authors}")

                if len(parsed_authors) > 1:
                    # Jeśli udało się podzielić na więcej niż 1 autora
                    # <<< --- LOG 6a (sukces podziału) --- >>>
                    logger.info(f"AUTH_DEBUG: Split successful! Count: {len(parsed_authors)}. Setting processed value to: {parsed_authors}")
                    processed_authors_value = parsed_authors
                elif len(parsed_authors) == 1:
                     # Jeśli split dał 1 element (brak separatorów lub same separatory)
                     processed_authors_value = [parsed_authors[0]] # Traktuj jako jednego autora
                     # <<< --- LOG 6b (wynik z 1 elementem) --- >>>
                     logger.debug(f"AUTH_DEBUG: Input string '{v}' treated as single author: {processed_authors_value}")
                else:
                     # Jeśli split dał pustą listę (np. string zawierał tylko separatory)
                     processed_authors_value = None
                     # <<< --- LOG 6c (wynik pusty) --- >>>
                     logger.debug(f"AUTH_DEBUG: Input string '{v}' resulted in empty list after split.")

            except Exception as split_error:
                 logger.error(f"AUTH_DEBUG: Error during splitting string '{v}': {split_error}")
                 # W razie błędu podziału, ustawiamy na None
                 processed_authors_value = None

            # Zaktualizuj kopię słownika 'data_copy' *przed* walidacją Pydantic
            data_copy["authors_list"] = processed_authors_value # Update copy
        else:
            # Jeśli authors_list_value to np. None, pusty string, lub inny typ
            processed_authors_value = None
            if authors_list_value is not None: # Loguj tylko jeśli nie było None
                 # <<< --- LOG 7 (inny typ lub None) --- >>>
                logger.debug(f"AUTH_DEBUG: Input authors_list was None, empty or unexpected type ({type(authors_list_value)}). Setting to None.")
            data_copy["authors_list"] = processed_authors_value # Update copy

        # <<< --- LOG 8 (dane przed walidacją Pydantic) --- >>>
        logger.debug(f"AUTH_DEBUG: Data prepared for Pydantic validation: {data_copy}")
        # --- Koniec logiki parsowania autorów ---

        # Teraz wywołaj walidację Pydantic na ZMODYFIKOWANYM słowniku 'data_copy'
        try:
            # Użyj model_validate dla Pydantic v2
            instance = cls.model_validate(data_copy)
            # <<< --- LOG 9 (finalny obiekt po walidacji) --- >>>
            # Sprawdźmy, co faktycznie trafiło do obiektu po walidacji
            logger.debug(f"AUTH_DEBUG: Pydantic validation successful. Final authors field in object: {instance.authors}")
            return instance
        except Exception as e:
            logger.error(f"Pydantic validation error for reference data: {data_copy}. Error: {e}", exc_info=True)
            # Zwróć domyślny pusty obiekt w razie błędu walidacji
            # Musimy zwrócić instancję klasy, nawet pustą
            try:
                return cls.model_validate({})
            except Exception as inner_e:
                 logger.critical(f"Failed even to validate empty Reference object after primary error: {inner_e}")
                 return cls() # Fallback to default unvalidated object


    def to_dict(self) -> Dict[str, Any]:
        """Convert the Reference object to a dictionary."""
        # Użyj model_dump dla Pydantic v2
        output_dict = self.model_dump(by_alias=True, exclude_none=True)
        # Logika zapewniająca poprawne aliasy w wyjściowym słowniku (może być nadmiarowa)
        if "authors_list" in output_dict and "authors" not in output_dict:
            output_dict["authors"] = output_dict.pop("authors_list")
        if "source" in output_dict and "journal" not in output_dict:
            output_dict["journal"] = output_dict.pop("source")
        return output_dict


    def has_minimal_data(self, allow_missing_year: bool = False) -> bool:
        """Check if the reference has the minimal data needed for searching."""
        # Check for DOI or PMID first
        if self.doi and self.doi.strip():
            return True
        if self.pmid and self.pmid.strip():
            return True

        # Otherwise, require title (and potentially year)
        has_title = self.title is not None and len(self.title.strip()) > 3 # Min title length

        if not has_title:
            return False

        # Check year requirement
        if not allow_missing_year and self.year is None:
            return False

        return True
