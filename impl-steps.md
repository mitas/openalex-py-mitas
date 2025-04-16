Przepraszam za niedociągnięcia w poprzedniej odpowiedzi. Poniżej przedstawiam kompletną dokumentację techniczną systemu dopasowywania publikacji OpenAlex, zgodną z wszystkimi wymaganiami. Dokument opisuje szczegółowo każdy plik projektu, implementację logiki wszystkich strategii wyszukiwania (DOI, PMID, TITLE_AUTHORS_YEAR, TITLE_AUTHORS, TITLE_YEAR, TITLE_JOURNAL, TITLE_ONLY), zależności, testy w duchu TDD oraz pełny przepływ danych. Zamiast kodu, wszystkie scenariusze są opisane słownie, z uwzględnieniem każdego możliwego przypadku (sukcesy, błędy, przypadki brzegowe). Dokumentacja bazuje na zaproponowanej strukturze projektu, stosuje zasady SOLID, DRY, SRP i Clean Code, oraz unika duplikacji logiki poprzez wskazywanie wspólnych elementów. Na końcu znajduje się pełny przepływ danych, uwzględniający wszystkie pliki projektu.

---

# Kompleksowa dokumentacja techniczna systemu dopasowywania publikacji OpenAlex

Niniejszy dokument w języku polskim przedstawia pełną dokumentację techniczną systemu automatycznego dopasowywania publikacji w bazie OpenAlex na podstawie referencji bibliograficznych z badań w przeglądach systematycznych (format RevMan). System został zaprojektowany z myślą o modularności, testowalności i niezawodności, zgodnie z zasadami TDD (Test-Driven Development), SOLID, DRY (Don’t Repeat Yourself), SRP (Single Responsibility Principle) oraz Clean Code. Dokument opisuje krok po kroku implementację każdego pliku, logikę wszystkich strategii wyszukiwania, zależności, przypadki testowe oraz przepływ danych od uruchomienia aplikacji do zapisu wyników.

---

## Struktura projektu

Projekt został zaprojektowany z myślą o czytelności i łatwości utrzymania, z wyraźnym podziałem na warstwy odpowiedzialności. Struktura projektu jest następująca:

```
src/
├── domain/
│   ├── enums/
│   │   ├── search_strategy_type.py  # Wyliczenie typów strategii wyszukiwania
│   │   ├── study_type.py            # Wyliczenie typów badań (included, excluded)
│   │   └── search_status.py         # Wyliczenie statusów wyszukiwania (found, not_found, rejected, skipped)
│   ├── interfaces/
│   │   ├── search_strategy.py       # Interfejs dla strategii wyszukiwania
│   │   └── publication_repository.py # Interfejs dla repozytorium publikacji
│   ├── models/
│   │   ├── reference.py             # Model referencji bibliograficznej
│   │   ├── study.py                 # Model badania
│   │   ├── search_result.py         # Model wyniku wyszukiwania
│   │   └── config.py                # Model konfiguracji systemu
│   └── strategies/
│       ├── base_strategy.py         # Bazowa strategia wyszukiwania (wspólna logika)
│       ├── doi_strategy.py          # Strategia wyszukiwania po DOI
│       ├── pmid_strategy.py         # Strategia wyszukiwania po PMID
│       ├── title_authors_year_strategy.py # Strategia wyszukiwania po tytule, autorach i roku
│       ├── title_authors_strategy.py     # Strategia wyszukiwania po tytule i autorach
│       ├── title_year_strategy.py        # Strategia wyszukiwania po tytule i roku
│       ├── title_journal_strategy.py     # Strategia wyszukiwania po tytule i czasopiśmie
│       └── title_only_strategy.py        # Strategia wyszukiwania tylko po tytule
├── application/
│   └── services/
│       └── matching_service.py       # Usługa koordynująca proces dopasowywania
├── infrastructure/
│   └── repositories/
│       └── openalex_repository.py    # Repozytorium do komunikacji z API OpenAlex
├── utils/
│   └── dict_helpers.py               # Narzędzia pomocnicze do operacji na słownikach
└── main.py                           # Punkt wejścia aplikacji
```

**Uwagi dotyczące struktury**:
- **Minimalizacja zbędnych plików**: Każdy plik ma unikalną rolę i jest wykorzystywany w przepływie danych. Nie ma nadmiarowych elementów.
- **Wspólna logika**: Plik `base_strategy.py` zawiera współdzieloną logikę dla strategii wyszukiwania (np. normalizacja danych, logowanie), aby uniknąć duplikacji kodu (zasada DRY).
- **SRP**: Każdy plik odpowiada za jedną odpowiedzialność (np. model, strategia, repozytorium).

---

## Wejściowy i wyjściowy format JSON

### Wejściowy JSON (format RevMan)

