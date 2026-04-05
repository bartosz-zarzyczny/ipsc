# ADR 002: Strategia mapowania dywizji WinMSS na standardowe dywizje IPSC

- Status: accepted
- Data: 2026-04-05
- Powiązane: [database.py](../../database.py) — tabela `division_mappings`, funkcje
  `apply_division_mappings()`, `set_division_mapping()`, `copy_division_mappings()`
- Powiązane API: `POST /admin/api/divisions-mapping`, `POST /admin/api/divisions-mapping/copy`

## Kontekst

Nazwy dywizji w plikach WinMSS (`.cab`) są **niestandardowe i zmienne** — różne zawody
mogą używać skrótów, wariantów językowych lub lokalnych nazw (np. `"STD"`, `"Standard Pistol"`,
`"Std"` dla tej samej dywizji IPSC Standard). Aplikacja musi:

1. Wyświetlać dywizje pod ujednoliconymi nazwami w UI i PDF.
2. Grupować zawodników z różnych zawodów w rankingach według jednej logicznej dywizji.
3. Zachować oryginalne nazwy z pliku źródłowego do celów audytowych.

## Opcje które rozważano

### Opcja A — Normalizacja w parserze (hardcoded mapping)

Stała tablica `DIVISION_ALIASES` w `winmss_results.py` mapująca znane warianty na
standardowe nazwy przy imporcie.

Wady: lista aliasów musi być utrzymywana w kodzie; nowe, lokalne warianty wymagają
nowej wersji aplikacji; nie obsługuje mapowań specyficznych dla jednych zawodów.

### Opcja B — Mapowanie per-zawody przez administratora (wybrana)

Admin ręcznie mapuje nazwy dywizji z każdych importowanych zawodów na standardowe dywizje
IPSC zdefiniowane w tabeli `standard_divisions`. Mapowania są per `(match_id, source_division)`.

Zalety: pełna elastyczność; obsługuje nieznane nazwy bez zmiany kodu; admin widzi
dokładnie co mapuje na co; operacja kopiowania (`copy_division_mappings`) redukuje
powtarzalną pracę między zawodami tej samej serii.  
Wady: wymaga manualnej akcji po każdym imporcie (jeśli nie użyto copy).

### Opcja C — Globalne mapowanie (bez kontekstu zawodów)

Jedna globalna tablica `source_division → standard_division` dla całej aplikacji.

Wady: kolizje gdy ta sama nazwa oznacza różną dywizję w różnych kontekstach;
niemożliwe cofnięcie dla jednych zawodów bez wpływu na inne.

## Decyzja

Wybrano **Opcję B** — mapowania per-zawody. Klucz główny tabeli `division_mappings`
to `(match_id, source_division)`, co gwarantuje izolację między zawodami.

Dodano operację **copy** (`POST /admin/api/divisions-mapping/copy`) aby zredukować
pracę manualną: kopiuje wszystkie mapowania z `source_match_id` na `target_match_id`
z semantyką **replace** (istniejące mapowania w target są nadpisywane rekordami ze source).

## Semantyka operacji `apply_division_mappings()`

Funkcja wykonuje **efemeryczną transformację** danych zawodów na potrzeby odpowiedzi API.
Nie modyfikuje `data_json` w bazie.

Pipeline per zawodnik:
1. Sprawdź `competitor.division` w słowniku mapowań dla danego `match_id`.
2. Jeśli mapowanie istnieje i `mapped_division_id != null`:
   - Pobierz nazwę z `standard_divisions` → nadpisz `competitor.division`.
   - Zapisz oryginalną nazwę w `competitor._original_division` (prefix `_` = pole pomocnicze, nie spec).
3. Jeśli mapowanie zawiera `color`:
   - Dodaj `competitor.division_color` (CSS string).
   - Akumuluj w `data.division_colors` (mapa `division_name → color`).
4. Jeśli brak mapowania dla danej dywizji — zawodnik pozostaje bez zmian.

## Zasady wynikające z tej decyzji

1. **`apply_division_mappings()` jest wywoływana wyłącznie w warstwie API** — nigdy wewnątrz
   funkcji bazy danych ani parsera. Miejsca wywołania: `api_get_match()`, `api_get_ranking()`.
2. **Kopie mapowań są idempotentne** — wielokrotne wywołanie `copy_division_mappings(src, tgt)`
   daje ten sam wynik (INSERT OR REPLACE semantics).
3. **`mapped_division_id = null` oznacza "brak mapowania ID"** — rekord może nadal istnieć
   z samym kolorem (`color != null`). Nie należy tego interpretować jako błędu.
4. **Nie cachować wyników `apply_division_mappings()`** — mapowania mogą się zmieniać
   przez panel admina w dowolnym momencie.
5. **Usunięcie standardowej dywizji jest blokowane** jeśli `division_mappings` zawiera
   referencję (`DELETE` → `RESTRICT` przez funkcję `delete_standard_division()`).

## Konsekwencje

- Każde nowe zawody zaimportowane z nową obsadą dywizji wymagają przejrzenia mapowań.
- Ranking zawodów z różnymi nazwami dywizji ale tym samym mapowaniem zwróci spójne
  nazwy dywizji — frontend może grupować zawodników poprawnie.
- Pole `_original_division` dostępne w odpowiedzi API umożliwia audyt bez potrzeby
  oddzielnego endpoint.
