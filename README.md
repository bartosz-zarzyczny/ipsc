# IPSC — WinMSS Results Viewer

Narzędzie do wyciągania i przeglądania wyników zawodów strzeleckich IPSC z plików WinMSS `.cab`.

## Struktura projektu

```
├── WinMSS.cab                    # Plik z danymi zawodów (WinMSS export)
├── ipsc.db                       # Baza danych SQLite (zawody, użytkownicy)
├── winmss_results.py             # Skrypt CLI – wyniki w terminalu / eksport CSV
├── app.py                        # Serwer Flask – przeglądarkowy interfejs UI
├── database.py                   # Warstwa bazy danych (ORM)
└── templates/
    ├── index.html                # Frontend (przeglądarka wyników)
    ├── admin.html                # Panel administracyjny (zawody + użytkownicy)
    └── admin_login.html          # Formularz logowania
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
# → przeglądarka otworzy się automatycznie na http://localhost:5000
```

### Panel logowania (Admin)

Dostęp do panelu administracyjnego wymaga zalogowania się.

**Konto domyślne:**
- **Login:** `bartek`
- **Hasło:** `IP$c2023`

Konta użytkowników przechowywane są w bazie danych SQLite (`ipsc.db`) z zabezpieczeniem SHA-256.

### Główna strona — przeglądarka wyników

- **Wybór zawodów** — lista zapisanych zawodów w bazie; kliknięcie ładuje wyniki
- **Nagłówek zawodów** — nazwa, data, poziom (L1/L2/L3), liczba torów i zawodników
- **Podium** — karty top 3 z Hit Factor / punktami / czasem
- **Zestawienie ogólne** — sortowalna tabela wszystkich zawodników; kliknięcie wiersza rozwija szczegóły torów (A/B/C/D/M/PE, HF, % w dywizji)
- **Zakładka Dywizje** — osobne tabele per dywizja z rankingiem i % do lidera dywizji
- **Zakładka Tory** — ranking na wybranym torze z kolorowanymi kolumnami strzelań; procenty liczone w ramach dywizji
- **Filtry** — wyszukiwanie po nazwisku, filtr po dywizji, filtr po kategorii (Lady / Senior / Super Senior); filtry działają na wszystkich zakładkach włącznie z torami
- **Eksport CSV** — generowany po stronie przeglądarki, otwieralny w Excelu (UTF-8 z BOM)
- **Link do panelu** — przycisk w górnym rogu odsyła do `/admin`

### Panel administracyjny

Dostępny pod `/admin` — wymaga zalogowania.

#### Tab: Zawody
- **Wgrywanie pliku** — drag & drop lub klik na formularz; automatyczne wykrywanie `WinMSS.cab` w bieżącym katalogu
- **Lista zawodów** — tabela wszystkich zapisanych zawodów (ID, nazwa, data, poziom)
- **Usuwanie zawodów** — przyciski do usunięcia pojedynczych zawodów z bazy

#### Tab: Użytkownicy
- **Zmiana hasła** — formularz do zmiany hasła zalogowanego użytkownika (wymaga starego hasła)
- **Zarządzanie użytkownikami** — tabela wszystkich użytkowników z labelką "Ty" dla zalogowanego
  - Tworzenie nowego użytkownika (login + hasło)
  - Usuwanie użytkownika (zabezpieczenie — ostatného użytkownika nie można usunąć)

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

## Baza danych (`database.py`)

Aplikacja wykorzystuje SQLite (`ipsc.db`) do przechowywania zawodów i zarządzania użytkownikami.

### Tabela: `matches`

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    date TEXT,
    level INTEGER,
    data_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
```

- **id** — unikalny identyfikator zawodów
- **name** — nazwa zawodów (z THEMATCH.XML)
- **date** — data (YYYY-MM-DD)
- **level** — poziom (1-3)
- **data_json** — pełne dane JSON (ustrukturyzowane wyniki, etapy, zawodnicy)
- **created_at** — znacznik czasu dodania

### Tabela: `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
```

- **id** — unikalny identyfikator użytkownika
- **username** — login (unikatowy)
- **password_hash** — SHA-256 hash hasła
- **created_at** — znacznik czasu utworzenia

**Funkcje:**
- `add_user(username, password_hash)` — tworzy użytkownika
- `verify_user(username, password_hash)` — weryfikuje hasło (timing-safe comparison)
- `list_users()` — pobiera listę wszystkich użytkowników
- `delete_user(user_id)` — usuwa użytkownika (zapobiega usunięciu ostatniego)
- `change_password(user_id, password_hash)` — zmienia hasło

## API Routes

### Public

| Route | Metoda | Opis |
|-------|--------|------|
| `/` | GET | Główna strona (przeglądarka wyników) |

### Zalogowany użytkownik (admin)

| Route | Metoda | Opis |
|-------|--------|------|
| `/admin` | GET | Panel administracyjny |
| `/admin/login` | GET, POST | Logowanie |
| `/admin/logout` | GET | Wylogowanie |
| `/admin/upload` | POST | Wgranie pliku .cab |
| `/admin/delete/<id>` | POST | Usunięcie zawodów |
| `/admin/users` | GET | Lista użytkowników (API JSON) |
| `/admin/users` | POST | Tworzenie użytkownika |
| `/admin/users/<id>` | POST | Usunięcie użytkownika |
| `/admin/change-password` | POST | Zmiana hasła |

### API Danych (JSON)

| Route | Metoda | Opis |
|-------|--------|------|
| `/api/matches` | GET | Lista dostępnych zawodów |
| `/api/match/<id>` | GET | Dane konkretnych zawodów |

## Mapowanie dywizji (Shotgun)

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