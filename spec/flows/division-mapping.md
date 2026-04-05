# Flow: Mapowanie dywizji

**Źródłowe funkcje:** `database.apply_division_mappings()`, `get_all_division_mappings()`,
`set_division_mapping()`, `copy_division_mappings()`  
**Powiązany ADR:** [002-division-mapping.md](../adr/002-division-mapping.md)  
**Powiązany endpoint:** `GET/POST /admin/api/divisions-mapping`

---

## Problem, który rozwiązuje mapowanie

WinMSS eksportuje dywizje jako numery (`DivId`), które `DIVISION_NAMES` tłumaczy na
nazwy tekstowe. Problem pojawia się gdy:

1. **Kolizja DivId** — DivId `"1"` to `"Open"` pistoletowy i DivId `"10"` to `"Open"`
   shotgunowy. Bez mapowania obie dywizje wyglądają identycznie.
2. **Lokalne nazewnictwo** — organizator zawodów używa własnych nazw dywizji
   (`"STD"`, `"OPN"`) niekompatybilnych z nazwami standardowymi.
3. **Kolorowanie dywizji** — admin chce przypisać kolory dywizjom w widoku wyników.

---

## Diagram przepływu

```
Admin panel → POST /admin/api/divisions-mapping
    │  { match_id, source_division, mapped_division_id, mapped_division_color }
    │
    ▼
set_division_mapping(match_id, source_division, mapped_division_id, color)
    │
    ├─ Jeśli mapped_division_id IS NULL AND color IS NULL
    │    → DELETE FROM division_mappings WHERE match_id=? AND source_division=?
    │
    └─ W przeciwnym razie
         → INSERT OR REPLACE INTO division_mappings
           (match_id, source_division, mapped_division_id, color)
    │
    ▼
Tabela division_mappings w SQLite
    │  match_id INTEGER  ─── FK → matches.id
    │  source_division TEXT (np. "Open", "STD", "OPN")
    │  mapped_division_id INTEGER (nullable) ─── FK → standard_divisions.id
    │  color TEXT NULLABLE  (np. "#ff0000")
    │
    ▼ (przy każdym GET /api/matches/<id>)
    │
apply_division_mappings(match_data, match_id)
    │
    ├─[1] Deep-copy match_data (json.loads(json.dumps(…))) — nie mutuje oryginału
    │
    ├─[2] Odczytaj match_id z parametru lub z data["match"]["id"]
    │      Jeśli brak match_id → zwróć dane bez zmian
    │
    ├─[3] Pobierz mappings = get_all_division_mappings(match_id)
    │      Jeśli brak mapowań → zwróć dane bez zmian (fast-path)
    │
    └─[4] Dla każdego zawodnika w data["competitors"]:
           original_division = competitor["division"]
           Jeśli original_division IN mappings:
             mapping = mappings[original_division]
             │
             ├─ mapped_division_id IS NOT NULL
             │    → competitor["division"] = standard_divisions[id]["name"]
             │      competitor["_original_division"] = original_division
             │
             └─ color IS NOT NULL
                  → competitor["division_color"] = color
                    division_colors[division] = color
    │
    ├─[5] Jeśli division_colors niepuste → data["division_colors"] = {div: color}
    │
    └─[6] Zwróć zmodyfikowaną kopię danych
```

---

## Semantyka operacji

### Tworzenie / aktualizacja mapowania

`set_division_mapping()` używa `INSERT OR REPLACE` — operacja jest **idempotentna**.
Ponowne wywołanie z tymi samymi lub nowymi wartościami zawsze nadpisuje.

```
set_division_mapping(match_id=5, source="Open", mapped_division_id=2, color="#0000ff")
# Pierwsze wywołanie: INSERT
# Drugie wywołanie: REPLACE (UPDATE)
# Wynik jest identyczny — mapowanie dla "Open" w meczu 5 = division 2, kolor niebieski
```

### Usuwanie mapowania

