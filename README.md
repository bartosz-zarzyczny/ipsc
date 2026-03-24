# IPSC — WinMSS Results Viewer

Narzędzie do wyciągania i przeglądania wyników zawodów strzeleckich IPSC z plików WinMSS `.cab`.

## Struktura projektu

```
├── WinMSS.cab              # Plik z danymi zawodów (WinMSS export)
├── winmss_results.py       # Skrypt CLI – wyniki w terminalu / eksport CSV
├── app.py                  # Serwer Flask – przeglądarkowy interfejs UI
└── templates/
    └── index.html          # Frontend (single-page app)
```

## Wymagania

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — do rozpakowywania plików `.cab`
  ```bash
  brew install cabextract   # macOS
  ```

## Skrypt CLI (`winmss_results.py`)

Wyciąga dane z pliku `.cab` i wyświetla wyniki w terminalu.

```bash
# Zestawienie ogólne + tabele per dywizja
python3 winmss_results.py

# Tylko zestawienie ogólne
python3 winmss_results.py --overall

# Ze szczegółami per tor
python3 winmss_results.py --stages

# Ranking na każdym torze (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Eksport do CSV (otwieralny w Excelu)
python3 winmss_results.py --csv wyniki.csv

# Inny plik .cab
python3 winmss_results.py inny_mecz.cab --csv wyniki.csv
```

## Interfejs webowy (`app.py`)

```bash
python3 app.py
# → przeglądarka otworzy się automatycznie na http://localhost:5050
```

### Funkcje UI

- **Wgrywanie pliku** — drag & drop lub klik; automatyczne wykrywanie `WinMSS.cab` w bieżącym katalogu
- **Nagłówek zawodów** — nazwa, data, poziom (L1/L2/L3), liczba torów i zawodników
- **Podium** — karty top 3 z Hit Factor / punktami / czasem
- **Zestawienie ogólne** — sortowalna tabela wszystkich zawodników; kliknięcie wiersza rozwija szczegóły torów (A/B/C/D/M/PE, HF, % w dywizji)
- **Zakładka Dywizje** — osobne tabele per dywizja z rankingiem i % do lidera dywizji
- **Zakładka Tory** — ranking na wybranym torze z kolorowanymi kolumnami strzelań; procenty liczone w ramach dywizji
- **Filtry** — wyszukiwanie po nazwisku, filtr po dywizji, filtr po kategorii (Lady / Senior / Super Senior); filtry działają na wszystkich zakładkach włącznie z torami
- **Eksport CSV** — generowany po stronie przeglądarki, otwieralny w Excelu (UTF-8 z BOM)

### Dane zawodnika

| Pole | Opis |
|------|------|
| Miejsce | Ranking ogólny (overall HF) |
| Nr | Numer startowy |
| Nazwisko Imię | Dane zawodnika |
| Dywizja | Open / Standard / Standard Manual / Modified |
| Kategoria | Lady / Senior / Super Senior / Junior |
| Pkt łącznie | Suma punktów ze wszystkich torów |
| Czas łącznie | Suma czasów |
| HF Overall | Hit Factor = punkty / czas |
| % lidera | Procent do najlepszego HF |

### Mapowanie dywizji (Shotgun)

| DivId | Dywizja |
|-------|---------|
| 10 | Open |
| 11 | Standard |
| 12 | Standard Manual |
| 13 | Modified |

Mapowanie można zmienić w `winmss_results.py` → słownik `DIVISION_NAMES`.

## Pliki XML w archiwum `.cab`

| Plik | Zawartość |
|------|-----------|
| `THEMATCH.XML` | Dane zawodów (nazwa, data, poziom) |
| `MEMBER.XML` | Baza zawodników |
| `ENROLLED.XML` | Rejestracja na zawody (dywizja, kategoria, eskwadra) |
| `STAGE.XML` | Definicje torów (nazwa, max punkty, typ) |
| `SCORE.XML` | Wyniki strzelań (A/B/C/D/M/PE, czas, HF) |
| `CLUB.XML` | Kluby |
| `SQUAD.XML` | Eskwadry |
| `TEAM.XML` | Drużyny |
| `CLASSIFY.XML` | Klasyfikacje zawodników |
| `TAG.XML` | Tagi (np. RO) |