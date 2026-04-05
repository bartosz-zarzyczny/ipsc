# Flow: Parsowanie pliku .cab WinMSS

**Źródłowe funkcje:** `winmss_results.extract_cab()`, `parse_winmss_xml()`, `load_data()`  
**Dane wejściowe:** ścieżka do pliku `.cab` wyprodukowanego przez oprogramowanie WinMSS  
**Dane wyjściowe:** słownik `data` z kluczami: `match`, `members`, `enrolled`, `stages`, `scores`, `clubs`, `squads`

---

## Diagram przepływu

```
plik .cab
    │
    ▼
extract_cab(cab_path, out_dir)
    │
    ├─ Sprawdź dostępność narzędzia:
    │    1. cabextract  (preferowane: cross-platform, brew install cabextract)
    │       └─ cabextract -d <out_dir> <cab_path>
    │    2. expand      (wbudowane macOS/Windows)
    │       └─ expand <cab_path> -F:* <out_dir>
    │    3. Żadne nie znalezione → RuntimeError z instrukcją instalacji
    │
    ▼
Folder tymczasowy tmpdir (tempfile.mkdtemp)
zawiera pliki XML po rozpakowaniu
    │
    ▼
load_data()
    │
    ├─ Buduje file_map: {NAZWA_UPPERCASE → bezwzględna ścieżka}
    │   (case-insensitive lookup — WinMSS czasem zmienia wielkość liter)
    │
    ├─ Wczytuje 7 plików przez parse_winmss_xml():
    │    ┌─────────────────┬───────────────────────────────────────────────┐
    │    │ Plik XML        │ Zawartość                                    │
    │    ├─────────────────┼───────────────────────────────────────────────┤
    │    │ THEMATCH.XML    │ Metadane meczu: MatchName, MatchDt, MatchLevel│
    │    │ MEMBER.XML      │ Zawodnicy: MemberId, Lastname, Firstname,     │
    │    │                 │   Female, RegionId                            │
    │    │ ENROLLED.XML    │ Rejestracja: MemberId, CompId, DivId, CatId, │
    │    │                 │   IsDisq, SquadId                             │
    │    │ STAGE.XML       │ Tory: StageId, StageName, MaxPoints           │
    │    │ SCORE.XML       │ Wyniki: MemberId, StageId, ScoreA–D, Misses,  │
    │    │                 │   ProcError, Penalties, ShootTime, FinalScore,│
    │    │                 │   IsDisq                                      │
    │    │ CLUB.XML        │ Kluby (używane tylko do wyświetlania)         │
    │    │ SQUAD.XML       │ Grupy (używane tylko do wyświetlania)         │
    │    └─────────────────┴───────────────────────────────────────────────┘
    │
    ├─ Jeśli plik nie istnieje → zwraca [] (nie rzuca wyjątku)
    │
    └─ Usuwa tmpdir (finally: shutil.rmtree)
    │
    ▼
dict data = {
    "match":    [ {MatchName, MatchDt, MatchLevel} ],
    "members":  [ {MemberId, Lastname, …}, … ],
    "enrolled": [ {MemberId, CompId, DivId, …}, … ],
    "stages":   [ {StageId, StageName, MaxPoints}, … ],
    "scores":   [ {MemberId, StageId, ScoreA, …}, … ],
    "clubs":    [ … ],
    "squads":   [ … ],
}
```

---

## Format XML WinMSS (rowset ADO)

WinMSS używa formatu **XML rowset** wywodzącego się z ADO (ActiveX Data Objects). Jest to **niestandardowy** format — stdlib `xml.etree` zwraca błędy na przestrzeni nazw `z:`, dlatego używamy parsera **regex**.

### Przykładowy plik MEMBER.XML

```xml
<xml xmlns:z='#RowsetSchema'>
  <z:row MemberId='1042' Lastname='Kowalski' Firstname='Jan' Female='false' RegionId='PL'/>
  <z:row MemberId='2031' Lastname='Nowak'    Firstname='Anna' Female='true' RegionId='PL'/>
</xml>
```