Mapowanie jest usuwane gdy **oba** pola są `None`:

```
set_division_mapping(match_id=5, source="Open", mapped_division_id=None, color=None)
→ DELETE FROM division_mappings WHERE match_id=5 AND source_division='Open'
```

Samo `mapped_division_id=None` z `color` ustawionym zachowuje wiersz (tylko kolor).

### Kopiowanie mapowań

`copy_division_mappings(source_match_id, target_match_id)` kopiuje **wszystkie** mapowania
ze źródłowego meczu do docelowego. Operacja to **replace** — istniejące mapowania w
`target_match_id` są nadpisywane. Brak mapowań źródłowych = brak operacji (return True).

### Efemeryczność

`apply_division_mappings()` **nie zapisuje** zmian z powrotem do bazy. Zmodyfikowane dane
`competitor["division"]` istnieją tylko w odpowiedzi API. Tabela `matches.data_json`
pozostaje niezmieniona. To jest świadoma decyzja projektowa — patrz
[ADR 002](../adr/002-division-mapping.md).

---

## Tabela bazy danych

```sql
CREATE TABLE IF NOT EXISTS division_mappings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id            INTEGER NOT NULL,
    source_division     TEXT NOT NULL,
    mapped_division_id  INTEGER,
    color               TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(match_id, source_division),
    FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
    FOREIGN KEY (mapped_division_id) REFERENCES standard_divisions(id)
);
```

Klucz unikalny `(match_id, source_division)` gwarantuje jedno mapowanie per dywizja
per mecz. `ON DELETE CASCADE` usuwa mapowania przy usunięciu meczu.

---

## Stany mapowania dla jednej dywizji

| `mapped_division_id` | `color` | Efekt |
|---------------------|---------|-------|
| NOT NULL | NULL | Zmiana nazwy dywizji, bez koloru |
| NOT NULL | NOT NULL | Zmiana nazwy + kolor |
| NULL | NOT NULL | Tylko kolor, nazwa bez zmian |
| NULL | NULL | Wiersz nie istnieje (usunięty) |

---

## Skąd pochodzi lista "imported_divisions"?

`GET /admin/api/divisions-mapping?match_id=X` zwraca pole `imported_divisions` —
listę unikalnych nazw dywizji znalezionych w `data_json` wszystkich meczów
(lub konkretnego meczu gdy `match_id` podane).

Funkcja `get_imported_divisions(match_id)` używa SQLite JSON1:

```sql
SELECT DISTINCT json_extract(value, '$.division') as division
FROM matches, json_each(json_extract(data_json, '$.competitors'))
WHERE matches.id = ?
```

To pozwala adminowi zobaczyć jakie dywizje są w danych i przypisać im mapowania,
bez konieczności ręcznego wpisywania nazw.

---

## Przykład kompletnego flow

**Scenariusz:** Zawody shotgunowe. WinMSS eksportuje dywizję `DivId="11"` jako `"Standard"`
(shotgun), ale organizator chce ją wyświetlać jako `"Shotgun Standard"` z kolorem zielonym.

```
1. Import meczu → data_json zawiera competitors z division="Standard"

2. Admin otwiera panel mapowania dywizji dla meczu ID=7
   GET /admin/api/divisions-mapping?match_id=7
   → imported_divisions: ["Standard", "Open", "Modified"]

3. Admin ustawia mapowanie:
   POST /admin/api/divisions-mapping
   { match_id: 7, source_division: "Standard",
     mapped_division_id: 3, mapped_division_color: "#00aa00" }
   → INSERT INTO division_mappings (7, "Standard", 3, "#00aa00")

4. Użytkownik pobiera wyniki:
   GET /api/matches/7
   → apply_division_mappings(match_data, 7)
   → competitor["division"] = "Shotgun Standard"  (z standard_divisions.id=3)
   → competitor["division_color"] = "#00aa00"
   → data["division_colors"]["Shotgun Standard"] = "#00aa00"
```