Pliki wejściowe JSON (przykładowy plik: `./data/antibiotics-for-sore-throat.json` mają następującą strukturę:

```json
{
  "studies": {
    "included": [
      {
        "study_id": "STD-Example-2023",
        "reference": {
          "title": "Example study title",
          "year": 2023,
          "authors_list": ["Smith, John", "Doe, Jane"],
          "source": "Journal of Examples",
          "volume": "10",
          "issue": "2",
          "pages": "123-145",
          "doi": "10.1234/example.2023",
          "pmid": "12345678"
        },
        "characteristics": {
          "key1": "value1",
          "key2": "value2"
        }
      }
    ],
    "excluded": [
      {
        "study_id": "STD-ExcludedExample-2023",
        "reference": {
          "title": "Excluded study title",
          "year": 2022,
          "authors_list": ["Brown, Robert"],
          "source": "Journal of Non-Examples",
          "volume": "5",
          "issue": "1",
          "pages": "10-20",
          "doi": "10.1234/non-example.2022",
          "pmid": null
        },
        "reason_for_exclusion": "Did not meet inclusion criteria"
      }
    ]
  }
}
```

**Opis pól**:
- `studies`: Główny obiekt zawierający dwie listy: `included` (badania włączone) i `excluded` (badania wykluczone).
- `included`: Lista badań z polami:
- `study_id`: Unikalny identyfikator (string).
- `reference`: Obiekt referencji z polami: `title`, `year`, `authors_list`, `source`, `volume`, `issue`, `pages`, `doi`, `pmid`.
- `characteristics`: Słownik z dodatkowymi metadanymi badania.
- `excluded`: Lista badań z polami:
- `study_id`, `reference` (jak w `included`).
- `reason_for_exclusion`: Powód wykluczenia (string).
- Wszystkie pola w `reference` mogą być `null`, co wymaga odpowiedniej obsługi w systemie.

**Scenariusze wejściowe**:
- Pełne dane: Wszystkie pola wypełnione, w tym `doi` i `pmid`.
- Częściowe dane: Brak niektórych pól (np. tylko `title` i `year`).
- Niepoprawne dane: Błędne typy (np. `year` jako string) lub brak `study_id`.
- Pusty JSON: Brak `studies` lub pustych list `included`/`excluded`.

### Wyjściowy JSON

Pliki wyjściowe JSON mają następującą strukturę:

```json
{
  "included": [{
    "study_id": "STD-Example-2023",
    "study_type": "included",
    "status": "found",
    "strategy": "doi",
    "openalex_id": "https://openalex.org/W1234567890",
    "pdf_url": "https://example.com/paper.pdf",
    "title": "Example study title",
    "journal": "Journal of Examples",
    "year": 2023,
    "doi": "https://doi.org/10.1234/example.2023",
    "open_access": true,
    "citation_count": 5,
    "search_details": {
      "query_type": "doi filter",
      "search_term": "10.1234/example.2023",
      "strategy": "doi"
    }
  }],
  "excluded": [{
    "study_id": "STD-ExcludedExample-2023",
    "study_type": "excluded",
    "status": "not_found",
    "search_attempts": [{
      "strategy": "title_only",
      "query_type": "title.search only",
      "search_term": "excluded study title"
    }],
    "original_reference": {
      "title": "Excluded study title",
      "year": 2022,
      "journal": "Journal of Non-Examples"
    }
  }],
  "summary": {
    "total": 2,
    "found": 1,
    "rejected": 0,
    "not_found": 1,
    "skipped": 0,
    "with_pdf_url": 1,
    "open_access": 1,
    "with_doi": 1,
    "found_percent": 50.0,
    "rejected_percent": 0.0,
    "not_found_percent": 50.0,
    "skipped_percent": 0.0
  }
}
```

**Opis pól**:
- `included` i `excluded`: Listy wyników dla badań włączonych i wykluczonych.
- Pola w rekordach:
- `study_id`: Unikalny identyfikator badania (string).
- `study_type`: Typ badania (`"included"` lub `"excluded"`).
- `status`: Status wyszukiwania (`"found"`, `"not_found"`, `"rejected"`, `"skipped"`).
- `strategy`: Nazwa strategii, która znalazła wynik (lub ostatnia próba przy `"not_found"`).
- `openalex_id`: Identyfikator publikacji w OpenAlex (np. `"https://openalex.org/W1234567890"`).
- `pdf_url`: URL do pliku PDF (jeśli dostępny).
- `title`, `journal`, `year`, `doi`: Dane publikacji z OpenAlex.
- `open_access`: Czy publikacja jest open access (`true`/`false`).
- `citation_count`: Liczba cytowań (integer).
- `search_details`: Szczegóły udanego wyszukiwania (tylko dla `"found"`):
- `query_type`: Typ zapytania (np. `"doi filter"`).
- `search_term`: Wartość zapytania (np. `"10.1234/example.2023"`).
- `strategy`: Nazwa strategii.
- `search_attempts`: Lista prób wyszukiwania dla `"not_found"` lub `"rejected"`:
- `strategy`: Nazwa strategii.
- `query_type`: Typ zapytania.
- `search_term`: Wartość zapytania.
- `original_reference`: Oryginalne dane referencji w przypadku niepowodzenia (`title`, `year`, `journal`).
- `summary`: Statystyki wyników:
- `total`: Liczba wszystkich badań.
- `found`, `rejected`, `not_found`, `skipped`: Liczba badań w każdym statusie.
- `with_pdf_url`, `open_access`, `with_doi`: Liczba publikacji z danymi atrybutami.
- `found_percent`, `rejected_percent`, `not_found_percent`, `skipped_percent`: Procentowy udział każdego statusu.

**Scenariusze wyjściowe**:
- Pełny sukces: Wszystkie badania mają status `"found"` z pełnymi danymi publikacji.
- Częściowy sukces: Niektóre badania `"not_found"` z zapisanymi próbami.
- Odrzucenie: Wyniki odrzucone z powodu niskiego podobieństwa (status `"rejected"`).
- Pominięcie: Badania bez minimalnych danych (status `"skipped"`).
- Brak danych: Pusty wynik z zerowymi statystykami.

---

## Używane pakiety PIP i sugerowane pakiety

### Używane pakiety

- **`aiohttp`**: Asynchroniczne zapytania HTTP do API OpenAlex.
- **`pyalex`**: Biblioteka do komunikacji z API OpenAlex.
- **`orjson`**: Szybka serializacja i deserializacja JSON.
- **`pydantic`**: Walidacja i parsowanie modeli danych (`Reference`, `Study`, `Config`).
- **`loguru`**: Zaawansowane logowanie z kontekstem.
- **`cachetools`**: Cache’owanie wyników zapytań API.

### Sugerowane pakiety

- **`aiofiles`**: Asynchroniczny odczyt/zapis plików JSON (optymalizacja I/O).
- **`tenacity`**: Automatyczne ponawianie zapytań przy błędach (np. limitach API).
- **`rapidfuzz`**: Obliczanie podobieństwa tekstu dla strategii TITLE_*.
- **`python-dotenv`**: Zarządzanie zmiennymi środowiskowymi (np. `OPENALEX_EMAIL`).
- **`pytest` i `pytest-asyncio`**: Testy jednostkowe i asynchroniczne.

**Uwaga dotycząca DRY**: Do serializacji/deserializacji używamy `orjson` w całym systemie (np. w `main.py`, `study.py`), aby uniknąć duplikacji logiki.

---

## Implementacja kodu – logiczne kroki

Implementacja systemu jest podzielona na logiczne kroki, z których każdy można przetestować niezależnie. Każdy plik zawiera szczegółowy opis logiki, zależności i przypadków testowych w duchu TDD.

### Krok 1: Utworzenie architektury projektu

**Opis**: Tworzymy strukturę projektu zgodnie z podaną powyżej hierarchią plików. Każdy pakiet (`domain`, `application`, `infrastructure`, `utils`) i plik ma unikalną rolę, zapewniając separację odpowiedzialności (SRP).

**Testy**:
- **Test struktury**: Manualna weryfikacja istnienia wszystkich plików i folderów.
- **Oczekiwany wynik**: Wszystkie pliki utworzone bez błędów składniowych.

**Uwagi**:
- Architektura jest statyczna, więc nie wymaga automatycznych testów jednostkowych.
- Ważne jest zapewnienie, że każdy plik importuje tylko niezbędne zależności, aby uniknąć cyklicznych importów.

---

### Krok 2: Implementacja modeli domenowych

Modele definiują strukturę danych i mapują wejściowy JSON na obiekty Pythona. Wszystkie modele używają `pydantic` do walidacji i deserializacji.

### Plik: `domain/models/reference.py`

**Opis**: Model `Reference` reprezentuje referencję bibliograficzną, mapując dane z pola `reference` w wejściowym JSON.

**Logika implementacji**:
- **Pola**:
- `title`: Opcjonalny string (mapuje `"title"` z JSON).
- `year`: Opcjonalny integer (mapuje `"year"`).
- `authors`: Opcjonalna lista stringów (mapuje `"authors_list"`).
- `journal`: Opcjonalny string (mapuje `"source"`).
- `volume`, `issue`, `pages`: Opcjonalne stringi (mapują odpowiednie pola).
- `doi`, `pmid`: Opcjonalne stringi (mapują `"doi"`, `"pmid"`).
- **Metody**:
- `from_json(data)`: Deserializuje JSON na obiekt `Reference`. Jeśli pole jest `null` lub nie istnieje, ustawia `None`.
- `to_dict()`: Konwertuje obiekt na słownik, pomijając pola `None` (używa `utils/dict_helpers.add_optional_field` dla DRY).
- `has_minimal_data(allow_missing_year)`: Sprawdza, czy referencja ma wystarczające dane do wyszukiwania (tytuł lub DOI/PMID, opcjonalnie rok).
- **Scenariusze**:
- **Sukces**: Pełny JSON z wszystkimi polami → pełny obiekt `Reference`.
- **Częściowe dane**: Brak pól (np. tylko `title`) → obiekt z `None` w brakujących polach.
- **Błąd**: Niepoprawny typ `year` (np. string „invalid”) → ustawia `None`.
- **Przypadek brzegowy**: Pusty JSON → wszystkie pola `None`, `has_minimal_data` zwraca `False`.
- **Przypadek brzegowy**: `authors_list` jako string → konwertuje na jednoelementową listę.

**Zależności**:
- **`pydantic`**: Walidacja i deserializacja.
- **`typing`**: Anotacje typów (`Optional`, `List`).
- **`src/utils/dict_helpers.py`**: Funkcja `add_optional_field` do serializacji.

**Testy (TDD)**:
- **Test deserializacji**:
- Dane wejściowe: `{"title": "Test", "year": 2023, "authors_list": ["Smith"], "source": "Journal", "doi": "10.1234/test", "pmid": "12345678"}`.
- Oczekiwany wynik: Obiekt `Reference` z poprawnymi wartościami.
- Test: `{"title": null}` → `Reference(title=None)`.
- **Test minimalnych danych**:
- Test: `Reference(title="Test")`, `allow_missing_year=True` → `True`.
- Test: `Reference()` → `False`.
- **Test błędnych danych**:
- Test: `{"year": "invalid"}` → `Reference(year=None)`.
- **Test serializacji**:
- Test: `Reference(title="Test").to_dict()` → `{"title": "Test"}`.
- Test: `Reference().to_dict()` → `{}`.

---

### Plik: `domain/models/study.py`

**Opis**: Model `Study` reprezentuje badanie w przeglądzie systematycznym, mapując dane z `included` lub `excluded` w JSON.

**Logika implementacji**:
- **Pola**:
- `id`: String (mapuje `"study_id"`, domyślnie pusty).
- `type`: Enum `StudyType` (ustalany na podstawie klucza JSON: `included`/`excluded`).
- `reference`: Obiekt `Reference` (mapuje `"reference"`).
- `characteristics`: Opcjonalny słownik (mapuje `"characteristics"` dla `included`).
- `exclusion_reason`: Opcjonalny string (mapuje `"reason_for_exclusion"` dla `excluded`).
- **Metody**:
- `from_json(data, study_type)`: Deserializuje JSON, tworząc `Reference` z podanego `"reference"`.
- `to_dict()`: Konwertuje obiekt na słownik, używając `utils/dict_helpers.add_optional_field`.
- **Scenariusze**:
- **Sukces**: Pełny JSON z `study_id`, `reference`, `characteristics` → pełny obiekt `Study`.
- **Częściowe dane**: Brak `characteristics` → `None`.
- **Błąd**: Brak `study_id` → pusty string.
- **Przypadek brzegowy**: Brak `reference` → pusty obiekt `Reference`.
- **Przypadek brzegowy**: `exclusion_reason` dla `included` → ignorowany.

**Zależności**:
- **`pydantic`**: Walidacja.
- **`domain/enums/study_type.py`**: Enum `StudyType`.
- **`domain/models/reference.py`**: Model `Reference`.
- **`src/utils/dict_helpers.py`**: Serializacja.

**Testy (TDD)**:
- **Test deserializacji**:
- Dane: `{"study_id": "STD-1", "reference": {"title": "Test"}, "characteristics": {"key": "value"}}`, `study_type=StudyType.INCLUDED`.
- Oczekiwany wynik: Poprawny obiekt `Study`.
- Test: `{"study_id": ""}` → `Study(id="")`.
- **Test serializacji**:
- Test: `Study(id="STD-1", type=StudyType.INCLUDED, reference=Reference()).to_dict()` → `{"id": "STD-1", "type": "included", "reference": {}}`.

---

### Plik: `domain/models/search_result.py`

**Opis**: Model `SearchResult` przechowuje wyniki wyszukiwania dla badania, mapując na wyjściowy JSON.

**Logika implementacji**:
- **Pola**:
- `study_id`: String (z `Study.id`).
- `study_type`: Enum `StudyType` (z `Study.type`).
- `status`: Enum `SearchStatus` (`"found"`, `"not_found"`, `"rejected"`, `"skipped"`).
- `strategy`: Opcjonalny string (nazwa strategii dla `"found"`).
- `openalex_id`, `pdf_url`, `title`, `journal`, `year`, `doi`, `open_access`, `citation_count`: Opcjonalne dane publikacji z OpenAlex (dla `"found"`).
- `search_details`: Opcjonalny słownik z `query_type`, `search_term`, `strategy` (dla `"found"`).
- `search_attempts`: Lista słowników z `strategy`, `query_type`, `search_term`, `error` (dla `"not_found"`/ `"rejected"`).
- `original_reference`: Opcjonalny słownik z `title`, `year`, `journal` (dla `"not_found"`/ `"rejected"`).
- **Metody**:
- `to_json()`: Konwertuje obiekt na wyjściowy JSON, używając `utils/dict_helpers.add_optional_field`.
- **Scenariusze**:
- **Sukces (`found`)**: Znaleziono publikację → wypełnia wszystkie pola publikacji i `search_details`.
- **Niepowodzenie (`not_found`)**: Brak wyników → zapisuje `search_attempts` i `original_reference`.
- **Odrzucenie (`rejected`)**: Niski próg podobieństwa → zapisuje powód w `search_attempts.error`.
- **Pominięcie (`skipped`)**: Brak danych → minimalny wynik z pustymi polami.
- **Przypadek brzegowy**: Częściowe dane publikacji → tylko dostępne pola w `to_json()`.

**Zależności**:
- **`pydantic`**: Walidacja.
- **`domain/enums/study_type.py`**: `StudyType`.
- **`domain/enums/search_status.py`**: `SearchStatus`.
- **`src/utils/dict_helpers.py`**: Serializacja.

**Testy (TDD)**:
- **Test sukcesu**:
- Dane: `SearchResult(study_id="STD-1", study_type=StudyType.INCLUDED, status=SearchStatus.FOUND, strategy="doi", openalex_id="W123")`.
- Oczekiwany wynik: JSON z `"status": "found"`, `"openalex_id": "W123"`.
- **Test niepowodzenia**:
- Dane: `SearchResult(..., status=SearchStatus.NOT_FOUND, search_attempts=[{"strategy": "title_only", "query_type": "title.search", "search_term": "Test"}])`.
- Oczekiwany wynik: JSON z `"status": "not_found"`, `"search_attempts"`.
- **Test pominięcia**:
- Dane: `SearchResult(..., status=SearchStatus.SKIPPED)`.
- Oczekiwany wynik: JSON z `"status": "skipped"`.

---

### Plik: `domain/models/config.py`

**Opis**: Model `Config` przechowuje ustawienia systemu, w tym progi podobieństwa i konfigurację API OpenAlex.

**Logika implementacji**:
- **Pola**:
- `openalex_email`: Opcjonalny string (e-mail dla API OpenAlex, z zmiennej środowiskowej).
- `title_similarity_threshold`: Float (domyślnie 0.85, dla strategii TITLE_*).
- `author_similarity_threshold`: Float (domyślnie 0.9, dla strategii z autorami).
- `disable_strategies`: Lista stringów (nazwy strategii do wyłączenia, np. `["doi"]`).
- `max_retries`: Integer (domyślnie 3, dla retry API).
- `retry_backoff_factor`: Float (domyślnie 0.5, dla retry API).
- `concurrency`: Integer (domyślnie 20, liczba równoległych zapytań).
- **Metody**:
- `from_env()`: Ładuje konfigurację z zmiennych środowiskowych, z domyślnymi wartościami.
- `validate()`: Sprawdza poprawność wartości (np. `title_similarity_threshold` w zakresie [0, 1]).
- **Scenariusze**:
- **Sukces**: Wszystkie zmienne środowiskowe ustawione → pełna konfiguracja.
- **Domyślne wartości**: Brak zmiennych → domyślne wartości.
- **Błąd**: Niepoprawny próg (np. 1.5) → poprawia na domyślny.
- **Przypadek brzegowy**: Pusta lista `disable_strategies` → wszystkie strategie włączone.

**Zależności**:
- **`pydantic`**: Walidacja.
- **`os`**: Odczyt zmiennych środowiskowych.

**Testy (TDD)**:
- **Test ładowania**:
- Zmienna: `OPENALEX_EMAIL="test@example.com"`.
- Oczekiwany wynik: `Config(openalex_email="test@example.com")`.
- **Test domyślnych wartości**:
- Brak zmiennych → `Config(title_similarity_threshold=0.85)`.
- **Test walidacji**:
- Dane: `title_similarity_threshold=-0.1` → poprawia na 0.85.

---

### Krok 3: Implementacja wyliczeń

Wyliczenia definiują stałe wartości używane w systemie, zapewniając typowanie i spójność.

### Plik: `domain/enums/search_strategy_type.py`

**Opis**: Wyliczenie strategii wyszukiwania z priorytetami.

**Logika implementacji**:
- **Wartości**:
- `DOI`: Priorytet 1.
- `PMID`: Priorytet 2.
- `TITLE_AUTHORS_YEAR`: Priorytet 3.
- `TITLE_AUTHORS`: Priorytet 4.
- `TITLE_YEAR`: Priorytet 5.
- `TITLE_JOURNAL`: Priorytet 6.
- `TITLE_ONLY`: Priorytet 7.
- **Metody**:
- `priority`: Zwraca wartość priorytetu (integer).
- `from_string(value)`: Konwertuje string (np. `"doi"`) na wartość wyliczenia, ignorując wielkość liter.
- **Scenariusze**:
- **Sukces**: Poprawny string (np. `"doi"`) → `SearchStrategyType.DOI`.
- **Błąd**: Niepoprawny string (np. `"invalid"`) → rzuca `ValueError`.
- **Przypadek brzegowy**: Pusty string → rzuca `ValueError`.

**Zależności**:
- **`enum`**: Standardowa biblioteka Pythona.

**Testy (TDD)**:
- **Test priorytetów**:
- Test: `SearchStrategyType.DOI.priority` → 1.
- Test: `SearchStrategyType.TITLE_ONLY.priority` → 7.
- **Test konwersji**:
- Test: `SearchStrategyType.from_string("doi")` → `SearchStrategyType.DOI`.
- Test: `SearchStrategyType.from_string("invalid")` → `ValueError`.

---

### Plik: `domain/enums/study_type.py`

**Opis**: Wyliczenie typów badań.

**Logika implementacji**:
- **Wartości**:
- `INCLUDED`: `"included"`.
- `EXCLUDED`: `"excluded"`.
- **Metody**:
- `from_string(value)`: Konwertuje string na wartość wyliczenia.
- **Scenariusze**:
- **Sukces**: `"included"` → `StudyType.INCLUDED`.
- **Błąd**: `"invalid"` → `ValueError`.
- **Przypadek brzegowy**: Pusty string → `ValueError`.

**Zależności**:
- **`enum`**

**Testy (TDD)**:
- **Test konwersji**:
- Test: `StudyType.from_string("excluded")` → `StudyType.EXCLUDED`.
- Test: `StudyType.from_string("invalid")` → `ValueError`.

---

### Plik: `domain/enums/search_status.py`

**Opis**: Wyliczenie statusów wyszukiwania.

**Logika implementacji**:
- **Wartości**:
- `FOUND`: `"found"`.
- `NOT_FOUND`: `"not_found"`.
- `REJECTED`: `"rejected"`.
- `SKIPPED`: `"skipped"`.
- **Metody**:
- `from_string(value)`: Konwertuje string na wartość wyliczenia.
- **Scenariusze**: Jak w `study_type.py`.

**Zależności**:
- **`enum`**

**Testy (TDD)**:
- **Test konwersji**:
- Test: `SearchStatus.from_string("found")` → `SearchStatus.FOUND`.
- Test: `SearchStatus.from_string("invalid")` → `ValueError`.

---

### Krok 4: Implementacja interfejsów

Interfejsy definiują kontrakty dla strategii i repozytoriów, zapewniając spójność implementacji.

### Plik: `domain/interfaces/search_strategy.py`

**Opis**: Interfejs dla strategii wyszukiwania.

**Logika implementacji**:
- **Metody**:
- `name`: Właściwość zwracająca nazwę strategii (string).
- `priority`: Właściwość zwracająca priorytet (integer).
- `supported(reference)`: Sprawdza, czy strategia może być użyta dla danej referencji (zwraca `bool`).
- `execute(reference)`: Wykonuje wyszukiwanie, zwracając listę wyników i metadane (krotka `[List[Dict], Dict]`).
- **Scenariusze**:
- **Sukces**: Implementacja dostarcza wszystkie metody.
- **Błąd**: Brak implementacji metody → rzuca wyjątek przy tworzeniu instancji.
- **Przypadek brzegowy**: Pusta referencja → `supported` zwraca `False`.

**Zależności**:
- **`abc`**: Klasy abstrakcyjne.
- **`typing`**: Anotacje typów.
- **`domain/models/reference.py`**: Model `Reference`.

**Testy (TDD)**:
- **Test abstrakcyjności**:
- Test: Próba stworzenia instancji bez implementacji → `TypeError`.
- Test: Implementacja z wszystkimi metodami → sukces.

---

### Plik: `domain/interfaces/publication_repository.py`

**Opis**: Interfejs dla repozytorium publikacji OpenAlex.

**Logika implementacji**:
- **Metody**:
- `get_by_doi(doi)`: Zwraca pojedynczą publikację dla DOI lub `None`.
- `get_by_pmid(pmid)`: Zwraca pojedynczą publikację dla PMID lub `None`.
- `search_by_title_authors_year(title, authors, year)`: Zwraca listę publikacji dla tytułu, autorów i roku.
- `search_by_title_authors(title, authors)`: Jak powyżej, bez roku.
- `search_by_title_year(title, year)`: Jak powyżej, bez autorów.
- `search_by_title_journal(title, journal)`: Zwraca listę publikacji dla tytułu i czasopisma.
- `search_by_title(title)`: Zwraca listę publikacji dla tytułu.
- **Scenariusze**:
- **Sukces**: Znaleziono wyniki → zwraca listę lub pojedynczy obiekt.
- **Błąd**: Brak wyników lub błąd API → `None` lub pusta lista.
- **Przypadek brzegowy**: Puste zapytanie → pusta lista.

**Zależności**:
- **`abc`**
- **`typing`**

**Testy (TDD)**:
- **Test abstrakcyjności**:
- Test: Jak w `search_strategy.py`.

---

### Krok 5: Implementacja strategii wyszukiwania

Strategie wyszukiwania definiują logikę znajdowania publikacji w OpenAlex. Wszystkie strategie dziedziczą z `BaseStrategy`, która zapewnia wspólną logikę (np. normalizacja tekstu, logowanie), zgodnie z zasadą DRY. Strategie oparte na tytule (`TITLE_AUTHORS_YEAR`, `TITLE_AUTHORS`, `TITLE_YEAR`, `TITLE_JOURNAL`, `TITLE_ONLY`) wykorzystują bibliotekę `rapidfuzz` do precyzyjnego obliczania podobieństwa tekstu między danymi referencji a wynikami z OpenAlex.

### Plik: `domain/strategies/base_strategy.py`

**Opis**: Klasa bazowa dla strategii wyszukiwania, współdzieląca wspólną logikę.

**Logika implementacji**:

- **Metody**:
    - `normalize_text(text)`: Konwertuje tekst na małe litery, usuwa znaki specjalne (poza spacjami), zachowuje spacje, aby zapewnić spójność w porównywaniu tytułów, autorów i czasopism.
    - `log_attempt(reference, result_count, error)`: Loguje próbę wyszukiwania, zapisując nazwę strategii, tytuł referencji (lub „Brak tytułu” dla pustego), liczbę zwróconych wyników oraz ewentualny błąd (lub „Brak błędu”).
    - `validate_reference(reference)`: Abstrakcyjna metoda, którą każda strategia potomna nadpisuje, aby zweryfikować minimalne wymagania dla referencji (np. obecność DOI, tytułu).
- **Scenariusze**:
    - **Sukces**: Poprawna normalizacja tekstu, np. „Test Title!” → „test title”.
    - **Błąd**: Błąd logowania (np. brak uprawnień do loggera) → ignoruje błąd i kontynuuje działanie.
    - **Przypadek brzegowy**: Pusty tekst w `normalize_text` → zwraca pusty string.
    - **Przypadek brzegowy**: Referencja bez tytułu w `log_attempt` → loguje „Brak tytułu”.

**Zależności**:

- **`loguru`**: Biblioteka do logowania prób wyszukiwania.
- **`domain/interfaces/search_strategy.py`**: Interfejs `SearchStrategy`, określający kontrakt dla strategii.
- **`domain/models/reference.py`**: Model `Reference`, używany w metodach walidacji i logowania.

**Testy (TDD)**:

- **Test normalizacji**:
    - Dane: `normalize_text("Test Title!")` → oczekiwany wynik: `"test title"`.
    - Dane: `normalize_text("")` → oczekiwany wynik: `""`.
    - Dane: `normalize_text("Test@#$%^Title")` → oczekiwany wynik: `"test title"`.
- **Test logowania**:
    - Dane: `log_attempt(Reference(title="Test Study"), result_count=1, error=None)` → oczekiwany wynik: Log zawiera „Strategy: [nazwa], Reference: Test Study, Results: 1, Error: Brak błędu”.
    - Dane: `log_attempt(Reference(title=None), result_count=0, error="API Timeout")` → oczekiwany wynik: Log zawiera „Reference: Brak tytułu, Error: API Timeout”.
- **Test abstrakcyjności**:
    - Dane: Próba wywołania `validate_reference` na `BaseStrategy` → oczekiwany wynik: `NotImplementedError`.

---

### Plik: `domain/strategies/doi_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie identyfikatora DOI.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"doi"`, unikalnie identyfikując strategię w systemie.
    - `priority`: Zwraca 1, określając najwyższy priorytet wśród strategii.
    - `supported(reference)`: Sprawdza, czy pole `reference.doi` istnieje i nie jest puste (np. nie jest `None` ani `""`).
    - `validate_reference(reference)`: Weryfikuje format DOI przy użyciu wyrażenia regularnego `^10\\.\\d{4,}/[-._;()/:\\w]+$`. Jeśli DOI nie spełnia wzorca (np. „invalid” lub „10/abc”), rzuca wyjątek `ValueError` z komunikatem „Niepoprawny format DOI”.
    - `execute(reference)`:
        - Wywołuje `normalize_text` z `BaseStrategy` na polu `reference.doi`, aby usunąć niepotrzebne znaki (np. spacje).
        - Wysyła zapytanie do repozytorium publikacji za pomocą `publication_repository.get_by_doi(normalized_doi)`.
        - Jeśli repozytorium zwraca wynik (słownik z danymi publikacji, np. `{id: "W123", title: "Example"}`), umieszcza go w jednoelementowej liście `[result]` i tworzy metadane `{strategy: "doi", query_type: "doi filter", search_term: normalized_doi}`.
        - Jeśli wynik jest pusty (`None`), zwraca pustą listę `[]` i metadane z błędem `{..., error: "No results found"}`.
        - Jeśli repozytorium rzuca wyjątek (np. błąd API, timeout), zwraca pustą listę i metadane z błędem `{..., error: "API error: [szczegóły]"}`.
        - Loguje próbę wyszukiwania za pomocą `log_attempt`, zapisując szczegóły zapytania.
- **Scenariusze**:
    - **Sukces**: Referencja ma DOI „10.1234/test.2023” → repozytorium zwraca publikację `{id: "W123"}` → zwraca `[publication_data]` i metadane `{strategy: "doi", query_type: "doi filter", search_term: "10.1234/test.2023"}`.
    - **Błąd – niepoprawny DOI**: Referencja ma DOI „invalid” → `validate_reference` rzuca `ValueError`, `supported` zwraca `False`.
    - **Błąd – brak wyników**: Poprawny DOI, ale brak publikacji w OpenAlex → zwraca `[]`, metadane z błędem „No results found”.
    - **Błąd API**: Zapytanie kończy się błędem (np. HTTP 429) → zwraca `[]`, metadane z błędem „API error: Too many requests”.
    - **Przypadek brzegowy – wiele wyników**: DOI zwraca więcej niż jedną publikację (rzadkie, ponieważ DOI jest unikalny) → wybiera pierwszą, loguje ostrzeżenie „Wiele wyników dla DOI”.
    - **Przypadek brzegowy – pusty DOI**: `reference.doi` jest `None` lub `""` → `supported` zwraca `False`.
    - **Przypadek brzegowy – DOI z białymi znakami**: DOI „ 10.1234 / test ” → normalizuje do „10.1234/test” i przetwarza poprawnie.

**Zależności**:

- **`domain/strategies/base_strategy.py`**: Klasa bazowa dostarczająca `normalize_text` i `log_attempt`.
- **`domain/models/reference.py`**: Model `Reference` dla danych wejściowych.
- **`domain/interfaces/publication_repository.py`**: Interfejs repozytorium dla metody `get_by_doi`.

**Testy (TDD)**:

- **Test metody supported**:
    - Dane: `Reference(doi="10.1234/test")` → oczekiwany wynik: `True`.
    - Dane: `Reference(doi=None)` → oczekiwany wynik: `False`.
    - Dane: `Reference(doi="")` → oczekiwany wynik: `False`.
- **Test walidacji**:
    - Dane: `Reference(doi="10.1234/test.2023")` → `validate_reference` przechodzi bez wyjątku.
    - Dane: `Reference(doi="invalid")` → `validate_reference` rzuca `ValueError` z „Niepoprawny format DOI”.
    - Dane: `Reference(doi="10/abc")` → `ValueError`.
- **Test wykonania**:
    - Dane: `Reference(doi="10.1234/test")`, mock repozytorium zwraca `{id: "W123", title: "Example"}` → oczekiwany wynik: `[dict(id="W123", title="Example")], {strategy: "doi", query_type: "doi filter", search_term: "10.1234/test"}`.
    - Dane: Mock zwraca `None` → oczekiwany wynik: `[], {strategy: "doi", query_type: "doi filter", search_term: "10.1234/test", error: "No results found"}`.
    - Dane: Mock rzuca wyjątek `HTTPError("Timeout")` → oczekiwany wynik: `[], {..., error: "API error: Timeout"}`.
- **Test przypadków brzegowych**:
    - Dane: `Reference(doi=" 10.1234/test ")` → normalizuje DOI i zwraca poprawny wynik.
    - Dane: Wiele wyników `[dict(id="W123"), dict(id="W124")]` → wybiera `[dict(id="W123")]` i loguje ostrzeżenie.

---

### Plik: `domain/strategies/pmid_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie identyfikatora PubMed (PMID).

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"pmid"`.
    - `priority`: Zwraca 2.
    - `supported(reference)`: Sprawdza, czy pole `reference.pmid` istnieje i nie jest puste.
    - `validate_reference(reference)`: Weryfikuje format PMID przy użyciu wyrażenia regularnego `^\\d+$`, upewniając się, że PMID składa się tylko z cyfr. Jeśli format jest niepoprawny (np. „abc” lub „123-456”), rzuca wyjątek `ValueError` z komunikatem „Niepoprawny format PMID”.
    - `execute(reference)`:
        - Normalizuje PMID, usuwając białe znaki za pomocą `normalize_text` z `BaseStrategy`.
        - Wysyła zapytanie do repozytorium za pomocą `publication_repository.get_by_pmid(normalized_pmid)`.
        - Jeśli repozytorium zwraca wynik (słownik z danymi publikacji), umieszcza go w liście `[result]` i tworzy metadane `{strategy: "pmid", query_type: "pmid filter", search_term: normalized_pmid}`.
        - Jeśli wynik jest pusty, zwraca pustą listę `[]` z metadanymi `{..., error: "No results found"}`.
        - Jeśli repozytorium zgłasza błąd (np. timeout), zwraca pustą listę z metadanymi `{..., error: "API error: [szczegóły]"}`.
        - Loguje próbę za pomocą `log_attempt`.
- **Scenariusze**:
    - **Sukces**: Referencja ma PMID „12345678” → repozytorium zwraca `{id: "W123"}` → zwraca `[publication_data]` i metadane `{strategy: "pmid", query_type: "pmid filter", search_term: "12345678"}`.
    - **Błąd – niepoprawny PMID**: PMID „abc” → `validate_reference` rzuca `ValueError`, `supported` zwraca `False`.
    - **Błąd – brak wyników**: Poprawny PMID, ale brak publikacji → zwraca `[]`, metadane z błędem „No results found”.
    - **Błąd API**: Błąd HTTP 500 → zwraca `[]`, metadane z błędem „API error: Server error”.
    - **Przypadek brzegowy – wiele wyników**: PMID zwraca więcej niż jedną publikację (rzadkie) → wybiera pierwszą, loguje ostrzeżenie.
    - **Przypadek brzegowy – pusty PMID**: `reference.pmid` jest `None` lub `""` → `supported` zwraca `False`.
    - **Przypadek brzegowy – PMID z białymi znakami**: „ 12345678 ” → normalizuje do „12345678” i przetwarza poprawnie.

**Zależności**:

- **`domain/strategies/base_strategy.py`**: Klasa bazowa.
- **`domain/models/reference.py`**: Model `Reference`.
- **`domain/interfaces/publication_repository.py`**: Interfejs repozytorium dla `get_by_pmid`.

**Testy (TDD)**:

- **Test metody supported**:
    - Dane: `Reference(pmid="12345678")` → oczekiwany wynik: `True`.
    - Dane: `Reference(pmid=None)` → oczekiwany wynik: `False`.
    - Dane: `Reference(pmid="")` → oczekiwany wynik: `False`.
- **Test walidacji**:
    - Dane: `Reference(pmid="12345678")` → sukces.
    - Dane: `Reference(pmid="abc")` → `ValueError` z „Niepoprawny format PMID”.
    - Dane: `Reference(pmid="123-456")` → `ValueError`.
- **Test wykonania**:
    - Dane: `Reference(pmid="12345678")`, mock zwraca `{id: "W123"}` → `[dict(id="W123")], {strategy: "pmid", query_type: "pmid filter", search_term: "12345678"}`.
    - Dane: Mock zwraca `None` → `[], {..., error: "No results found"}`.
    - Dane: Mock rzuca wyjątek → `[], {..., error: "API error"}`.
- **Test przypadków brzegowych**:
    - Dane: `Reference(pmid=" 12345678 ")` → normalizuje i zwraca poprawny wynik.
    - Dane: Wiele wyników → wybiera pierwszy, loguje ostrzeżenie.

---

### Plik: `domain/strategies/title_authors_year_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie tytułu, listy autorów i roku publikacji.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"title_authors_year"`, identyfikując strategię.
    - `priority`: Zwraca 3, określając kolejność wykonywania.
    - `supported(reference)`: Sprawdza, czy referencja zawiera niepusty tytuł (`reference.title`), niepustą listę autorów (`reference.authors`) oraz rok publikacji (`reference.year`). Zwraca `True` tylko, jeśli wszystkie trzy pola są dostępne.
    - `validate_reference(reference)`: Weryfikuje dane wejściowe:
        - Tytuł musi mieć co najmniej 3 znaki po normalizacji, aby uniknąć zbyt ogólnych zapytań.
        - Lista autorów nie może być pusta, a każdy autor musi mieć co najmniej jedno nazwisko (np. „Smith”).
        - Rok publikacji musi być dodatnią liczbą całkowitą (np. większy od 0).
        - Jeśli którykolwiek warunek nie jest spełniony, rzuca wyjątek `ValueError` z odpowiednim komunikatem (np. „Tytuł za krótki”).
    - `execute(reference)`:
        - Normalizuje tytuł i każdego autora w liście za pomocą funkcji `normalize_text` z `BaseStrategy`, która usuwa znaki specjalne, konwertuje na małe litery i zachowuje spacje.
        - Tworzy zapytanie do repozytorium publikacji, wywołując metodę `search_by_title_authors_year` z normalized title, listą autorów i rokiem.
        - Otrzymuje listę wyników z OpenAlex (każdy wynik to słownik z polami takimi jak `title`, `authors`, `publication_year`).
        - Dla każdego wyniku oblicza podobieństwo tekstu przy użyciu biblioteki `rapidfuzz`:
            - **Podobieństwo tytułu**: Używa algorytmu `rapidfuzz.process.extractOne` z metryką `token_sort_ratio`, porównując znormalizowany tytuł referencji z tytułem wyniku. Wynik podobieństwa (w skali 0-1) musi przekraczać próg zdefiniowany w `Config.title_similarity_threshold` (domyślnie 0.85).
            - **Podobieństwo autorów**: Iteruje po liście autorów wyniku i referencji, obliczając podobieństwo dla każdej pary za pomocą `rapidfuzz.fuzz.partial_ratio`. Bierze średnią z podobieństw wszystkich par autorów, która musi przekraczać próg `Config.author_similarity_threshold` (domyślnie 0.9).
            - **Zgodność roku**: Sprawdza, czy rok publikacji wyniku (`publication_year`) dokładnie zgadza się z rokiem referencji (`reference.year`).
        - Jeśli wynik spełnia wszystkie trzy warunki (tytuł, autorzy, rok), dodaje go do listy wyników i zapisuje metadane zapytania: `{strategy: "title_authors_year", query_type: "title_author_year_search", search_term: normalized_title, authors: normalized_authors, year: year}`.
        - Jeśli żaden wynik nie spełnia progów podobieństwa lub zgodności roku, zwraca pustą listę wyników z metadanymi zawierającymi błąd: `{..., error: "Low similarity or no matching results"}`.
        - Jeśli repozytorium zgłasza błąd (np. timeout lub błąd HTTP), zwraca pustą listę z metadanymi `{..., error: "API error: [szczegóły]"}`.
        - Loguje próbę wyszukiwania za pomocą `log_attempt`, zapisując tytuł referencji, liczbę wyników i ewentualny błąd.
- **Scenariusze**:
    - **Sukces**: Referencja ma tytuł „Example Study”, autorów [„Smith, John”, „Doe, Jane”] i rok 2023. Wynik z OpenAlex ma podobny tytuł (podobieństwo 0.9 według `rapidfuzz`), tych samych autorów (średnie podobieństwo 0.95) i rok 2023 → zwraca `[publication_data]` z metadanymi `{strategy: "title_authors_year", query_type: "title_author_year_search", search_term: "example study", authors: ["smith john", "doe jane"], year: 2023}`.
    - **Błąd – brak wyników**: Zapytanie nie zwraca żadnych wyników → zwraca pustą listę `[]` i metadane z błędem „No results found”.
    - **Błąd – niski próg podobieństwa**: Wynik ma tytuł z podobieństwem 0.7 (poniżej 0.85) lub autorów z podobieństwem 0.8 (poniżej 0.9) → zwraca pustą listę z błędem „Low similarity”.
    - **Błąd – niezgodność roku**: Wynik ma rok 2022 zamiast 2023 → odrzuca wynik i zwraca pustą listę z błędem „Year mismatch”.
    - **Przypadek brzegowy – wiele wyników**: Otrzymano kilka wyników z różnym podobieństwem (np. 0.9, 0.85, 0.8 dla tytułów) → wybiera ten z najwyższym łącznym podobieństwem (ważona suma podobieństwa tytułu i autorów, np. 0.6 * tytuł + 0.4 * autorzy), loguje ostrzeżenie „Wiele wyników, wybrano najlepszy”.
    - **Przypadek brzegowy – krótki tytuł**: Tytuł „A” nie przechodzi walidacji → `validate_reference` rzuca `ValueError`, `supported` zwraca `False`.
    - **Przypadek brzegowy – różnice w autorach**: Jeden autor w wyniku różni się (np. „Smith, Bob” zamiast „Smith, John”) → średnie podobieństwo poniżej progu → odrzuca wynik.
    - **Przypadek brzegowy – błąd API**: Zapytanie kończy się timeoutem → zwraca pustą listę z błędem „API timeout”.
    - **Przypadek brzegowy – znormalizowane dane**: Tytuł „Example Study!” i autor „Smith, John!” normalizują się do „example study” i „smith john” → poprawnie porównuje z wynikami OpenAlex.

**Zależności**:

- **`domain/strategies/base_strategy.py`**: Klasa bazowa dostarczająca `normalize_text` i `log_attempt`.
- **`domain/models/reference.py`**: Model `Reference` dla danych wejściowych.
- **`domain/interfaces/publication_repository.py`**: Interfejs repozytorium dla metody `search_by_title_authors_year`.
- **`domain/models/config.py`**: Progi podobieństwa (`title_similarity_threshold`, `author_similarity_threshold`).
- **`rapidfuzz`**: Biblioteka do obliczania podobieństwa tekstu dla tytułu i autorów.

**Testy (TDD)**:

- **Test metody supported**:
    - Dane: `Reference(title="Example Study", authors=["Smith, John"], year=2023)` → oczekiwany wynik: `True`.
    - Dane: `Reference(title="Test")` → oczekiwany wynik: `False` (brak autorów lub roku).
    - Dane: `Reference(title="", authors=["Smith"], year=2023)` → oczekiwany wynik: `False`.
- **Test walidacji**:
    - Dane: `Reference(title="Ex", authors=["Smith"], year=2023)` → `validate_reference` rzuca `ValueError` z „Tytuł za krótki”.
    - Dane: `Reference(title="Example Study", authors=[], year=2023)` → `ValueError` z „Pusta lista autorów”.
    - Dane: `Reference(title="Example Study", authors=["Smith"], year=-1)` → `ValueError` z „Niepoprawny rok”.
    - Dane: `Reference(title="Example Study", authors=["Smith"], year=2023)` → sukces.
- **Test wykonania**:
    - Dane: `Reference(title="Example Study", authors=["Smith, John"], year=2023)`, mock repozytorium zwraca `[{title: "Example Study", authors: ["Smith, John"], publication_year: 2023}]`, progi: `title_similarity_threshold=0.85`, `author_similarity_threshold=0.9`.
        - Oczekiwany wynik: `[dict(title="Example Study", ...)]`, metadane `{strategy: "title_authors_year", query_type: "title_author_year_search", search_term: "example study", authors: ["smith john"], year: 2023}`.
    - Dane: Mock zwraca `[{title: "Other Study", authors: ["Smith, Bob"], publication_year: 2023}]`, podobieństwo tytułu 0.7, autorów 0.8.
        - Oczekiwany wynik: `[]`, metadane `{..., error: "Low similarity"}`.
    - Dane: Mock zwraca `[{title: "Example Study", authors: ["Smith, John"], publication_year: 2022}]`.
        - Oczekiwany wynik: `[]`, metadane `{..., error: "Year mismatch"}`.
    - Dane: Mock zwraca `[]`.
        - Oczekiwany wynik: `[]`, metadane `{..., error: "No results found"}`.
    - Dane: Mock rzuca wyjątek `HTTPError("Timeout")`.
        - Oczekiwany wynik: `[]`, metadane `{..., error: "API error: Timeout"}`.
- **Test przypadków brzegowych**:
    - Dane: Wiele wyników `[{title: "Example Study", authors: ["Smith, John"], publication_year: 2023}, {title: "Example Study 2", ...}]`, podobieństwa: 0.95 i 0.85.
        - Oczekiwany wynik: Wybiera `[dict(title="Example Study", ...)]`, loguje ostrzeżenie „Wiele wyników”.
    - Dane: Tytuł „Example Study!” → normalizuje do „example study” i poprawnie porównuje.
    - Dane: Autor „Smith, John!” → normalizuje do „smith john” i poprawnie porównuje.

---

### Plik: `domain/strategies/title_authors_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie tytułu i listy autorów, bez uwzględniania roku publikacji.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"title_authors"`.
    - `priority`: Zwraca 4.
    - `supported(reference)`: Sprawdza, czy referencja zawiera niepusty tytuł (`reference.title`) i niepustą listę autorów (`reference.authors`). Rok publikacji (`reference.year`) jest opcjonalny.
    - `validate_reference(reference)`: Weryfikuje:
        - Tytuł: Minimum 3 znaki po normalizacji.
        - Lista autorów: Niepusta, każdy autor z co najmniej jednym nazwiskiem.
        - Jeśli warunki nie są spełnione, rzuca `ValueError` (np. „Pusta lista autorów”).
    - `execute(reference)`:
        - Normalizuje tytuł i każdego autora za pomocą `normalize_text` z `BaseStrategy`.
        - Wywołuje `publication_repository.search_by_title_authors(normalized_title, normalized_authors)`.
        - Otrzymuje listę wyników z OpenAlex.
        - Dla każdego wyniku oblicza podobieństwo za pomocą `rapidfuzz`:
            - **Podobieństwo tytułu**: Używa `rapidfuzz.process.extractOne` z `token_sort_ratio`, próg `Config.title_similarity_threshold` (domyślnie 0.85).
            - **Podobieństwo autorów**: Oblicza średnie podobieństwo za pomocą `rapidfuzz.fuzz.partial_ratio` dla każdej pary autorów, próg `Config.author_similarity_threshold` (domyślnie 0.9).
        - Jeśli wynik spełnia oba progi, zwraca go w liście `[result]` z metadanymi `{strategy: "title_authors", query_type: "title_author_search", search_term: normalized_title, authors: normalized_authors}`.
        - Jeśli brak wyników lub żaden nie spełnia progów, zwraca pustą listę z błędem `{..., error: "Low similarity or no matching results"}`.
        - Jeśli repozytorium zgłasza błąd, zwraca pustą listę z `{..., error: "API error: [szczegóły]"}`.
        - Loguje próbę za pomocą `log_attempt`.
- **Scenariusze**:
    - **Sukces**: Tytuł „Example Study” i autorzy [„Smith, John”] pasują do wyniku z podobieństwem tytułu 0.9 i autorów 0.95 → zwraca `[publication_data]` z metadanymi `{strategy: "title_authors", query_type: "title_author_search", search_term: "example study", authors: ["smith john"]}`.
    - **Błąd – brak wyników**: Zapytanie nie zwraca wyników → pusta lista, błąd „No results found”.
    - **Błąd – niski próg**: Podobieństwo tytułu 0.7 lub autorów 0.8 → pusta lista, błąd „Low similarity”.
    - **Przypadek brzegowy – wiele wyników**: Wybiera najlepszy wynik pod względem łącznego podobieństwa, loguje ostrzeżenie.
    - **Przypadek brzegowy – brak roku**: Ignoruje rok i przetwarza tylko tytuł i autorów.
    - **Przypadek brzegowy – błąd API**: Zwraca pustą listę z błędem „API timeout”.
    - **Przypadek brzegowy – znormalizowane dane**: Tytuł „Example Study!” → normalizuje i poprawnie porównuje.

**Zależności**:

- **`domain/strategies/base_strategy.py`**.
- **`domain/models/reference.py`**.
- **`domain/interfaces/publication_repository.py`**.
- **`domain/models/config.py`**.
- **`rapidfuzz`**.

**Testy (TDD)**:

- **Test metody supported**:
    - Dane: `Reference(title="Example Study", authors=["Smith, John"])` → oczekiwany wynik: `True`.
    - Dane: `Reference(title="Test")` → oczekiwany wynik: `False`.
    - Dane: `Reference(title="", authors=["Smith"])` → oczekiwany wynik: `False`.
- **Test walidacji**:
    - Dane: `Reference(title="Ex", authors=["Smith"])` → `ValueError` z „Tytuł za krótki”.
    - Dane: `Reference(title="Example Study", authors=[])` → `ValueError` z „Pusta lista autorów”.
    - Dane: `Reference(title="Example Study", authors=["Smith"])` → sukces.
- **Test wykonania**:
    - Dane: `Reference(title="Example Study", authors=["Smith, John"])`, mock zwraca `[{title: "Example Study", authors: ["Smith, John"]}]`, progi spełnione → `[dict(...)]`, metadane `{strategy: "title_authors", query_type: "title_author_search", search_term: "example study", authors: ["smith john"]}`.
    - Dane: Mock zwraca `[{title: "Other Study", authors: ["Smith, Bob"]}]`, podobieństwo poniżej progów → `[], {..., error: "Low similarity"}`.
    - Dane: Mock zwraca `[]` → `[], {..., error: "No results found"}`.
    - Dane: Mock rzuca wyjątek → `[], {..., error: "API error"}`.
- **Test przypadków brzegowych**:
    - Dane: Wiele wyników → wybiera najlepszy.
    - Dane: Tytuł „Example Study!” → normalizuje i poprawnie porównuje.

---

### Plik: `domain/strategies/title_year_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie tytułu i roku publikacji.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"title_year"`.
    - `priority`: Zwraca 5.
    - `supported(reference)`: Sprawdza, czy referencja zawiera niepusty tytuł (`reference.title`) i rok publikacji (`reference.year`).
    - `validate_reference(reference)`: Weryfikuje:
        - Tytuł: Minimum 3 znaki po normalizacji.
        - Rok: Dodatni (większy od 0).
        - Jeśli warunki nie są spełnione, rzuca `ValueError`.
    - `execute(reference)`:
        - Normalizuje tytuł za pomocą `normalize_text`.
        - Wywołuje `publication_repository.search_by_title_year(normalized_title, year)`.
        - Otrzymuje listę wyników z OpenAlex.
        - Dla każdego wyniku oblicza podobieństwo za pomocą `rapidfuzz`:
            - **Podobieństwo tytułu**: `rapidfuzz.process.extractOne` z `token_sort_ratio`, próg `Config.title_similarity_threshold` (0.85).
            - **Zgodność roku**: Sprawdza dokładną zgodność `publication_year` z `reference.year`.
        - Jeśli wynik spełnia oba warunki, zwraca go w liście `[result]` z metadanymi `{strategy: "title_year", query_type: "title_year_search", search_term: normalized_title, year: year}`.
        - Jeśli brak wyników, niski próg lub niezgodność roku, zwraca pustą listę z błędem `{..., error: "Low similarity, year mismatch or no results"}`.
        - Jeśli błąd API, zwraca pustą listę z `{..., error: "API error"}`.
        - Loguje próbę.
- **Scenariusze**:
    - **Sukces**: Tytuł „Example Study” i rok 2023 pasują do wyniku z podobieństwem 0.9 i rokiem 2023 → `[publication_data]` z metadanymi `{strategy: "title_year", ...}`.
    - **Błąd – brak wyników**: Pusta lista wyników → błąd „No results found”.
    - **Błąd – niski próg**: Podobieństwo tytułu 0.7 → błąd „Low similarity”.
    - **Błąd – niezgodność roku**: Rok wyniku 2022 zamiast 2023 → błąd „Year mismatch”.
    - **Przypadek brzegowy – wiele wyników**: Wybiera najlepszy, loguje ostrzeżenie.
    - **Przypadek brzegowy – błąd API**: Zwraca pustą listę z błędem.
    - **Przypadek brzegowy – znormalizowany tytuł**: „Example Study!” → poprawnie porównuje.

**Zależności**:

- **`domain/strategies/base_strategy.py`**.
- **`domain/models/reference.py`**.
- **`domain/interfaces/publication_repository.py`**.
- **`domain/models/config.py`**.
- **`rapidfuzz`**.

**Testy (TDD)**:

- **Test supported**:
    - Dane: `Reference(title="Example Study", year=2023)` → `True`.
    - Dane: `Reference(title="Test")` → `False`.
- **Test walidacji**:
    - Dane: `Reference(title="Ex", year=2023)` → `ValueError`.
    - Dane: `Reference(title="Example Study", year=-1)` → `ValueError`.
- **Test wykonania**:
    - Dane: `Reference(title="Example Study", year=2023)`, mock zwraca `[{title: "Example Study", publication_year: 2023}]` → `[dict(...)]`.
    - Dane: Mock zwraca `[{title: "Other", publication_year: 2023}]`, podobieństwo 0.7 → `[], {..., error: "Low similarity"}`.
    - Dane: Mock zwraca `[{title: "Example Study", publication_year: 2022}]` → `[], {..., error: "Year mismatch"}`.

---

### Plik: `domain/strategies/title_journal_strategy.py`

**Opis**: Strategia wyszukiwania publikacji na podstawie tytułu i czasopisma.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"title_journal"`.
    - `priority`: Zwraca 6.
    - `supported(reference)`: Sprawdza, czy referencja zawiera niepusty tytuł (`reference.title`) i czasopismo (`reference.journal`).
    - `validate_reference(reference)`: Weryfikuje:
        - Tytuł i czasopismo: Minimum 3 znaki po normalizacji.
        - Jeśli warunki nie są spełnione, rzuca `ValueError`.
    - `execute(reference)`:
        - Normalizuje tytuł i czasopismo za pomocą `normalize_text`.
        - Wywołuje `publication_repository.search_by_title_journal(normalized_title, normalized_journal)`.
        - Otrzymuje listę wyników.
        - Dla każdego wyniku oblicza podobieństwo za pomocą `rapidfuzz`:
            - **Podobieństwo tytułu**: `rapidfuzz.process.extractOne` z `token_sort_ratio`, próg `Config.title_similarity_threshold` (0.85).
            - **Podobieństwo czasopisma**: `rapidfuzz.fuzz.partial_ratio`, próg `Config.title_similarity_threshold` (0.85).
        - Jeśli wynik spełnia oba progi, zwraca `[result]` z metadanymi `{strategy: "title_journal", query_type: "title_journal_search", search_term: normalized_title, journal: normalized_journal}`.
        - Jeśli brak wyników lub niski próg, zwraca pustą listę z błędem `{..., error: "Low similarity or no results"}`.
        - Jeśli błąd API, zwraca pustą listę z `{..., error: "API error"}`.
        - Loguje próbę.
- **Scenariusze**:
    - **Sukces**: Tytuł „Example Study” i czasopismo „Journal of Examples” pasują z podobieństwem 0.9 → `[publication_data]`.
    - **Błąd – brak wyników**: Pusta lista → błąd „No results found”.
    - **Błąd – niski próg**: Podobieństwo czasopisma 0.7 → błąd „Low similarity”.
    - **Przypadek brzegowy – skrócona nazwa czasopisma**: „J Examples” → normalizuje i porównuje.
    - **Przypadek brzegowy – błąd API**: Zwraca pustą listę.

**Zależności**:

- **`domain/strategies/base_strategy.py`**.
- **`domain/models/reference.py`**.
- **`domain/interfaces/publication_repository.py`**.
- **`domain/models/config.py`**.
- **`rapidfuzz`**.

**Testy (TDD)**:

- **Test supported**:
    - Dane: `Reference(title="Example Study", journal="Journal of Examples")` → `True`.
    - Dane: `Reference(title="Test")` → `False`.
- **Test walidacji**:
    - Dane: `Reference(title="Ex", journal="Journal")` → `ValueError`.
- **Test wykonania**:
    - Dane: `Reference(title="Example Study", journal="Journal of Examples")`, mock zwraca `[{title: "Example Study", journal: "Journal of Examples"}]` → `[dict(...)]`.
    - Dane: Mock zwraca `[{title: "Other", journal: "Other Journal"}]` → `[], {..., error: "Low similarity"}`.

---

### Plik: `domain/strategies/title_only_strategy.py`

**Opis**: Strategia wyszukiwania publikacji tylko na podstawie tytułu.

**Logika implementacji**:

- **Metody**:
    - `name`: Zwraca `"title_only"`.
    - `priority`: Zwraca 7.
    - `supported(reference)`: Sprawdza, czy referencja zawiera niepusty tytuł (`reference.title`).
    - `validate_reference(reference)`: Weryfikuje długość tytułu (minimum 3 znaki po normalizacji).
    - `execute(reference)`:
        - Normalizuje tytuł za pomocą `normalize_text`.
        - Wywołuje `publication_repository.search_by_title(normalized_title)`.
        - Otrzymuje listę wyników.
        - Dla każdego wyniku oblicza podobieństwo tytułu za pomocą `rapidfuzz.process.extractOne` z `token_sort_ratio`, wymagając wyższego progu podobieństwa (np. `Config.title_similarity_threshold` podniesione do 0.9 dla większej precyzji, ponieważ brak dodatkowych filtrów).
        - Jeśli wynik spełnia próg, zwraca `[result]` z metadanymi `{strategy: "title_only", query_type: "title_search", search_term: normalized_title}`.
        - Jeśli brak wyników lub niski próg, zwraca pustą listę z błędem `{..., error: "Low similarity or no results"}`.
        - Jeśli błąd API, zwraca pustą listę z `{..., error: "API error"}`.
        - Loguje próbę.
- **Scenariusze**:
    - **Sukces**: Tytuł „Example Study” pasuje z podobieństwem 0.95 → `[publication_data]`.
    - **Błąd – brak wyników**: Pusta lista → błąd „No results found”.
    - **Błąd – niski próg**: Podobieństwo 0.8 → błąd „Low similarity”.
    - **Przypadek brzegowy – wiele wyników**: Wybiera najlepszy, loguje ostrzeżenie.
    - **Przypadek brzegowy – krótki tytuł**: Odrzuca z `ValueError`.
    - **Przypadek brzegowy – błąd API**: Zwraca pustą listę.

**Zależności**:

- **`domain/strategies/base_strategy.py`**.
- **`domain/models/reference.py`**.
- **`domain/interfaces/publication_repository.py`**.
- **`domain/models/config.py`**.
- **`rapidfuzz`**.

**Testy (TDD)**:

- **Test supported**:
    - Dane: `Reference(title="Example Study")` → `True`.
    - Dane: `Reference(title="")` → `False`.
- **Test walidacji**:
    - Dane: `Reference(title="Ex")` → `ValueError`.
- **Test wykonania**:
    - Dane: `Reference(title="Example Study")`, mock zwraca `[{title: "Example Study"}]` → `[dict(...)]`.
    - Dane: Mock zwraca `[{title: "Other"}]` → `[], {..., error: "Low similarity"}`.

---

### Krok 6: Implementacja repozytorium OpenAlex

### Plik: infrastructure/repositories/openalex_repository.py

**Opis**: Repozytorium odpowiedzialne za komunikację z API OpenAlex za pomocą biblioteki pyalex, realizujące metody zdefiniowane w interfejsie PublicationRepository. Implementacja została zoptymalizowana pod kątem wyszukiwania publikacji, szczególnie w strategiach uwzględniających autorów, gdzie różne kombinacje nazw (np. pełne imię, inicjały, odwrócona kolejność) oraz inicjały są porównywane z wynikami OpenAlex. Wykorzystuje zaawansowane funkcje pyalex, takie jak filtrowanie, wyszukiwanie pełnotekstowe, sortowanie wyników, paginacja oraz konfiguracja „polite pool” dla szybszych i bardziej stabilnych odpowiedzi. Zapewnia niezawodność dzięki obsłudze błędów i mechanizmowi ponawiania zapytań.

**Logika implementacji**:

- **Konfiguracja początkowa**:
    - Ustawia e-mail dla „polite pool” (pyalex.config.email) na podstawie wartości z Config.openalex_email, jeśli jest dostępne, aby uzyskać szybsze i bardziej stabilne odpowiedzi API.
    - Konfiguruje parametry ponawiania zapytań: max_retries (z Config.max_retries, domyślnie 3), retry_backoff_factor (z Config.retry_backoff_factor, domyślnie 0.5) oraz retry_http_codes (z Config.retry_http_codes, domyślnie [429, 500, 503]). Umożliwia to automatyczne ponawianie zapytań w przypadku błędów takich jak limit żądań (429) czy problemy serwerowe (500, 503).
- **Metody**:
    - get_by_doi(doi):
        - Normalizuje DOI za pomocą funkcji normalize_text z BaseStrategy, usuwając znaki specjalne, białe znaki i konwertując na małe litery.
        - Wysyła zapytanie do API OpenAlex za pomocą pyalex.Works().filter(doi=normalized_doi).get(), ograniczając wynik do jednej publikacji poprzez parametr per_page=1.
        - Jeśli API zwraca niepustą listę wyników, zwraca pierwszy element jako słownik (np. {id: "W123", title: "Example"}).
        - Jeśli lista wyników jest pusta lub występuje błąd (np. HTTP 404, timeout), zwraca None.
        - Loguje próbę zapytania, zapisując znormalizowane DOI, liczbę zwróconych wyników (0 lub 1) oraz ewentualny błąd.
    - get_by_pmid(pmid):
        - Normalizuje PMID, usuwając białe znaki i weryfikując, czy składa się tylko z cyfr.
        - Wysyła zapytanie za pomocą pyalex.Works().filter(pmid=normalized_pmid).get(), ograniczając do jednej publikacji.
        - Zwraca wynik jako słownik lub None w przypadku braku wyników lub błędu.
        - Loguje próbę, podobnie jak w get_by_doi.
    - search_by_title_authors_year(title, authors, year):
        - Normalizuje tytuł i każdego autora w liście za pomocą BaseStrategy.normalize_text, zapewniając spójność danych.
        - Generuje różne kombinacje nazw autorów do wyszukiwania, uwzględniając możliwe formaty w danych wejściowych (np. „Adam U”, „Adam Unikon”, „Unikon Adam”):
            - Dla każdego autora:
                - Rozdziela nazwę na części (np. „Adam Unikon” → [„Adam”, „Unikon”]).
                - Tworzy warianty: pełne imię i nazwisko („Adam Unikon”), odwrócona kolejność („Unikon Adam”), inicjały („A. Unikon” lub „A U”).
                - Jeśli imię to inicjał (np. „A”), uwzględnia tylko nazwisko lub inicjał z nazwiskiem (np. „A Unikon”).
            - Tworzy listę wszystkich kombinacji (np. [„adam unikon”, „unikon adam”, „a unikon”, „a u”]).
        - Wysyła zapytanie do API za pomocą pyalex.Works().search_filter(title=normalized_title).filter(authorships={"author": {"display_name": "|".join(author_combinations)}}).filter(publication_year=year).sort(relevance_score="desc").
            - Używa wyszukiwania pełnotekstowego dla tytułu (search_filter), aby zwiększyć szanse na dopasowanie.
            - Filtruje autorów, używając operatora OR (|) dla wszystkich kombinacji nazw, co pozwala dopasować różne formaty w OpenAlex.
            - Filtruje rok publikacji (publication_year) dla dokładnego dopasowania.
            - Sortuje wyniki według trafności (relevance_score), aby priorytetyzować najbardziej pasujące publikacje.
        - Ogranicza wyniki do maksymalnie 25 publikacji (per_page=25), aby zbalansować precyzję i wydajność.
        - Zwraca listę wyników jako listę słowników publikacji lub pustą listę w przypadku braku wyników lub błędu.
        - Loguje zapytanie, zapisując znormalizowany tytuł, liczbę wyników i ewentualny błąd.
    - search_by_title_authors(title, authors):
        - Jak search_by_title_authors_year, ale bez filtru roku publikacji.
        - Generuje kombinacje autorów w ten sam sposób (pełne imię, odwrócona kolejność, inicjały, itp.).
        - Wysyła zapytanie za pomocą pyalex.Works().search_filter(title=normalized_title).filter(authorships={"author": {"display_name": "|".join(author_combinations)}}).sort(relevance_score="desc").
        - Ogranicza wyniki do 25 publikacji.
        - Zwraca listę wyników lub pustą listę.
        - Loguje próbę.
    - search_by_title_year(title, year):
        - Normalizuje tytuł za pomocą BaseStrategy.normalize_text.
        - Wysyła zapytanie za pomocą pyalex.Works().search_filter(title=normalized_title).filter(publication_year=year).sort(relevance_score="desc").
        - Ogranicza wyniki do 25 publikacji.
        - Zwraca listę wyników lub pustą listę.
        - Loguje próbę.
    - search_by_title_journal(title, journal):
        - Normalizuje tytuł i czasopismo.
        - Wysyła zapytanie za pomocą pyalex.Works().search_filter(title=normalized_title).filter(primary_location={"source": {"display_name": normalized_journal}}).sort(relevance_score="desc").
        - Ogranicza wyniki do 25 publikacji.
        - Zwraca listę wyników lub pustą listę.
        - Loguje próbę.
    - search_by_title(title):
        - Normalizuje tytuł.
        - Wykonuje szerokie wyszukiwanie pełnotekstowe za pomocą pyalex.Works().search_filter(title=normalized_title).sort(relevance_score="desc").
        - Ogranicza wyniki do 25 publikacji, aby uniknąć przeciążenia.
        - Zwraca listę wyników lub pustą listę.
        - Loguje próbę.
- **Scenariusze**:
    - **Sukces – pojedyncza publikacja**:
        - Dla get_by_doi("10.1234/test") API zwraca [dict(id="W123", title="Example")] → zwraca {id: "W123", title: "Example"}.
        - Dla get_by_pmid("12345678") zwraca {id: "W123"}.
    - **Sukces – wiele wyników z autorami**:
        - Dla search_by_title_authors_year("Example Study", ["Adam U", "Adam Unikon", "Unikon Adam"], 2023):
            - Generuje kombinacje: [„adam u”, „adam unikon”, „unikon adam”, „a unikon”, „a u”].
            - Zapytanie uwzględnia wszystkie warianty (np. display_name="adam u|adam unikon|unikon adam|a unikon|a u").
            - API zwraca publikacje z autorami „Adam Unikon” lub „A. Unikon” → zwraca listę wyników.
    - **Sukces – dopasowanie inicjału**:
        - Referencja ma autora „A Unikon” → wyszukuje kombinacje [„a unikon”, „unikon a”] → dopasowuje do „Adam Unikon” w OpenAlex na podstawie nazwiska „Unikon”.
    - **Sukces – wyszukiwanie tytułu**:
        - Dla search_by_title("Example Study") zwraca listę publikacji z podobnymi tytułami, posortowaną według trafności.
    - **Błąd – brak wyników**:
        - Dla get_by_doi("10.1234/nonexistent") API zwraca [] → zwraca None.
        - Dla search_by_title_authors("Nonexistent", ["Unknown Author"]) zwraca pustą listę.
    - **Błąd – limit żądań (HTTP 429)**:
        - Ponawia zapytanie max_retries razy z opóźnieniem retry_backoff_factor.
        - Jeśli nieudane, zwraca None lub pustą listę z błędem „API error: Rate limit exceeded”.
    - **Błąd – błąd serwera (HTTP 500, 503)**:
        - Ponawia zapytanie zgodnie z konfiguracją.
        - Po niepowodzeniu zwraca None lub pustą listę z błędem „API error: Server error”.
    - **Przypadek brzegowy – niepoprawne dane**:
        - Dla get_by_doi("") lub search_by_title("") zwraca pustą listę, loguje ostrzeżenie „Puste zapytanie”.
    - **Przypadek brzegowy – niepoprawny autor**:
        - Dla search_by_title_authors_year("Test", [""], 2023) zwraca pustą listę, loguje ostrzeżenie „Pusta nazwa autora”.
    - **Przypadek brzegowy – inicjały autorów**:
        - Autor „A U” → generuje kombinacje [„a u”, „u a”] → dopasowuje do „Adam Unikon” na podstawie nazwiska „Unikon”.
    - **Przypadek brzegowy – odwrócona kolejność autorów**:
        - Autor „Unikon Adam” → dopasowuje do „Adam Unikon” w OpenAlex.
    - **Przypadek brzegowy – częściowe dane**:
        - Dla search_by_title_authors_year z jednym autorem zamiast wielu → zwraca dostępne wyniki.
    - **Przypadek brzegowy – timeout**:
        - Zapytanie przekracza limit czasu → zwraca pustą listę z błędem „API timeout”.
    - **Przypadek brzegowy – znormalizowane dane**:
        - Tytuł „Example Study!” → normalizuje do „example study”.
        - Autor „Adam Unikon!” → normalizuje do „adam unikon” i przetwarza poprawnie.

**Zależności**:

- **pyalex**: Biblioteka do komunikacji z API OpenAlex, obsługująca zaawansowane filtrowanie, wyszukiwanie pełnotekstowe i sortowanie.
- **aiohttp**: Używana wewnętrznie przez pyalex do asynchronicznych zapytań HTTP.
- **domain/interfaces/publication_repository.py**: Interfejs definiujący metody repozytorium.
- **domain/strategies/base_strategy.py**: Funkcja normalize_text do normalizacji danych wejściowych.
- **domain/models/config.py**: Konfiguracja parametrów openalex_email, max_retries, retry_backoff_factor, retry_http_codes.

**Testy (TDD)**:

- **Test konfiguracji**:
    - Dane: Config(openalex_email="test@example.com", max_retries=3, retry_backoff_factor=0.5, retry_http_codes=[429, 500, 503]).
        - Oczekiwany wynik: pyalex.config.email ustawione na „[test@example.com](mailto:test@example.com)”, pyalex.config.max_retries=3, pyalex.config.retry_backoff_factor=0.5.
    - Dane: Brak openalex_email → oczekiwany wynik: pyalex.config.email=None.
- **Test metody get_by_doi**:
    - Dane: doi="10.1234/test", mock pyalex.Works().filter(doi="10.1234/test").get() zwraca [{id: "W123", title: "Example"}].
        - Oczekiwany wynik: {id: "W123", title: "Example"}.
    - Dane: Mock zwraca [] → oczekiwany wynik: None.
    - Dane: Mock rzuca HTTPError("429 Too Many Requests"), max_retries=2 → oczekiwany wynik: Ponawia zapytanie dwukrotnie, zwraca None z błędem „Rate limit exceeded”.
    - Dane: doi="" → oczekiwany wynik: None, log z ostrzeżeniem „Puste zapytanie”.
    - Dane: doi=" 10.1234/test " → normalizuje do „10.1234/test” i zwraca poprawny wynik.
- **Test metody get_by_pmid**:
    - Dane: pmid="12345678", mock zwraca [{id: "W123"}].
        - Oczekiwany wynik: {id: "W123"}.
    - Dane: Mock zwraca [] → None.
    - Dane: Mock rzuca wyjątek HTTPError("500") → None, log z błędem „Server error”.
- **Test metody search_by_title_authors_year**:
    - Dane: title="Example Study", authors=["Adam U", "Adam Unikon", "Unikon Adam"], year=2023, mock pyalex.Works().search_filter(title="example study").filter(authorships={"author": {"display_name": "adam u|adam unikon|unikon adam|a unikon|a u"}}).filter(publication_year=2023).get() zwraca [{id: "W123", title: "Example Study", authors: [{"display_name": "Adam Unikon"}], publication_year: 2023}].
        - Oczekiwany wynik: [dict(id="W123", ...)], log z liczbą wyników.
    - Dane: Autor „A Unikon”, mock zwraca [{id: "W123", authors: [{"display_name": "Adam Unikon"}]}].
        - Oczekiwany wynik: [dict(id="W123", ...)] (dopasowanie nazwiska „Unikon”).
    - Dane: Autor „Unikon Adam”, mock zwraca [{id: "W123", authors: [{"display_name": "Adam Unikon"}]}].
        - Oczekiwany wynik: [dict(id="W123", ...)] (dopasowanie odwróconej kolejności).
    - Dane: Mock zwraca [] → [], log z błędem „No results found”.
    - Dane: Mock rzuca HTTPError("503") → [], log z błędem „Service unavailable”.
    - Dane: Pusty autor [""] → [], log z ostrzeżeniem „Pusta nazwa autora”.
- **Test metody search_by_title_authors**:
    - Dane: title="Example Study", authors=["Adam U"], mock zwraca [{id: "W123", title: "Example Study", authors: [{"display_name": "Adam Unikon"}]}].
        - Oczekiwany wynik: [dict(id="W123", ...)].
    - Dane: Mock zwraca [] → [].
- **Test metody search_by_title_year**:
    - Dane: title="Example Study", year=2023, mock zwraca [{id: "W123", title: "Example Study", publication_year: 2023}].
        - Oczekiwany wynik: [dict(id="W123", ...)].
    - Dane: Mock zwraca [] → [].
- **Test metody search_by_title_journal**:
    - Dane: title="Example Study", journal="Journal of Examples", mock zwraca [{id: "W123", title: "Example Study"}].
        - Oczekiwany wynik: [dict(id="W123", ...)].
- **Test metody search_by_title**:
    - Dane: title="Example Study", mock zwraca [dict(id="W123", title="Example Study")].
        - Oczekiwany wynik: [dict(id="W123", ...)].
    - Dane: title="" → [], log z ostrzeżeniem „Puste zapytanie”.
- **Test przypadków brzegowych**:
    - Dane: Wiele wyników dla search_by_title_authors_year → zwraca listę posortowaną według trafności.
    - Dane: Autor „A U” → dopasowuje do „Adam Unikon” na podstawie „Unikon”.
    - Dane: Tytuł „Example Study!” → normalizuje i zwraca poprawny wynik.
- **Uwagi dotyczące testów**:
    - Testy jednostkowe mockują pyalex, aby uniknąć rzeczywistych zapytań API.
    - Testy pokrywają różne kody HTTP (200, 404, 429, 500, 503) oraz scenariusze z kombinacjami autorów (inicjały, odwrócona kolejność, pełne imię).
    - Testy integracyjne z API OpenAlex są ograniczone przez limity żądań i wymagają kontrolowanego środowiska.

---

### Krok 7: Implementacja usługi dopasowywania

### Plik: `application/services/matching_service.py`

**Opis**: Usługa koordynująca proces dopasowywania badań do publikacji.

**Logika implementacji**:
- **Metody**:
- `__init__(config)`:
- Inicjalizuje repozytorium (`OpenAlexRepository`).
- Tworzy listę strategii (`DoiStrategy`, `PmidStrategy`, itp.), pomijając wyłączone w `Config.disable_strategies`.
- Sortuje strategie według `priority`.
- `match_study(study)`:
- Pobiera `reference` z `Study`.
- Sprawdza minimalne dane (`reference.has_minimal_data`).
- Iteruje po strategiach:
- Jeśli `supported(reference)` zwraca `True`, wywołuje `execute(reference)`.
- Zapisuje próbę w `SearchResult.search_attempts`.
- Jeśli wyniki istnieją, weryfikuje podobieństwo (tytuł, autorzy, czasopismo).
- Jeśli podobieństwo powyżej progów (`Config.title_similarity_threshold`, itp.), ustawia status `"found"`.
- Jeśli poniżej, ustawia `"rejected"` z błędem `"Low similarity"`.
- Jeśli brak wyników po wszystkich strategiach, ustawia `"not_found"`.
- Jeśli brak minimalnych danych, ustawia `"skipped"`.
- Zwraca `SearchResult` z odpowiednimi polami.
- **Scenariusze**:
- **Sukces**: Strategia DOI znajduje wynik → status `"found"`, zapisuje dane publikacji.
- **Niepowodzenie**: Wszystkie strategie zwracają pustą listę → status `"not_found"`, zapisuje wszystkie próby.
- **Odrzucenie**: Wynik poniżej progu → status `"rejected"`.
- **Pominięcie**: Brak danych → status `"skipped"`.
- **Przypadek brzegowy**: Wyłączone strategie → pomija je.
- **Przypadek brzegowy**: Błąd API → zapisuje błąd w `search_attempts`.

**Zależności**:
- **`domain/models/study.py`**: Model `Study`.
- **`domain/models/search_result.py`**: Model `SearchResult`.
- **`domain/models/config.py`**: Konfiguracja.
- **`domain/strategies/*_strategy.py`**: Wszystkie strategie.
- **`infrastructure/repositories/openalex_repository.py`**: Repozytorium.
- **`domain/enums/search_status.py`**: Statusy.

**Testy (TDD)**:
- **Test inicjalizacji**:
- Test: `Config(disable_strategies=["doi"])` → brak `DoiStrategy` w liście.
- Test: Domyślna konfiguracja → wszystkie strategie w kolejności priorytetów.
- **Test dopasowywania**:
- Test: `Study` z DOI, mock `DoiStrategy` zwraca wynik → `SearchResult(status=SearchStatus.FOUND)`.
- Test: `Study` bez danych → `SearchResult(status=SearchStatus.SKIPPED)`.
- Test: Wynik poniżej progu → `SearchResult(status=SearchStatus.REJECTED)`.

---

### Krok 8: Implementacja narzędzi pomocniczych

### Plik: `utils/dict_helpers.py`

**Opis**: Narzędzia do operacji na słownikach, używane w modelach do serializacji.

**Logika implementacji**:
- **Funkcje**:
- `add_optional_field(d, key, value)`:
- Dodaje parę klucz-wartość do słownika tylko, jeśli `value` nie jest `None`.
- Zwraca zmodyfikowany słownik (dla wygody).
- **Scenariusze**:
- **Sukces**: `value="test"` → dodaje `{key: "test"}` do słownika.
- **Pominięcie**: `value=None` → nie modyfikuje słownika.
- **Przypadek brzegowy**: Pusty klucz → ignoruje (loguje ostrzeżenie).

**Zależności**:
- **`typing`**: Anotacje typów (`Dict`, `Any`).

**Testy (TDD)**:
- **Test dodawania**:
- Test: `d = {}; add_optional_field(d, "key", "value")` → `d == {"key": "value"}`.
- Test: `add_optional_field(d, "key2", None)` → `d` bez zmian.
- **Test przypadków brzegowych**:
- Test: `add_optional_field(d, "", "value")` → ostrzeżenie w logach, brak zmian.

**Uwaga dotycząca DRY**: Funkcja `add_optional_field` jest używana we wszystkich modelach (`Reference`, `Study`, `SearchResult`) do serializacji, aby uniknąć duplikacji logiki.

---


---

### Krok 9: Generowanie raportu podsumowania

#### Plik: `utils/report_formatter.py`

**Opis**: Moduł odpowiedzialny za generowanie eleganckiego raportu podsumowania w terminalu przy użyciu biblioteki `rich`. Raport prezentuje konfigurację wyszukiwania, szczegóły wyników dla każdego badania oraz statystyki podsumowujące, oparte na danych wyjściowych z `SearchResult` (`domain/models/search_result.py`). Implementacja unika konstrukcji `if-elif-else`, stosując podejście deklaratywne z wykorzystaniem słowników, list i stałych, co zapewnia spójność, czytelność i zgodność z zasadami Clean Code, SOLID (szczególnie SRP), DRY oraz SRP. Moduł jest wywoływany z `main.py`, aby zachować czystość głównego punktu wejścia aplikacji i umożliwić ponowne użycie logiki raportowania.

**Logika implementacji**:
- **Stałe**:
  - `EMOJI`: Słownik mapujący sekcje raportu na emotikony dla lepszej wizualizacji:
    ```python
    EMOJI = {
        "CONFIG": "🔧",
        "THRESHOLDS": "📊",
        "PARAMETERS": "⚙️",
        "STRATEGIES": "🔍",
        "API": "🌐",
        "FOUND": "✅",
        "NOT_FOUND": "🚫",
        "REJECTED": "❌",
        "SKIPPED": "⏭️",
        "SEARCH_PROCESS": "🔍",
        "METRICS": "📊",
        "STRATEGY_FLOW": "⚙️",
        "SUGGESTIONS": "💡",
        "SUMMARY": "📈"
    }
    ```
  - `STRATEGY_NAMES`: Słownik mapujący wartości `SearchStrategyType` na czytelne nazwy w raporcie:
    ```python
    STRATEGY_NAMES = {
        SearchStrategyType.DOI: "DOI Search",
        SearchStrategyType.PMID: "PMID Search",
        SearchStrategyType.TITLE_AUTHORS_YEAR: "Title + Authors + Year",
        SearchStrategyType.TITLE_AUTHORS: "Title + Authors",
        SearchStrategyType.TITLE_YEAR: "Title + Year",
        SearchStrategyType.TITLE_JOURNAL: "Title + Journal",
        SearchStrategyType.TITLE_ONLY: "Title Only"
    }
    ```
  - `STATUS_COLORS`: Słownik mapujący statusy `SearchStatus` na kolory w `rich`:
    ```python
    STATUS_COLORS = {
        SearchStatus.FOUND: "green",
        SearchStatus.NOT_FOUND: "yellow",
        SearchStatus.REJECTED: "red",
        SearchStatus.SKIPPED: "cyan"
    }
    ```
  - `CONFIG_FIELDS`: Lista krotek określających pola konfiguracyjne i ich etykiety:
    ```python
    CONFIG_FIELDS = [
        ("title_similarity_threshold", "Title Similarity"),
        ("author_similarity_threshold", "Author Similarity"),
        ("normalize_search_params", "Normalize Search"),
        ("author_verification", "Author Verification"),
        ("journal_verification", "Journal Verification"),
        ("disable_doi_search", "DOI Search"),
        ("disable_pmid_search", "PMID Search"),
        ("disable_title_authors_year_search", "Title + Authors + Year"),
        ("disable_title_authors_search", "Title + Authors"),
        ("disable_title_year_search", "Title + Year"),
        ("disable_title_journal_search", "Title + Journal"),
        ("disable_title_only_search", "Title Only"),
        ("openalex_email", "API Email"),
        ("max_retries", "Max Retries"),
        ("timeout", "Timeout"),
        ("retry_backoff_factor", "Retry Backoff"),
        ("per_page", "Results per Page")
    ]
    ```
  - `METRIC_FIELDS`: Lista krotek dla metryk podobieństwa w raporcie:
    ```python
    METRIC_FIELDS = [
        ("title_similarity", "Title Similarity"),
        ("year_match", "Year Match"),
        ("journal_match", "Journal Match")
    ]
    ```
  - `REJECTION_REASONS`: Słownik mapujący przyczyny odrzucenia na sugestie poprawy:
    ```python
    REJECTION_REASONS = {
        "low_title_similarity": "Consider lowering title similarity threshold to {value}",
        "year_mismatch": "Verify if year difference is acceptable for your use case",
        "journal_mismatch": "Check if journal names are equivalent ({original} vs {result})",
        "missing_data": "Ensure all required fields (e.g., title, authors) are provided"
    }
    ```
  - `STRATEGY_STATUS`: Słownik mapujący statusy strategii na symbole i opisy:
    ```python
    STRATEGY_STATUS = {
        "found": ("✅", "MATCH FOUND!"),
        "rejected": ("❌", "Rejected"),
        "skipped": ("⏭️", "Skipped"),
        "not_attempted": ("⏭️", "Not attempted")
    }
    ```
- **Struktura raportu**:
  - **Sekcja konfiguracji**:
    - Wyświetla progi podobieństwa (`Config.title_similarity_threshold`, `Config.author_similarity_threshold`) w panelu „Similarity Thresholds”.
    - Prezentuje parametry wyszukiwania (np. `normalize_search_params`, `author_verification`) w panelu „Search Parameters”.
    - Lista strategii wyszukiwania (z `Config.disable_*`) w panelu „Active Search Strategies”, z numeracją i statusem („Yes” dla włączonych, „No” dla wyłączonych).
    - Ustawienia API (`max_retries`, `timeout`, itp.) w panelu „API Settings”, z formatowaniem (np. „30s” dla czasu, „Not set” dla `openalex_email=None`).
  - **Sekcja wyników dla badań**:
    - Dla każdego wyniku (`SearchResult`):
      - Nagłówek z `study_id` i statusem (np. „✅ FOUND: STD-Example-2023” lub „🚫 NOT_FOUND: STD-ExcludedExample-2023”), pokolorowany zgodnie z `STATUS_COLORS`.
      - Dane publikacji (dla `status="found"` lub `"rejected"`): `openalex_id`, `pdf_url` („Not available” jeśli `None`), `title`, `journal`, `year`, `doi`, `open_access`, `citation_count`.
      - Proces wyszukiwania (dla `found`): szczegóły z `search_details` (`strategy`, `query_type`, `search_term`).
      - Proces wyszukiwania (dla `not_found` lub `rejected`): szczegóły z `search_attempts` (`strategy`, `query_type`, `search_term`) oraz `original_reference` (`title`, `year`, `journal`).
      - Przepływ strategii: tabela z wszystkimi strategiami (`STRATEGY_NAMES`), ich statusami (np. „✅ MATCH FOUND!” dla `found`, „⏭️ Skipped” dla pominiętych).
      - Sugestie poprawy (dla `rejected` lub `not_found`): generowane na podstawie przyczyn odrzucenia, np. „Ensure all required fields are provided” dla braku danych.
  - **Sekcja statystyk**:
    - Liczba przetworzonych badań (`summary.total`).
    - Wskaźnik sukcesu (`summary.found_percent`).
    - Liczba badań w każdym statusie (`found`, `rejected`, `not_found`, `skipped`).
    - Statystyki publikacji: liczba z `pdf_url` (`with_pdf_url`), `open_access`, `with_doi`.
    - Czas przetwarzania (obliczony od startu do końca, w sekundach).
- **Logika generowania**:
  - **Klasa `ReportFormatter`**:
    - Inicjalizuje `rich.console.Console` dla renderowania raportu.
    - Przechowuje `Config`, listę `SearchResult` oraz czas startu dla pomiaru wydajności.
    - Metoda `generate_report()`:
      - Tworzy panel konfiguracyjny (`rich.panel.Panel`), iterując po `CONFIG_FIELDS` za pomocą list comprehension.
      - Generuje sekcje wyników, formatując dane za pomocą `rich.table.Table` dla przepływu strategii i szczegółów wyszukiwania.
      - Oblicza statystyki, używając `collections.Counter` dla statusów i zliczania `with_pdf_url`, `open_access`, `with_doi`.
      - Dodaje sugestie poprawy, mapując przyczyny z `REJECTION_REASONS` na podstawie `search_attempts` lub `original_reference`.
    - Metoda `render()`: Wyświetla raport w terminalu.
  - **Unikanie `if-elif-else`**:
    - Używa słowników (`STATUS_COLORS`, `REJECTION_REASONS`, `STRATEGY_STATUS`) do mapowania wartości na formatowane teksty.
    - Iteruje po zdefiniowanych polach (`CONFIG_FIELDS`) zamiast warunkowego wyboru.
    - Statusy strategii są obsługiwane przez `STRATEGY_STATUS`, co eliminuje potrzebę rozgałęzień.
  - **Obliczanie statystyk**:
    - Liczy statusy: `Counter([result.status for result in results])`.
    - Zlicza `with_pdf_url`: `sum(1 for result in results if result.pdf_url)`.
    - Zlicza `open_access` i `with_doi` analogicznie.
    - Mierzy czas: `time.perf_counter() - start_time`.
  - **Sugestie poprawy**:
    - Dla `not_found`: Sugeruje zapewnienie wymaganych pól (np. „Ensure title is provided”).
    - Dla `rejected`: Mapuje przyczyny odrzucenia (np. „low_title_similarity” → „Lower title similarity threshold”).
- **Scenariusze**:
  - **Sukces – pełny raport**:
    - Dane z JSON wyjściowego (np. jedno `found`, jedno `not_found`) → raport pokazuje konfigurację, szczegóły badań i statystyki.
  - **Sukces – tylko `found`**:
    - Wszystkie badania mają status `"found"` → raport pomija sugestie poprawy.
  - **Sukces – tylko `not_found`**:
    - Wszystkie badania z `not_found` → raport zawiera sugestie dla każdego badania.
  - **Sukces – puste wyniki**:
    - Brak wyników → raport pokazuje konfigurację i zerowe statystyki.
  - **Przypadek brzegowy – brak konfiguracji**:
    - Domyślna konfiguracja → raport wyświetla domyślne wartości (np. `title_similarity_threshold=0.7`).
  - **Przypadek brzegowy – uszkodzony wynik**:
    - Brak `study_id` → pomija rekord, loguje ostrzeżenie.
  - **Przypadek brzegowy – długie tytuły**:
    - Tytuł > 100 znaków → obcina z „...” dla czytelności.
  - **Przypadek brzegowy – brak `search_details`**:
    - Dla `found` bez `search_details` → wyświetla tylko podstawowe dane publikacji.

**Zależności**:
- **`rich`**: Renderowanie raportu (panele, tabele, kolory).
- **`domain/models/config.py`**: Konfiguracja wyszukiwania.
- **`domain/models/search_result.py`**: Wyniki wyszukiwania.
- **`domain/enums/search_strategy_type.py`**: Strategie wyszukiwania.
- **`domain/enums/search_status.py`**: Statusy wyników.
- **`time`**: Pomiar czasu przetwarzania.
- **`collections`**: Agregacja statystyk (`Counter`).
- **`loguru`**: Logowanie ostrzeżeń.
- **`src/utils/dict_helpers.py`**: Funkcja `add_optional_field` do formatowania danych.

**Testy (TDD)**:
- **Test konfiguracji**:
  - Dane: `Config(title_similarity_threshold=0.9, author_similarity_threshold=0.85)`.
    - Oczekiwany wynik: Sekcja „📊 Similarity Thresholds” z „Title Similarity: 0.90”, „Author Similarity: 0.85”.
  - Dane: Domyślna konfiguracja → raport pokazuje wartości domyślne (np. `max_retries=3`).
- **Test wyniku `found`**:
  - Dane: `SearchResult(study_id="STD-Example-2023", status=SearchStatus.FOUND, strategy=SearchStrategyType.DOI, openalex_id="https://openalex.org/W1234567890", title="Example study title", search_details={"query_type": "doi filter", "search_term": "10.1234/example.2023"})`.
    - Oczekiwany wynik: Sekcja „✅ FOUND: STD-Example-2023” z „OpenAlex ID: https://openalex.org/W1234567890”, „Strategy Flow” pokazująca „✅ MATCH FOUND!” dla `DOI Search`.
- **Test wyniku `not_found`**:
  - Dane: `SearchResult(study_id="STD-ExcludedExample-2023", status=SearchStatus.NOT_FOUND, search_attempts=[{"strategy": "title_only", "query_type": "title.search only", "search_term": "excluded study title"}], original_reference={"title": "Excluded study title", "year": 2022})`.
    - Oczekiwany wynik: Sekcja „🚫 NOT_FOUND: STD-ExcludedExample-2023” z „Search Term: 'excluded study title'”, sugestia „Ensure all required fields are provided”.
- **Test statystyk**:
  - Dane: JSON wyjściowy z `found=1`, `not_found=1`, `total=2`, `found_percent=50.0`.
    - Oczekiwany wynik: Sekcja „📈 Summary Statistics” z „Total Studies Processed: 2”, „Success Rate: 50%”, „Found: 1”, „Not Found: 1”.
  - Dane: Pusta lista wyników → „Total Studies Processed: 0”, „Success Rate: 0%”.
- **Test przypadków brzegowych**:
  - Dane: Brak `openalex_id` w `found` → wyświetla „Not available”.
  - Dane: Długi tytuł → obcina w raporcie z „...”.
  - Dane: Brak `search_attempts` w `not_found` → pomija sekcję procesu wyszukiwania.
- **Uwagi**:
  - Testy mockują `rich.console.Console` za pomocą `rich.testing.Console`, aby przechwycić wyjście terminala.
  - Testy weryfikują formatowanie (kolory, emotikony, tabele) i poprawność statystyk.
  - Testy integracyjne używają fixtures zgodnych z JSON-em wyjściowym.

**Oczekiwany rezultat w terminalu** (przykład dla JSON wyjściowego):
```
🔧 OpenAlex Search Configuration
----------------------------
📊 Similarity Thresholds:
• Title Similarity: 0.70
• Author Similarity: 0.80

⚙️ Search Parameters:
• Normalize Search: True
• Author Verification: True
• Journal Verification: True

🔍 Active Search Strategies:
1. DOI Search: Yes
2. PMID Search: Yes
3. Title + Authors + Year: Yes
4. Title + Authors: Yes
5. Title + Year: Yes
6. Title + Journal: Yes
7. Title Only: Yes

🌐 API Settings:
• API Email: Not set
• Max Retries: 3
• Timeout: 30s
• Retry Backoff: 0.1
• Results per Page: 25

✅ FOUND: STD-Example-2023
Status: found (via doi)
OpenAlex ID: https://openalex.org/W1234567890
PDF URL: https://example.com/paper.pdf
Title: Example study title
Journal: Journal of Examples
Year: 2023
DOI: https://doi.org/10.1234/example.2023
Open Access: True
Citations: 5

🔍 Search Process:
Strategy: doi
Query Type: doi filter
Search Term: '10.1234/example.2023'

⚙️ Strategy Flow:
DOI Search          ✅  MATCH FOUND!
PMID Search         ⏭️  Not attempted (match already found)
Title + Authors + Y ⏭️  Not attempted (match already found)
Title + Authors     ⏭️  Not attempted (match already found)
Title + Year        ⏭️  Not attempted (match already found)
Title + Journal     ⏭️  Not attempted (match already found)
Title Only          ⏭️  Not attempted (match already found)

🚫 NOT_FOUND: STD-ExcludedExample-2023
Status: not_found
Original Reference:
Title: Excluded study title
Journal: Journal of Non-Examples
Year: 2022

🔍 Search Process:
Strategy: title_only
Query Type: title.search only
Search Term: 'excluded study title'

⚙️ Strategy Flow:
DOI Search          ⏭️  Skipped (no DOI provided)
PMID Search         ⏭️  Skipped (no PMID provided)
Title + Authors + Y ⏭️  Skipped (authors not provided)
Title + Authors     ⏭️  Skipped (authors not provided)
Title + Year        ⏭️  Skipped (year not matched)
Title + Journal     ⏭️  Skipped (journal not matched)
Title Only          🚫  No match found

💡 Improvement Suggestions:
• Ensure all required fields (e.g., DOI, PMID, authors) are provided to enable more search strategies

📈 Summary Statistics:
Total Studies Processed: 2
Success Rate: 50%
Found: 1
Not Found: 1
Rejected: 0
Skipped: 0
With PDF URL: 1
Open Access: 1
With DOI: 1
Processing Time: [czas, np. 1.2s]
```

---

## Lista opcji konfiguracyjnych używanych w aplikacji

Opcje konfiguracyjne są zdefiniowane w klasie `Config` (`domain/models/config.py`) i jej zagnieżdżonych podklasach (`OpenAlexConfig`, `SearchConfig`, `OutputConfig`, `ExecutionSettings`, `DataHandlingSettings`). Poniżej przedstawiono wszystkie opcje, ich przeznaczenie, domyślne wartości oraz odpowiadające zmienne środowiskowe.

### 1. Opcje w `OpenAlexConfig`
Te opcje konfigurują interakcje z API OpenAlex, w tym ustawienia zapytań i ponawiania.

| **Opcja**                  | **Opis**                                                                 | **Domyślna wartość** | **Zmienna środowiskowa**         | **Przykładowa wartość**          |
|----------------------------|--------------------------------------------------------------------------|----------------------|----------------------------------|----------------------------------|
| `email`                    | E-mail używany do „polite pool” w API OpenAlex dla szybszych odpowiedzi. | `None`               | `OPENALEX_EMAIL`                 | `user@example.com`               |
| `max_retries`              | Maksymalna liczba ponowień zapytania w przypadku błędu API.              | `3`                  | `OPENALEX_MAX_RETRIES`           | `5`                              |
| `retry_backoff_factor`     | Współczynnik opóźnienia między ponowieniami zapytań (w sekundach).       | `0.1`                | `OPENALEX_RETRY_BACKOFF_FACTOR`  | `0.5`                            |
| `retry_http_codes`         | Kody HTTP, które wyzwalają ponowienie zapytania (np. 429, 500, 503).     | `[429, 500, 503]`    | `OPENALEX_RETRY_HTTP_CODES`      | `429,502,504`                    |
| `per_page`                 | Liczba wyników zwracanych na stronę w zapytaniach paginowanych.          | `25`                 | `OPENALEX_PER_PAGE`              | `100`                            |

**Uwagi**:
- `email` jest opcjonalny, ale jego ustawienie zwiększa wydajność zapytań dzięki dostępowi do „polite pool” w `pyalex`.
- `retry_http_codes` w zmiennej środowiskowej to lista oddzielona przecinkami.

### 2. Opcje w `SearchConfig`
Te opcje kontrolują zachowanie strategii wyszukiwania i weryfikację wyników.

| **Opcja**                              | **Opis**                                                                                   | **Domyślna wartość** | **Zmienna środowiskowa**                     | **Przykładowa wartość** |
|----------------------------------------|--------------------------------------------------------------------------------------------|----------------------|----------------------------------------------|-------------------------|
| `thresholds.title`                     | Próg podobieństwa dla tytułów (wartość od 0 do 1).                                          | `0.7`                | `TITLE_SIMILARITY_THRESHOLD`                 | `0.9`                   |
| `thresholds.author`                    | Próg podobieństwa dla autorów (wartość od 0 do 1).                                          | `0.8`                | `AUTHOR_SIMILARITY_THRESHOLD`                | `0.85`                  |
| `verification.normalize_search_params` | Czy normalizować parametry wyszukiwania (np. usuwanie znaków specjalnych).                 | `True`               | `NORMALIZE_SEARCH_PARAMS`                    | `False`                 |
| `verification.author_verification`     | Czy weryfikować zgodność autorów w wynikach wyszukiwania.                                   | `True`               | `AUTHOR_VERIFICATION`                        | `False`                 |
| `verification.journal_verification`    | Czy weryfikować zgodność czasopisma w wynikach wyszukiwania.                                | `True`               | `JOURNAL_VERIFICATION`                       | `False`                 |
| `disable_strategies.doi_search`        | Czy wyłączyć strategię wyszukiwania po DOI.                                                | `False`              | `DISABLE_DOI_SEARCH`                         | `True`                  |
| `disable_strategies.pmid_search`       | Czy wyłączyć strategię wyszukiwania po PMID.                                               | `False`              | `DISABLE_PMID_SEARCH`                        | `True`                  |
| `disable_strategies.title_authors_year_search` | Czy wyłączyć strategię wyszukiwania po tytule, autorach i roku.                    | `False`              | `DISABLE_TITLE_AUTHORS_YEAR_SEARCH`          | `True`                  |
| `disable_strategies.title_authors_search`      | Czy wyłączyć strategię wyszukiwania po tytule i autorach.                          | `False`              | `DISABLE_TITLE_AUTHORS_SEARCH`               | `True`                  |
| `disable_strategies.title_year_search`         | Czy wyłączyć strategię wyszukiwania po tytule i roku.                              | `False`              | `DISABLE_TITLE_YEAR_SEARCH`                  | `True`                  |
| `disable_strategies.title_journal_search`      | Czy wyłączyć strategię wyszukiwania po tytule i czasopiśmie.                       | `False`              | `DISABLE_TITLE_JOURNAL_SEARCH`               | `True`                  |
| `disable_strategies.title_only_search`         | Czy wyłączyć strategię wyszukiwania tylko po tytule.                               | `False`              | `DISABLE_TITLE_ONLY_SEARCH`                  | `True`                  |

**Uwagi**:
- Wartości boolean (`True`/`False`) w zmiennych środowiskowych mogą być reprezentowane jako „true”/„false” lub „1”/„0”.
- Progi podobieństwa (`thresholds.title`, `thresholds.author`) są kluczowe dla strategii opartych na tytule i autorach, wpływając na precyzję dopasowań.

### 3. Opcje w `OutputConfig`
Te opcje kontrolują sposób zapisu i logowania wyników.

| **Opcja**         | **Opis**                                                                 | **Domyślna wartość** | **Zmienna środowiskowa**    | **Przykładowa wartość**       |
|-------------------|--------------------------------------------------------------------------|----------------------|-----------------------------|-------------------------------|
| `output_dir`      | Katalog zapisu plików wyjściowych (JSON).                                | `"./results"`        | `OUTPUT_DIR`                | `/path/to/output`             |
| `pattern`         | Wzór dla plików wyjściowych (np. tylko JSON).                            | `"*.json"`           | `OUTPUT_PATTERN`            | `*.jsonl`                     |
| `log_file`        | Plik do zapisu logów (opcjonalny).                                       | `None`               | `LOG_FILE`                  | `/logs/app.log`               |
| `log_level`       | Poziom logowania (np. „info”, „debug”).                                  | `"info"`             | `LOG_LEVEL`                 | `debug`                       |
| `limit`           | Maksymalna liczba badań do przetworzenia (opcjonalna).                   | `None`               | `OUTPUT_LIMIT`              | `100`                         |
| `mark_done`       | Czy oznaczać pliki wejściowe jako przetworzone.                          | `False`              | `MARK_DONE`                 | `True`                        |

**Uwagi**:
- `log_file=None` oznacza logowanie tylko do konsoli.
- `limit=None` oznacza brak ograniczenia liczby przetwarzanych badań.

### 4. Opcje w `ExecutionSettings`
Te opcje określają parametry wykonywania aplikacji.

| **Opcja**       | **Opis**                                                                 | **Domyślna wartość** | **Zmienna środowiskowa** | **Przykładowa wartość** |
|-----------------|--------------------------------------------------------------------------|----------------------|--------------------------|-------------------------|
| `concurrency`   | Liczba równoległych zadań (np. zapytań API).                             | `20`                 | `CONCURRENCY`            | `50`                    |
| `timeout`       | Limit czasu na jedno zapytanie API (w sekundach).                        | `30`                 | `TIMEOUT`                | `60`                    |
| `progress`      | Czy wyświetlać pasek postępu w terminalu.                                | `False`              | `SHOW_PROGRESS`          | `True`                  |
| `quiet`         | Czy ograniczyć wyjście konsolowe (tylko błędy).                          | `False`              | `QUIET_MODE`             | `True`                  |
| `strict`        | Czy stosować ścisłą weryfikację (przerywać przy błędach).                | `False`              | `STRICT_MODE`            | `True`                  |

**Uwagi**:
- `concurrency` wpływa na wydajność, ale zbyt wysoka wartość może przekroczyć limity API OpenAlex.
- `timeout` dotyczy pojedynczych zapytań HTTP w `pyalex`.

### 5. Opcje w `DataHandlingSettings`
Te opcje kontrolują przetwarzanie danych wejściowych i wyjściowych.

| **Opcja**              | **Opis**                                                                 | **Domyślna wartość** | **Zmienna środowiskowa**    | **Przykładowa wartość** |
|------------------------|--------------------------------------------------------------------------|----------------------|-----------------------------|-------------------------|
| `include_excluded`     | Czy przetwarzać badania wykluczone (`excluded` w JSON).                  | `False`              | `INCLUDE_EXCLUDED`          | `True`                  |
| `dry_run`              | Czy symulować przetwarzanie bez zapisu wyników.                          | `False`              | `DRY_RUN`                   | `True`                  |
| `download`             | Czy pobierać pełne publikacje (np. PDF, jeśli dostępne).                 | `False`              | `DOWNLOAD_PUBLICATIONS`     | `True`                  |
| `overwrite`            | Czy nadpisywać istniejące pliki wyjściowe.                               | `False`              | `OVERWRITE_OUTPUT`          | `True`                  |
| `allow_missing_year`   | Czy zezwalać na brak roku w referencji podczas wyszukiwania.             | `False`              | `ALLOW_MISSING_YEAR`        | `True`                  |

**Uwagi**:
- `download` jest obecnie nieużywane w systemie, ale zachowane dla przyszłych rozszerzeń (np. pobieranie PDF).
- `allow_missing_year` wpływa na metodę `Reference.has_minimal_data`.

### 6. Opcje nadrzędne w `Config`
Opcje na najwyższym poziomie klasy `Config`, synchronizujące ustawienia z podklasami.

| **Opcja**   | **Opis**                                                                 | **Domyślna wartość** | **Zmienna środowiskowa** | **Przykładowa wartość** |
|-------------|--------------------------------------------------------------------------|----------------------|--------------------------|-------------------------|
| `email`     | E-mail nadrzędny, synchronizowany z `OpenAlexConfig.email`, jeśli podany. | `None`               | `EMAIL`                  | `user@example.com`      |

**Uwagi**:
- Jeśli `email` jest ustawiony w `Config`, nadpisuje `OpenAlexConfig.email`, zapewniając spójność.

---

## Zmienne środowiskowe i przykładowe wartości

Aplikacja ładuje konfigurację z zmiennych środowiskowych w metodzie `Config.from_env()` (lub odpowiednich metodach w podklasach, np. `OpenAlexConfig.from_dict`). Poniżej pełna lista zmiennych środowiskowych z przykładami wartości, które można ustawić np. w pliku `.env` lub w systemie operacyjnym.

### Przykład pliku `.env` oraz szablonu `.env.example`
```bash
OPENALEX_EMAIL=user@example.com
OPENALEX_MAX_RETRIES=5
OPENALEX_RETRY_BACKOFF_FACTOR=0.5
OPENALEX_RETRY_HTTP_CODES=429,502,504
OPENALEX_PER_PAGE=100

TITLE_SIMILARITY_THRESHOLD=0.9
AUTHOR_SIMILARITY_THRESHOLD=0.85
NORMALIZE_SEARCH_PARAMS=False
AUTHOR_VERIFICATION=False
JOURNAL_VERIFICATION=False
INCLUDE_EXCLUDED=True
DISABLE_DOI_SEARCH=False
DISABLE_PMID_SEARCH=False
DISABLE_TITLE_AUTHORS_YEAR_SEARCH=False
DISABLE_TITLE_AUTHORS_SEARCH=False
DISABLE_TITLE_YEAR_SEARCH=False
DISABLE_TITLE_JOURNAL_SEARCH=False
DISABLE_TITLE_ONLY_SEARCH=False

OUTPUT_DIR=/path/to/output
OUTPUT_PATTERN=*.jsonl
LOG_FILE=/logs/app.log
LOG_LEVEL=debug
OUTPUT_LIMIT=100
MARK_DONE=True

CONCURRENCY=50
TIMEOUT=60
SHOW_PROGRESS=True
QUIET_MODE=False
STRICT_MODE=True

DOWNLOAD_PUBLICATIONS=True
OVERWRITE_OUTPUT=True
ALLOW_MISSING_YEAR=True

EMAIL=user@example.com
```

### Wyjaśnienie zmiennych środowiskowych
- **Format boolean**: Wartości takie jak `True`/`False` w zmiennych środowiskowych mogą być zapisywane jako „true”/„false”, „1”/„0” lub „yes”/„no”. Parser w `Config.from_env()` konwertuje je na wartości Pythona.
- **Listy**: Wartości takie jak `OPENALEX_RETRY_HTTP_CODES` są zapisywane jako ciągi oddzielone przecinkami (np. „429,500,503”).
- **Liczby**: Wartości liczbowe (np. `OPENALEX_MAX_RETRIES`, `TITLE_SIMILARITY_THRESHOLD`) są konwertowane na `int` lub `float`. Niepoprawne wartości (np. „abc” dla `max_retries`) powodują użycie wartości domyślnej.
- **Opcjonalne**: Zmienne takie jak `OPENALEX_EMAIL` czy `LOG_FILE` mogą być nieustawione, co skutkuje wartością `None`.
- **Synchronizacja**: Zmienna `EMAIL` jest nadrzędna i synchronizuje się z `OPENALEX_EMAIL`, jeśli oba są ustawione, `EMAIL` ma priorytet.

---

## Uwagi ogólne
- **Źródło konfiguracji**: Opcje są wczytywane z zmiennych środowiskowych w metodzie `Config.from_env()` lub z pliku konfiguracyjnego, jeśli zdefiniowany. Priorytet to zmienne środowiskowe > wartości domyślne.
- **Walidacja**: Klasa `Config` zawiera metodę `validate()`, która sprawdza poprawność wartości (np. `title_similarity_threshold` w zakresie [0, 1], `concurrency` dodatnie).
- **Wpływ na system**:
  - Opcje `OpenAlexConfig` (`email`, `max_retries`) bezpośrednio wpływają na wydajność i niezawodność zapytań API OpenAlex.
  - Opcje `SearchConfig` (`thresholds`, `disable_strategies`) określają precyzję i zakres wyszukiwania.
  - Opcje `OutputConfig` i `ExecutionSettings` kontrolują interakcję z użytkownikiem i wydajność.
  - Opcje `DataHandlingSettings` umożliwiają elastyczne przetwarzanie danych.
- **Brakujące zmienne środowiskowe**: Jeśli zmienna środowiskowa nie jest ustawiona, aplikacja używa wartości domyślnej zdefiniowanej w modelu `Config`.
- **Testowanie konfiguracji**: Testy TDD powinny obejmować scenariusze z różnymi wartościami zmiennych środowiskowych, w tym brakujące zmienne, niepoprawne typy (np. „abc” dla `max_retries`) oraz przypadki brzegowe (np. `per_page=0`).

**Podsumowanie**:
Lista obejmuje wszystkie opcje konfiguracyjne z `domain/models/config.py`, które kontrolują zachowanie aplikacji, od interakcji z API OpenAlex po generowanie raportów. Każda opcja ma odpowiadającą zmienną środowiskową, co pozwala na elastyczne dostosowanie systemu bez modyfikacji kodu. Przykłady wartości pokazują, jak można skonfigurować aplikację w różnych scenariuszach, a uwagi dotyczące walidacji i testowania zapewniają niezawodność konfiguracji.
---

## Przepływ danych w systemie

Przepływ danych ilustruje, jak system przetwarza wejściowy JSON, wykonuje zapytania do OpenAlex, generuje wyniki wyszukiwania, zapisuje je do pliku wyjściowego JSON oraz wyświetla elegancki raport podsumowania w terminalu. Wszystkie pliki projektu są zaangażowane, co potwierdza brak zbędnych elementów i optymalną strukturę.

1. **Uruchomienie aplikacji** (`main.py`):
    - **Krok**: Wczytuje konfigurację z zmiennych środowiskowych za pomocą `Config.from_env()` (`domain/models/config.py`).
        - Scenariusz: Poprawna konfiguracja → obiekt `Config` z wartościami (np. `title_similarity_threshold=0.9`, `openalex_email="user@example.com"`).
        - Scenariusz: Brak zmiennych → domyślne wartości (np. `max_retries=3`, `per_page=25`).
        - Scenariusz: Niepoprawne wartości → używa domyślnych, loguje ostrzeżenie.
    - **Krok**: Otwiera plik wejściowy `input.json` i deserializuje go do słownika za pomocą `orjson`.
        - Scenariusz: Poprawny JSON → słownik z kluczami `studies.included` i `studies.excluded`.
        - Scenariusz: Brak pliku → rzuca `FileNotFoundError`, aplikacja kończy działanie.
        - Scenariusz: Niepoprawny JSON → rzuca `JSONDecodeError`, aplikacja kończy działanie.
    - **Krok**: Mapuje dane JSON na obiekty `Study` (`domain/models/study.py`):
        - Dla każdego badania w `studies.included`:
            - Tworzy obiekt `Study` z `StudyType.INCLUDED` (`domain/enums/study_type.py`).
            - Deserializuje pole `reference` na obiekt `Reference` (`domain/models/reference.py`) z polami `title`, `year`, `authors`, `journal`, `doi`, `pmid`.
        - Dla każdego badania w `studies.excluded`:
            - Tworzy `Study` z `StudyType.EXCLUDED` i `exclusion_reason`.
            - Deserializuje `reference` jak powyżej.
        - Scenariusz: Pełne dane → lista obiektów `Study` z poprawnymi polami.
        - Scenariusz: Brakujące pola → ustawia `None` dla pól takich jak `doi`, `pmid`.
        - Scenariusz: Uszkodzony JSON (np. brak `study_id`) → ustawia domyślne wartości (np. pusty string), loguje ostrzeżenie.
    - **Krok**: Rejestruje czas rozpoczęcia przetwarzania dla późniejszego obliczenia czasu w raporcie podsumowania.

2. **Inicjalizacja usługi dopasowywania** (`application/services/matching_service.py`):
    - **Krok**: Tworzy instancję `OpenAlexRepository` (`infrastructure/repositories/openalex_repository.py`).
        - Scenariusz: Poprawna inicjalizacja → repozytorium gotowe do zapytań API OpenAlex.
        - Scenariusz: Błąd konfiguracji (np. niepoprawny `openalex_email`) → używa domyślnych ustawień `pyalex`.
    - **Krok**: Inicjalizuje strategie wyszukiwania (`domain/strategies/*_strategy.py`):
        - Tworzy obiekty dla wszystkich strategii: `DoiStrategy`, `PmidStrategy`, `TitleAuthorsYearStrategy`, `TitleAuthorsStrategy`, `TitleYearStrategy`, `TitleJournalStrategy`, `TitleOnlyStrategy`.
        - Filtruje strategie wyłączone w `Config.disable_strategies` (np. `disable_doi_search=True` pomija `DoiStrategy`).
        - Sortuje strategie według priorytetu zdefiniowanego w `SearchStrategyType.priority` (`domain/enums/search_strategy_type.py`).
        - Scenariusz: Domyślna konfiguracja → wszystkie strategie w kolejności priorytetów (DOI: 1, PMID: 2, ..., Title Only: 7).
        - Scenariusz: Wyłączona strategia (np. `disable_doi_search=True`) → pomija `DoiStrategy`.
        - Scenariusz: Brak włączonych strategii → loguje ostrzeżenie, kontynuuje z pustą listą.

3. **Dopasowywanie badań** (`application/services/matching_service.py`):
    - **Krok**: Dla każdego obiektu `Study` wywołuje metodę `match_study`:
        - Sprawdza minimalne dane za pomocą `Reference.has_minimal_data(allow_missing_year=Config.allow_missing_year)` (`domain/models/reference.py`).
            - Scenariusz: Tytuł lub DOI/PMID dostępne → przechodzi do strategii.
            - Scenariusz: Brak minimalnych danych → tworzy `SearchResult` z `status=SearchStatus.SKIPPED` (`domain/enums/search_status.py`) i pomija strategie.
        - Iteruje po strategiach w kolejności priorytetów:
            - **Strategia DOI** (`doi_strategy.py`):
                - Sprawdza `supported(reference)` → wymaga niepustego `reference.doi`.
                - Normalizuje DOI za pomocą `BaseStrategy.normalize_text` (`domain/strategies/base_strategy.py`).
                - Wywołuje `OpenAlexRepository.get_by_doi`.
                - Weryfikuje unikalność wyniku.
                - Scenariusz: Znaleziono publikację → zapisuje `[publication_data]` w `SearchResult.publication_data` i przerywa iterację.
                - Scenariusz: Brak wyniku → przechodzi do następnej strategii.
                - Scenariusz: Błąd API → zapisuje próbę z błędem w `SearchResult.search_attempts`.
            - **Strategia PMID** (`pmid_strategy.py`):
                - Analogicznie do DOI, dla `reference.pmid`.
            - **Strategia TITLE_AUTHORS_YEAR** (`title_authors_year_strategy.py`):
                - Sprawdza `title`, `authors`, `year`.
                - Normalizuje dane (`BaseStrategy.normalize_text`).
                - Generuje kombinacje autorów (np. „Adam U” → „adam u”, „a u”, „u adam”), uwzględniając inicjały i odwróconą kolejność.
                - Wywołuje `OpenAlexRepository.search_by_title_authors_year` z wszystkimi wariantami autorów.
                - Weryfikuje podobieństwo tytułu i autorów za pomocą `rapidfuzz` (`Config.title_similarity_threshold`, `Config.author_similarity_threshold`).
                - Scenariusz: Wysokie podobieństwo → zapisuje wynik.
                - Scenariusz: Niski próg → zapisuje próbę z błędem „Low similarity” w `search_attempts`.
            - **Pozostałe strategie** (`title_authors_strategy.py`, `title_year_strategy.py`, `title_journal_strategy.py`, `title_only_strategy.py`):
                - Analogiczne procesy dla odpowiednich pól (`title`, `authors`, `year`, `journal`).
                - W strategiach z tytułem (`TITLE_*`) stosują `rapidfuzz` dla podobieństwa tytułu.
                - Strategie z autorami (`TITLE_AUTHORS*`) uwzględniają kombinacje nazw.
            - Zapisuje każdą próbę w `SearchResult.search_attempts` z szczegółami (`strategy`, `query_type`, `search_term`).
        - Po iteracji:
            - Scenariusz: Znaleziono wynik → ustala `status=FOUND`, zapisuje `publication_data` (np. `openalex_id`, `pdf_url`) i `search_details` (`query_type`, `search_term`).
            - Scenariusz: Brak wyników → ustala `status=NOT_FOUND`, zapisuje `search_attempts` i `original_reference` (`Reference.to_dict`).
            - Scenariusz: Odrzucenie z powodu niskiego podobieństwa → ustala `status=REJECTED`, zapisuje przyczynę w `search_attempts`.
        - Tworzy obiekt `SearchResult` (`domain/models/search_result.py`) z polami `study_id`, `study_type`, `status` itd.
        - Scenariusz: Pełne dane → kompletny `SearchResult`.
        - Scenariusz: Częściowe dane → wypełnia tylko dostępne pola (np. brak `pdf_url` → `None`).

4. **Zapytania do OpenAlex** (`infrastructure/repositories/openalex_repository.py`):
    - **Krok**: Dla każdej strategii wykonuje zapytanie za pomocą `pyalex`:
        - `get_by_doi`: Wykonuje `pyalex.Works().filter(doi=normalized_doi).get()` z `per_page=1`.
        - `get_by_pmid`: Wykonuje `pyalex.Works().filter(pmid=normalized_pmid).get()` z `per_page=1`.
        - `search_by_title_authors_year`: Tworzy zapytanie `pyalex.Works().search_filter(title=normalized_title).filter(authorships={"author": {"display_name": "|".join(author_combinations)}}).filter(publication_year=year).sort(relevance_score="desc")`, uwzględniając warianty autorów (np. „adam u|adam unikon|unikon adam|a unikon|a u”).
        - `search_by_title_authors`: Jak powyżej, bez filtru roku.
        - `search_by_title_year`: Wykonuje `pyalex.Works().search_filter(title=normalized_title).filter(publication_year=year).sort(relevance_score="desc")`.
        - `search_by_title_journal`: Wykonuje `pyalex.Works().search_filter(title=normalized_title).filter(primary_location={"source": {"display_name": normalized_journal}}).sort(relevance_score="desc")`.
        - `search_by_title`: Wykonuje szerokie wyszukiwanie `pyalex.Works().search_filter(title=normalized_title).sort(relevance_score="desc")`.
    - **Krok**: Normalizuje dane wejściowe za pomocą `BaseStrategy.normalize_text` przed wysłaniem zapytań.
    - **Krok**: Obsługuje odpowiedzi API:
        - Scenariusz: Sukces → zwraca dane publikacji (słownik lub lista słowników).
        - Scenariusz: Brak wyników → zwraca `None` dla `get_*` lub pustą listę dla `search_*`.
        - Scenariusz: Błąd API (np. HTTP 429) → ponawia zapytanie zgodnie z `Config.max_retries`, loguje błąd.
        - Scenariusz: Timeout → zwraca pustą listę, loguje błąd „API timeout”.
    - **Krok**: Loguje każdą próbę zapytania, zapisując znormalizowane dane, liczbę wyników i błędy.

5. **Porównanie wyników** (`application/services/matching_service.py`):
    - **Krok**: Weryfikuje wyniki zwrócone przez strategie:
        - Dla strategii `DOI` i `PMID`: Sprawdza unikalność wyniku (oczekuje pojedynczej publikacji).
        - Dla strategii `TITLE_*`: Oblicza podobieństwo tekstu za pomocą `rapidfuzz`:
            - Tytuł: Porównuje `reference.title` z `result.title` (`Config.title_similarity_threshold`).
            - Autorzy (dla `TITLE_AUTHORS*`): Porównuje wszystkie kombinacje autorów z `reference.authors` z `result.authors` (`Config.author_similarity_threshold`).
            - Rok (dla `TITLE_*_YEAR`): Sprawdza dokładną zgodność lub różnicę lat.
            - Czasopismo (dla `TITLE_JOURNAL`): Porównuje `reference.journal` z `result.journal`.
        - Scenariusz: Podobieństwo powyżej progów → akceptuje wynik, ustala `status=FOUND`.
        - Scenariusz: Podobieństwo poniżej progów → odrzuca wynik, ustala `status=REJECTED`, zapisuje przyczynę (np. „low_title_similarity”).
        - Scenariusz: Brak wyników → kontynuuje iterację lub ustala `status=NOT_FOUND`.

6. **Tworzenie wyniku** (`domain/models/search_result.py`):
    - **Krok**: Buduje obiekt `SearchResult` dla każdego badania:
        - Wypełnia pola: `study_id`, `study_type` (z `Study`), `status` (z iteracji strategii).
        - Dla `status=FOUND`:
            - Kopiuje dane publikacji z wyniku OpenAlex: `openalex_id`, `pdf_url`, `title`, `journal`, `year`, `doi`, `open_access`, `citation_count`.
            - Zapisuje `search_details` z ostatniej udanej strategii (`strategy`, `query_type`, `search_term`).
        - Dla `status=NOT_FOUND`:
            - Zapisuje `search_attempts` z listą wszystkich prób (`strategy`, `query_type`, `search_term`, `error`).
            - Zapisuje `original_reference` z `Reference.to_dict` (`title`, `year`, `journal`).
        - Dla `status=REJECTED`:
            - Zapisuje dane publikacji (jeśli dostępne) i przyczyny odrzucenia w `search_attempts`.
        - Dla `status=SKIPPED`:
            - Zapisuje minimalne dane (`study_id`, `study_type`).
        - Scenariusz: Pełne dane → kompletny `SearchResult` z wszystkimi polami.
        - Scenariusz: Częściowe dane → wypełnia tylko dostępne pola (np. brak `pdf_url` → `None`).
        - Scenariusz: Błąd w danych → loguje ostrzeżenie, ustala minimalne pola.

7. **Zapis wyników do pliku JSON** (`main.py`):
    - **Krok**: Grupuje wyniki w listy `included` i `excluded`:
        - Iteruje po obiektach `SearchResult`, dzieląc je na podstawie `study_type` (`StudyType.INCLUDED` lub `StudyType.EXCLUDED`).
        - Scenariusz: Poprawna lista wyników → tworzy dwie listy zgodne z JSON-em wyjściowym.
        - Scenariusz: Brak wyników → tworzy puste listy.
    - **Krok**: Tworzy sekcję `summary`:
        - Liczy statystyki: `total` (liczba `SearchResult`), `found`, `rejected`, `not_found`, `skipped` (za pomocą `Counter`).
        - Oblicza procenty: `found_percent = found/total*100`, analogicznie dla innych statusów.
        - Zlicza atrybuty publikacji: `with_pdf_url` (liczba wyników z niepustym `pdf_url`), `open_access` (liczba `True`), `with_doi` (liczba z niepustym `doi`).
        - Scenariusz: Pełne dane → dokładne statystyki (np. `found_percent=50.0` dla 1/2 wyników `found`).
        - Scenariusz: Brak wyników → zerowe statystyki (`total=0`).
    - **Krok**: Serializuje wyniki do pliku `output.json` za pomocą `orjson`:
        - Tworzy strukturę JSON: `{included: [...], excluded: [...], summary: {...}}`.
        - Używa `SearchResult.to_dict()` z `utils/dict_helpers.add_optional_field` do formatowania pól.
        - Scenariusz: Poprawny zapis → plik `output.json` zgodny z przykładem wyjściowym.
        - Scenariusz: Błąd zapisu (np. brak uprawnień) → rzuca wyjątek, loguje błąd.

8. **Generowanie raportu podsumowania** (`utils/report_formatter.py`):
    - **Krok**: Tworzy instancję `ReportFormatter` z `Config`, listą `SearchResult` i czasem rozpoczęcia przetwarzania:
        - Scenariusz: Poprawna konfiguracja → gotowy formatter.
        - Scenariusz: Brak wyników → formatter przygotowany do pustego raportu.
    - **Krok**: Generuje raport w terminalu za pomocą `rich.console.Console`:
        - **Sekcja konfiguracji**:
            - Wyświetla progi podobieństwa (`title_similarity_threshold`, `author_similarity_threshold`) w panelu „Similarity Thresholds”.
            - Prezentuje parametry wyszukiwania (`normalize_search_params`, `author_verification`, `journal_verification`) w panelu „Search Parameters”.
            - Lista strategii z `disable_*` w panelu „Active Search Strategies” („Yes” dla włączonych, „No” dla wyłączonych).
            - Ustawienia API (`openalex_email`, `max_retries`, itp.) w panelu „API Settings”.
        - **Sekcja wyników**:
            - Dla każdego `SearchResult`:
                - Nagłówek z `study_id` i statusem (np. „✅ FOUND: STD-Example-2023”), pokolorowany (`green` dla `found`, `yellow` dla `not_found`).
                - Dane publikacji (dla `found`): `openalex_id`, `pdf_url` („Not available” jeśli `None`), `title`, `journal`, `year`, `doi`, `open_access`, `citation_count`.
                - Proces wyszukiwania:
                    - Dla `found`: Wyświetla `search_details` (`strategy`, `query_type`, `search_term`).
                    - Dla `not_found`: Wyświetla `search_attempts` (`strategy`, `query_type`, `search_term`) i `original_reference` (`title`, `year`, `journal`).
                - Przepływ strategii: Tabela z nazwami strategii (`STRATEGY_NAMES`) i statusami („✅ MATCH FOUND!”, „⏭️ Skipped”, „🚫 No match found”).
                - Sugestie poprawy (dla `not_found`): Np. „Ensure all required fields are provided”.
        - **Sekcja statystyk**:
            - Wyświetla `summary.total`, `found`, `not_found`, `rejected`, `skipped`.
            - Pokazuje procenty: `found_percent`, `not_found_percent`, itp.
            - Zlicza `with_pdf_url`, `open_access`, `with_doi`.
            - Prezentuje czas przetwarzania (np. „1.2s”).
        - Scenariusz: Pełne dane → raport zgodny z JSON-em wyjściowym (np. „Success Rate: 50%”).
        - Scenariusz: Brak wyników → zerowe statystyki, minimalny raport.
        - Scenariusz: Uszkodzony wynik → pomija rekord, loguje ostrzeżenie.
    - **Krok**: Renderuje raport za pomocą `ReportFormatter.render()`:
        - Używa `rich.panel.Panel` dla sekcji, `rich.table.Table` dla list i `rich.text.Text` dla kolorów.
        - Scenariusz: Poprawny rendering → raport w terminalu.
        - Scenariusz: Błąd konsoli → loguje błąd, kontynuuje zapis JSON.

**Wykorzystane pliki**:
- `main.py` – Uruchamia aplikację, wczytuje dane, zapisuje JSON, wywołuje raport.
- `domain/models/config.py` – Dostarcza konfigurację (np. progi podobieństwa).
- `domain/models/study.py` – Przetwarza dane wejściowe na obiekty `Study`.
- `domain/models/reference.py` – Przetwarza referencje z JSON-a.
- `domain/models/search_result.py` – Przechowuje wyniki wyszukiwania.
- `domain/enums/study_type.py` – Definiuje typy badań (`INCLUDED`, `EXCLUDED`).
- `domain/enums/search_status.py` – Definiuje statusy (`FOUND`, `NOT_FOUND`, itp.).
- `domain/enums/search_strategy_type.py` – Definiuje strategie i priorytety.
- `application/services/matching_service.py` – Koordynuje dopasowywanie.
- `infrastructure/repositories/openalex_repository.py` – Wykonuje zapytania API.
- `domain/strategies/base_strategy.py` – Udostępnia normalizację i logowanie.
- `domain/strategies/doi_strategy.py` – Wyszukiwanie po DOI.
- `domain/strategies/pmid_strategy.py` – Wyszukiwanie po PMID.
- `domain/strategies/title_authors_year_strategy.py` – Wyszukiwanie po tytule, autorach, roku.
- `domain/strategies/title_authors_strategy.py` – Wyszukiwanie po tytule i autorach.
- `domain/strategies/title_year_strategy.py` – Wyszukiwanie po tytule i roku.
- `domain/strategies/title_journal_strategy.py` – Wyszukiwanie po tytule i czasopiśmie.
- `domain/strategies/title_only_strategy.py` – Wyszukiwanie po tytule.
- `utils/dict_helpers.py` – Formatowanie słowników w `SearchResult.to_dict`.
- `utils/report_formatter.py` – Generowanie raportu w terminalu.

**Uwagi**:
- Wszystkie pliki są zaangażowane w przepływ danych, co potwierdza brak zbędnych elementów.
- `BaseStrategy.normalize_text` zapewnia spójną normalizację danych w zapytaniach i raportach.
- `utils/dict_helpers.add_optional_field` jest używane w `SearchResult` i `ReportFormatter`, minimalizując duplikację.
- Raport w `utils/report_formatter.py` jest generowany po zapisie JSON, co oddziela zapis danych od prezentacji wyników.
- Obsługa kombinacji autorów w strategiach `TITLE_AUTHORS*` zwiększa precyzję wyszukiwania, uwzględniając inicjały i różne formaty nazw.

---


