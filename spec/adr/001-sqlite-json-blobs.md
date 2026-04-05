# ADR 001: Przechowywanie wyników zawodów jako JSON blob w SQLite

- Status: accepted
- Data: 2026-04-05
- Powiązane: [database.py](../../database.py) — tabela `matches`, funkcje `save_match()`, `get_match()`

## Kontekst

Aplikacja importuje wyniki zawodów IPSC z plików `.cab` (WinMSS). Każde zawody składają się
z hierarchicznych, zagnieżdżonych danych: metadane meczu → etapy → zawodnicy → wyniki per etap.
Liczba etapów (3–30+) i zawodników (10–500+) jest zmienna i zależy od konkretnych zawodów.

Dane te są **zawsze odczytywane w całości** — żadna operacja nie wymaga filtrowania po
pojedynczych polach wewnątrz wyników. Jedyny publiczny wyjątek to edycja imienia/nazwiska
i kategorii zawodnika (`update_competitor_name()`), która wymaga pełnego round-trip
deserializacji i ponownej serializacji.

## Opcje które rozważano

### Opcja A — Pełna normalizacja relacyjna

Osobne tabele: `match_stages`, `match_competitors`, `stage_scores`.

Zalety: naturalne zapytania SQL, indeksy, możliwość raportowania między zawodami.  
Wady: schemat musi modelować wszystkie warianty danych WinMSS z góry; migracje przy każdej
zmianie formatu źródłowego; złożone JOIN-y dla odczytu całości meczu; żaden widok UI
nie używa zapytań między zawodami w obrębie jednego meczu.

### Opcja B — JSON blob w kolumnie TEXT SQLite (wybrana)

Cała struktura `{match, stages[], competitors[]}` serializowana do `data_json TEXT`.
Metadane skrótowe (`name`, `date`, `level`, `multiplier`) pozostają kolumnami relacyjnymi
dla potrzeb listowania i sortowania bez deserializacji.

Zalety: zero migracji przy zmianie struktury `_prepare()`; odczyt = jeden `SELECT` bez JOIN;
format wyjściowy API == format przechowywania (brak mapowania warstw).  
Wady: brak możliwości zapytań wewnątrz JSON (bez SQLite JSON1); edycja pól wymaga
pełnego deserialization → modyfikacja → serialize.

### Opcja C — Osobny plik JSON na dysku

Zalety: możliwość inspekcji wzrokiem, brak SQLite dependency.  
Wady: brak transakcji, brak atomic backup, trudniejsza izolacja per-instancja.

## Decyzja

Wybrano **Opcję B**. Dane zawodów są `write-once, read-all` — wyniki zawodów po imporcie
nie zmieniają się strukturalnie. Edycja zawodnika to operacja administracyjna, rzadka
i akceptowalna jako round-trip. Uproszczenie kodu (brak ORM, brak JOIN) przeważa nad
korzyściami normalizacji.

Metadane skrótowe (`name`, `date`, `level`, `multiplier`) są kolumnami relacyjnymi —
to granica: wszystko co jest potrzebne **bez** ładowania pełnych danych zawodów.

## Zasady wynikające z tej decyzji

1. **Nie dodawać pól do `data_json` które mogą być potrzebne do listowania** — takie pola
   trafiają jako kolumny relacyjne w tabeli `matches`.
2. **Wersjonowanie formatu bloba** — każda zmiana schematu `_prepare()` musi być udokumentowana
   w [spec/schemas/match.json](../schemas/match.json). Nie wymagamy migracji istniejących
   rekordów jeśli nowe pola mają wartości domyślne i są opcjonalne w schemacie.
3. **Edycja wewnątrz bloba** — akceptowalna tylko dla operacji administracyjnych (admin panel).
   Nie implementować endpointów publicznych które modyfikują `data_json`.
4. **Dane pochodne** (`division_colors`, `_original_division`) injektowane przez
   `apply_division_mappings()` są **efemeryczne** — nie zapisywane z powrotem do `data_json`,
   tylko dodawane do odpowiedzi API.

## Konsekwencje

- `get_match()` deserializuje cały blob przy każdym odczycie — akceptowalne dla rozmiaru
  danych zawodów IPSC (typowo < 500 KB).
- Backup bazy = backup całości danych + mapowań + użytkowników jednym plikiem `.db`.
- Izolacja instancji przez UUID w nazwie pliku DB (`{instance_id}.db`) pozostaje spójna
  z tym podejściem — każda instancja ma własny blob store.
- Dodanie SQLite JSON1 (`json_each`, `json_extract`) umożliwiłoby zapytania bez zmiany
  schematu — opcja na przyszłość jeśli pojawi się potrzeba.