### Strategia parsowania (`parse_winmss_xml`)

```python
for m in re.finditer(r"<z:row\s+([^>]+)/>", content, re.DOTALL):
    attrs = dict(re.findall(r"(\w+)='([^']*)'", m.group(1)))
    rows.append(attrs)
```

**Ograniczenia parsera regex:**
- Wartości atrybutów **nie mogą** zawierać apostrofów `'` (brak obsługi encji XML).  
  WinMSS w praktyce ich nie generuje.
- Parser pomija elementy inne niż `<z:row … />` (np. deklaracje schematu `<z:Schema>`).
- Wszystkie wartości są **stringami** — konwersja typów (int, float, bool) odbywa się
  w `build_results()`.

---

## Mapowania wartości XML → model domenowy

### DivId → nazwa dywizji (`DIVISION_NAMES`)

| DivId | Nazwa         | Uwaga                          |
|-------|---------------|--------------------------------|
| `"1"` | Open          | Pistolet                       |
| `"2"` | Standard      | Pistolet                       |
| `"3"` | Standard S2   | Pistolet                       |
| `"4"` | Modified      | Pistolet                       |
| `"5"` | Production    | Pistolet                       |
| `"6"` | Production Optics | Pistolet                   |
| `"7"` | Prod. Optics Carry | Pistolet                  |
| `"8"` | Classic       | Pistolet                       |
| `"9"` | Revolver      | Pistolet                       |
| `"10"` | Open         | Shotgun (ten sam DivId, inny FirearmId) |
| `"11"` | Standard     | Shotgun                        |
| `"12"` | Standard Manual | Shotgun                     |
| `"13"` | Modified     | Shotgun                        |
| inne  | `Div<id>`     | Fallback — nieznane dywizje    |

> **Uwaga:** DivId `"1"` i `"10"` mapują się na tę samą nazwę `"Open"`. W zawodach
> mieszanych (pistolet + shotgun) może to powodować kolizje w widoku per-dywizja.
> Rozwiązanie: funkcja admin mapowania dywizji (patrz [division-mapping.md](division-mapping.md)).

### CatId → kategoria (`CATEGORY_NAMES`)

| CatId | Kategoria    |
|-------|--------------|
| `"0"` | *(brak)*     |
| `"1"` | Lady         |
| `"2"` | Junior       |
| `"3"` | Senior       |
| `"4"` | Super Senior |
| `"5"` | Super Junior |

### Boolean w XML

`"true"` / `"false"` (case-insensitive) → Python `bool` przez `.lower() == "true"`.  
Pola: `Female`, `IsDisq` (w enrolled i scores).

---

## Obsługa błędów

| Sytuacja | Zachowanie |
|----------|-----------|
| Brak narzędzia `cabextract` / `expand` | `RuntimeError` z komunikatem + instrukcją `brew install cabextract` |
| Plik XML nieobecny w archiwum | `load()` zwraca `[]` — `build_results` traktuje jako pusty |
| Błąd wypakowania (cabextract returncode ≠ 0) | `RuntimeError` z output stderr |
| Błąd odczytu XML (encoding) | `errors="replace"` — znak zastępczy `\ufffd`, parsowanie kontynuowane |
| Zawodnik bez wyników na torze | `stage_scores[i] = None` |
| ShootTime = 0 | HF = 0.0 (dzielenie przez zero zabezpieczone) |

---

## Środowisko wykonania

`extract_cab()` wywołuje **zewnętrzny proces** (`subprocess.run`). W środowisku
produkcyjnym Docker (patrz [Dockerfile](../../Dockerfile)) `cabextract` musi być
zainstalowany w obrazie. W testach `extract_cab()` mockujemy — testy nie
wymagają pliku `.cab` ani zewnętrznych narzędzi.
