# Flow: Obliczanie wyników i rankingu

**Źródłowe funkcje:** `winmss_results.build_results()`, `rank_competitors()`,
`add_percent_of_best()`, `app._prepare()`  
**Dane wejściowe:** plik `.cab` (ścieżka) lub słownik `data` (w testach)  
**Dane wyjściowe:** słownik `{ match, stages[], competitors[] }` gotowy do serializacji JSON

---

## Diagram przepływu

```
.cab plik
    │
    ▼
load_data()
    │  ─ rozpakowuje .cab → tmpdir
    │  ─ parsuje 7 plików XML (parse_winmss_xml)
    │  ─ zwraca dict: match / members / enrolled / stages / scores / clubs / squads
    │
    ▼
build_results()
    │
    ├─[1] Wczytaj match_info (pierwszy wiersz THEMATCH.XML)
    │
    ├─[2] Zindeksuj members: MemberId → {Lastname, Firstname, Female, …}
    │
    ├─[3] Zindeksuj enrolled: MemberId → {CompId, DivId, CatId, IsDisq, SquadId}
    │
    ├─[4] Posortuj stages po StageId (int)
    │
    ├─[5] Zindeksuj scores: (MemberId, StageId) → {ScoreA…ScoreD, Misses, ProcError,
    │      Penalties, ShootTime, FinalScore, IsDisq}
    │
    ├─[6] Dla każdego zawodnika w enrolled:
    │       ├─ Przetłumacz DivId → nazwa dywizji (DIVISION_NAMES)
    │       ├─ Przetłumacz CatId → kategoria (CATEGORY_NAMES)
    │       ├─ Dla każdego etapu:
    │       │    ─ Jeśli brak score → stage_score = None
    │       │    ─ Oblicz HF = FinalScore / ShootTime
    │       │    ─ Zbierz {A, B, C, D, M, PE, NS, time, hf, pts, disq}
    │       └─ Suma total_points / total_time (z pominięciem dyskwalifikowanych torów)
    │
    ├─[7] Oblicz best_hf_per_stage_global[i] — max HF na torze i spośród WSZYSTKICH,
    │      z pominięciem zawodników zdyskwalifikowanych
    │
    ├─[8] Oblicz best_hf_per_stage_div[division][i] — max HF per dywizja per tor
    │
    └─[9] Dla każdego zawodnika:
           Dla każdego toru i:
             stage_pts_overall  = (hf / best_global_hf[i])   × MaxPoints[i]
             stage_pts_in_div   = (hf / best_div_hf[div][i]) × MaxPoints[i]
             sc["pts"]          = round(stage_pts_in_div, 4)

           total_points         = Σ stage_pts_overall  (ranking ogólny)
           total_points_overall = Σ stage_pts_overall  (zakładka Overall)
           total_points_in_div  = Σ stage_pts_in_div   (zakładka Dywizje)
    │
    ▼
rank_competitors()
    │  ─ Rozdziela na active (not is_disq) i disq
    │  ─ active.sort(by total_points DESC)
    │  ─ Remis → ten sam rank (ex aequo)
    │  ─ Dyskwalifikowani sortowani po nazwisku, rank = "DSQ"
    │
    ▼
add_percent_of_best()
    │  ─ best_pts = max(total_points) spośród active
    │  ─ pct = (total_points / best_pts) × 100  (0.0 dla DSQ)
    │
    ▼
_prepare() — finalna serializacja
    │
    ├─ Oblicz max_hf_by_div per tor per dywizja
    │    stage_div_max_hf[i][division] = max HF (spośród non-disq)
    │    Służy do wyświetlania % per tor w zakładce dywizji
    │
    ├─ Wyłuś level z nazwy (kaskadowe regex):
    │    1. "LEVEL N"  (arabski)
    │    2. "LEVEL III" (rzymski → roman_to_int)
    │    3. "L2" (litera + cyfra, bez kolizji z "LEVEL")
    │    4. "L II"
    │    5. Fallback: MatchLevel z danych XML
    │
    └─ Zwróć { match, stages[], competitors[] }
```

---

## Szczegóły algorytmu IPSC

### Kalkulacja punktów IPSC

IPSC stosuje **Hit Factor (HF)** jako podstawę oceny:

$$HF = \frac{\text{suma punktów za strefy trafień}}{\text{czas strzelania [s]}}$$

Punkty procentowe na torze:

$$pts\_stage = \frac{HF_{zawodnik}}{HF_{lider\_w\_dyw}} \times MaxPoints_{tor}$$

Zawodnik z najwyższym HF w dywizji otrzymuje 100% punktów toru. Pozostali proporcjonalnie mniej.

### Dwa systemy punktów

| Pole | Opis | Zastosowanie |
|------|------|--------------|
| `total_points_overall` | Lider = zawodnik z best HF **globalnie** | Zakładka Overall, ranking ogólny |
| `total_points_in_division` | Lider = zawodnik z best HF **w dywizji** | Zakładka Dywizje |
| `total_points` | Alias dla `total_points_overall` | Podstawa rankingu i `pct` |

### Dyskwalifikacja

| Poziom | Pole | Skutek |
|--------|------|--------|
| Zawodnik (cały mecz) | `enrolled.IsDisq = True` → `c["is_disq"] = True` | Rank = `"DSQ"`, nie wlicza się do best HF, `pct = 0.0` |
| Zawodnik na torze | `score.IsDisq = True` → `sc["disq"] = True` | Tor nie wlicza się do total_points / total_time |

### Remisy

Dwóch zawodników z identycznym `total_points` (zmiennoprzecinkowym) otrzymuje **ten sam rank**. Następny zawodnik otrzymuje rank **n+2** (nie n+1). Jest to standardowe zachowanie IPSC.

---

## Niezmienniki (ważne dla testów)

1. `len(c["stage_scores"]) == len(stages)` dla każdego zawodnika — brakujący wynik to `None`, nie pominięcie.
2. Zawodnik z `is_disq=True` ma `rank == "DSQ"` i zawsze pojawia się **po** sklasyfikowanych.
3. Lider aktywnych zawodników ma `pct == 100.0`.
4. `total_points == total_points_overall` — są to aliasy (oba przechowywane oddzielnie).
5. `sc["pts"]` po `build_results` zawiera `stage_pts_in_div` (per-dywizja), **nie** surowy `FinalScore`.
6. `stage_div_max_hf` w odpowiedzi API jest obliczany w `_prepare()`, **nie** w `build_results()`.
