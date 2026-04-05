# Plan wdrożenia Spec-Driven Development (SDD)

## Kontekst

Projekt to aplikacja Flask 2.3.3 + SQLite zarządzająca wynikami zawodów IPSC. Logika biznesowa jest solidna, jednak brakuje specyfikacji, testów i ujednoliconych kontraktów API. SDD wprowadzamy przyrostowo przez 6 faz.

**Zasada:** spec → test → (dopiero wtedy) kod dla każdej nowej funkcji.

---

## Proponowana struktura katalogów

```
ipsc/
├── spec/
│   ├── openapi.yaml               ← kontrakt API (spec-first)
│   ├── schemas/
│   │   ├── match.json             ← struktura data_json bloba w matches
│   │   ├── ranking.json           ← odpowiedź /api/rankings/{id}
│   │   ├── competitor.json        ← model zawodnika
│   │   ├── division.json          ← dywizja standardowa
│   │   └── error.json             ← ujednolicony format błędów
│   ├── adr/
│   │   ├── 001-sqlite-json-blobs.md
│   │   ├── 002-division-mapping.md
│   │   ├── 003-auth-strategy.md
│   │   └── 004-error-contracts.md
│   └── flows/
│       ├── ranking-calculation.md ← algorytm _prepare() krok po kroku
│       ├── cab-parsing.md         ← CAB → XML → dict
│       └── division-mapping.md    ← semantyka merge/replace
├── tests/
│   ├── conftest.py                ← factory fixture: app w trybie test + :memory: DB
│   ├── fixtures/
│   │   ├── sample_match.json      ← przykładowy data_json
│   │   └── sample_ranking.json
│   ├── test_parser.py             ← winmss_results.py
│   ├── test_api_public.py         ← /api/matches, /api/rankings
│   ├── test_api_admin.py          ← admin CRUD
│   └── test_database.py           ← apply_division_mappings, get_ranking
├── requirements-dev.txt           ← pytest, jsonschema, schemathesis, flask[testing]
└── .github/
    └── workflows/
        └── ci.yml                 ← pytest + schema lint + docker build
```

---

## Fazy

### Faza 0 — Infrastruktura *(blokuje wszystko)*

1. Wydzielić `requirements-dev.txt` z `requirements.txt`
   - Dodać: `pytest`, `jsonschema`, `schemathesis`, `flask[testing]`
2. Stworzyć `tests/conftest.py` — factory fixture tworzący aplikację Flask z `TESTING=True` i SQLite `:memory:` jako DB
3. Stworzyć szkielet katalogów: `spec/schemas/`, `spec/adr/`, `spec/flows/`, `tests/fixtures/`

---

### Faza 1 — Schematy danych JSON Schema *(równolegle z Fazą 2)*

4. `spec/schemas/match.json`
   - Udokumentować pola bloba `matches.data_json` (stages, competitors, levels)
   - Źródło: `app.py` — funkcja `_prepare()` (ok. linie 131–260)
5. `spec/schemas/ranking.json`, `competitor.json`, `division.json`
6. `spec/schemas/error.json`
   - Ujednolicony format: `{"error": string, "code": string}`
   - Dodać helper `_error_response()` w `app.py` zastępujący rozrzucone `jsonify({"error": ...})`

---

### Faza 2 — OpenAPI spec *(równolegle z Fazą 1)*

7. `spec/openapi.yaml` — spec-first dla wszystkich ~35 tras:
   - Publiczne: `/api/matches`, `/api/rankings`, `/api/translations`
   - Admin: `/admin/api/divisions-mapping`, `/admin/api/standard-divisions`, itd.
   - Error codes per endpoint
   - Referencje do schematów z Fazy 1 przez `$ref`

---

### Faza 3 — Architecture Decision Records *(można równolegle z Fazą 4)*

8. `spec/adr/001-sqlite-json-blobs.md`
   - Dlaczego JSON blob w SQLite zamiast tabel relacyjnych
   - Trade-off + zasady wersjonowania bloba
9. `spec/adr/002-division-mapping.md`
   - Semantyka mapowania dywizji: merge vs replace
   - Kolejność rozwiązywania konfliktów
10. `spec/adr/003-auth-strategy.md`
    - Legacy hash + upgrade, polityka sesji i ciasteczek
11. `spec/adr/004-error-contracts.md`
    - Kiedy zwracać 400 vs 404 vs 422 vs 500

Format: [MADR](https://adr.github.io/madr/) — pozwala na automatyczne generowanie indeksu.

---

### Faza 4 — Testy kontraktowe *(zależy od Faz 1 + 2)*

12. `tests/test_parser.py`
    - `winmss_results.py`: parsing XML→dict, edge cases (puste pola, nieznane dywizje, uszkodzony CAB)
13. `tests/test_api_public.py`
    - Weryfikacja odpowiedzi `/api/matches/{id}` i `/api/rankings/{id}` względem JSON Schema
    - URL state restore (`?match=5&div=Open,Modified`)
14. `tests/test_api_admin.py`
    - CRUD dywizji standardowych
    - Batch division mapping — idempotentność operacji
15. `tests/test_database.py`
    - `apply_division_mappings()` (`database.py`)
    - `get_ranking()` (`database.py`)

---

### Faza 5 — Flow docs *(można równolegle z Fazą 4)*

16. `spec/flows/ranking-calculation.md`
    - Algorytm `_prepare()` w formacie Given/When/Then krok po kroku
    - Kalkulator procent, ekstrakcja poziomów, przypisanie dywizji
17. `spec/flows/cab-parsing.md`
    - CAB → XML rowsets → dict z referencją do `winmss_results.py`
18. `spec/flows/division-mapping.md`
    - Pipeline i kolejność aplikowania mapowań per match

---

### Faza 6 — CI pipeline *(zależy od Fazy 4)*

19. `.github/workflows/ci.yml`
    - `pytest tests/` — testy kontraktowe
    - Walidacja schematów JSON Schema (`jsonschema`)
    - `docker compose build` — weryfikacja buildu (bez push)
    - Opcjonalnie: `schemathesis run spec/openapi.yaml` (fuzz-testing)

---

## Kluczowe pliki do modyfikacji

| Plik | Zmiana |
|------|--------|
| `requirements.txt` | wydzielić dev-deps do `requirements-dev.txt` |
| `app.py` | dodać `_error_response()` helper; bez refaktoryzacji `_prepare()` |
| `database.py` | bez zmian struktury — opisany przez ADR i schematy |
| `winmss_results.py` | pierwsze testy projektu — tutaj zaczynamy |

---

## Decyzje projektowe

| Decyzja | Wybór |
|---------|-------|
| Kierunek spec | **Spec-first** — piszemy spec → testy → kod, nie generujemy spec z kodu |
| Refaktoryzacja `_prepare()` | **Poza zakresem** — specs opisują funkcję, refaktor to osobny PR |
| E2E (Playwright) | **Poza zakresem** — najpierw testy kontraktowe HTTP |
| Format ADR | **MADR** — umożliwia automatyczne generowanie indeksu |
| `schemathesis` w CI | Opcjonalny na start, obowiązkowy gdy spec jest stabilny |

---

## Otwarte pytania

1. **Język testów i ADR** — angielski (standard Open Source) czy polski (spójny z README)?
2. **Schemathesis w CI** — od razu obowiązkowy krok czy opcjonalny?
3. **Format ADR** — MADR z frontmatterem czy prosty Markdown?
