# IPSC — WinMSS Results Viewer

Narzędzie do wyciągania i przeglądania wyników zawodów strzeleckich IPSC z plików WinMSS `.cab`.

## Struktura projektu

```
├── WinMSS.cab                    # Plik z danymi zawodów (WinMSS export)
├── data/                         # Folder z bazą danych i konfiguracją (persystentny w Docker)
│   ├── config.json               # Automatycznie generowana konfiguracja instancji
│   └── {instance_id}.db          # Baza danych SQLite (unikalnie nazwana dla każdej instancji)
├── winmss_results.py             # Skrypt CLI – wyniki w terminalu / eksport CSV
├── app.py                        # Serwer Flask – przeglądarkowy interfejs UI
├── database.py                   # Warstwa bazy danych (ORM)
├── docker-compose.yml            # Konfiguracja Docker Compose
├── Dockerfile                    # Specyfikacja kontenera
└── templates/
    ├── index.html                # Frontend (przeglądarka wyników)
    ├── admin.html                # Panel administracyjny (zawody + ranking + użytkownicy)
    └── admin_login.html          # Formularz logowania
```

## Wymagania

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — do rozpakowywania plików `.cab`
  ```bash
  brew install cabextract   # macOS
  ```

## Uruchomienie

### Lokalnie (bez Docker)

```bash
python3 app.py
# → przeglądarka otworzy się na http://localhost:5000
```

### W kontenerze Docker

#### Opcja 1: Docker Compose (zalecane)

```bash
# Instancja domyślna – port 3001, domyślna nazwa kontenera
docker-compose up --build

# Lub w tle
docker-compose up -d
```

**Uruchomienie wielu instancji na jednym VPSie:**

Aby uniknąć konfliktów między instancjami, użyj flagi `-p` (project-name). Każdy projekt musi mieć unikalną nazwę:

```bash
# Instancja 1 – port 3001, projekt ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 docker-compose -p ipsc1 up -d

# Instancja 2 – port 3002, projekt ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 docker-compose -p ipsc2 up -d

# Instancja 3 – port 3003, projekt ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 docker-compose -p ipsc3 up -d
```

**Zarządzanie instancjami:**

```bash
# Wyświetl wszystkie uruchomione kontenery
docker ps

# Zatrzymaj konkretną instancję
docker-compose -p ipsc1 down

# Podgląd logów instancji
docker-compose -p ipsc1 logs -f

# Restartuj konkretną instancję
docker-compose -p ipsc1 restart
```

**Pourczenie flagi `-p`:**

Flaga `-p` izoluje każdy projekt z jego kontenerami, sieciami i wolumenami. Bez niej wszystkie instancje dzielą ten sam project-name, co prowadzi do konfliktów i uniemożliwia uruchomienie wielu instancji jednocześnie.

Każda instancja automatycznie utworzy:
- Unikalny `config.json` (ID instancji)
- Unikalną bazę danych (`data/{instance_id}.db`)
- Oddzielne dane bez konfliktów

Baza danych (`{instance_id}.db`) będzie przechowywana w katalogu `./data/` na hoście i **persysty pomiędzy restartami**.

#### Opcja 2: Docker bezpośrednio

```bash
# Budowanie obrazu
docker build -t ipsc:latest .

# Uruchamianie kontenera
docker run -d \
  --name ipsc-app \
  -p 3001:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Zatrzymanie
docker stop ipsc-app
docker rm ipsc-app
```

#### Zmienne środowiskowe

W `docker-compose.yml` można dostosować:

| Zmienna | Opis | Domyślnie |
|---------|------|----------|
| `PORT` | Port hosta do mapowania | `3001` |
| `CONTAINER_NAME` | Nazwa kontenera Docker | `ipsc-app` |
| `SECRET_KEY` | Klucz sesji Flask (SHA-256) | `default-secret-key-change-me` |

**Przykład:**
```bash
CONTAINER_NAME=my-app PORT=8080 SECRET_KEY="moj-super-tajny-klucz" docker-compose up -d
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

### Panel logowania (Admin)

Dostęp do panelu administracyjnego wymaga zalogowania się.

**Konto domyślne:**
- **Login:** `bartek`
- **Hasło:** `IP$c2023` (ZMIEŃ JE PO PIERWSZYM LOGOWANIU!)

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

#### Tab: Ranking
- **Dodawanie rankingu** — nazwa rankingu + wybór wielu zawodów, które tworzą grupę rankingową
- **Edycja rankingu** — zmiana nazwy oraz przypisanych zawodów
- **Usuwanie rankingu** — możliwe tylko wtedy, gdy ranking nie ma przypisanych zawodów
- **Lista rankingów** — podgląd nazw, liczby zawodów i pełnych przypisań do rankingu

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

Aplikacja wykorzystuje SQLite do przechowywania zawodów i zarządzania użytkownikami.

### Konfiguracja instancji (`data/config.json`)

Każda instancja automatycznie generuje unikalny ID przy pierwszym uruchomieniu i zapisuje go w pliku konfiguracyjnym:

```json
{
  "instance_id": "a1b2c3d4",
  "created_at": "2026-03-26T10:30:00"
}
```

**Pole konfiguracji:**
- **instance_id** — losowy 8-znakowy identyfikator (pierwsze 8 znaków UUID, np. `"a1b2c3d4"`)
- **created_at** — znacznik czasu pierwszego uruchomienia instancji

**Nazwanie bazy danych:**

Baza danych jest automatycznie tworzona w folderze `data/` z nazwą opartą na `instance_id` z `config.json`:

```
data/{instance_id}.db
```

Na przykład, jeśli `instance_id = "a1b2c3d4"`, baza będzie: `data/a1b2c3d4.db`

Plik `config.json` **persysty** między restartami kontenera (znajduje się w tomie Docker), dlatego wszystkie dane pozostają nienaruszone.
To rozwiązanie pozwala na uruchomienie kilka instancji na jednym VPSie bez konfliktów — każda ma swoją bazę danych z unikalną nazwą.

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

### Tabela: `rankings`

```sql
CREATE TABLE rankings (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
)
```

- **id** — unikalny identyfikator rankingu
- **name** — nazwa grupy rankingowej
- **created_at** — znacznik czasu utworzenia
- **updated_at** — znacznik czasu ostatniej edycji

### Tabela: `ranking_matches`

```sql
CREATE TABLE ranking_matches (
  ranking_id INTEGER NOT NULL,
  match_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (ranking_id, match_id)
)
```

- **ranking_id** — powiązanie z tabelą `rankings`
- **match_id** — powiązanie z tabelą `matches`
- **created_at** — znacznik czasu przypisania zawodów do rankingu

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
- `list_rankings()` — zwraca listę rankingów z przypisanymi zawodami
- `add_ranking(name, match_ids)` — tworzy ranking i przypisuje zawody
- `update_ranking(ranking_id, name, match_ids)` — aktualizuje ranking i jego przypisania
- `delete_ranking(ranking_id)` — usuwa pusty ranking

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
| `/admin/rankings` | POST | Dodanie rankingu |
| `/admin/rankings/<id>` | POST | Edycja rankingu |
| `/admin/rankings/<id>/delete` | POST | Usunięcie pustego rankingu |
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

## Licencja

Niniejsze oprogramowanie jest udostępniane **za darmo** na zasadzie "jest jaki jest". Pełne warunki licencji dostępne są w pliku [LICENSE.md](LICENSE.md).

### Ważne:
- **Brak gwarancji** — autor nie odpowiada za żadne błędy lub szkody
- **Każdy użytkownik** korzysta z oprogramowania **na własną odpowiedzialność**
- **Wymóg zachowania** — sekcja "Śledź nas w mediach społecznych" musi pozostać na głównej stronie aplikacji

Dostępna również [wersja angielska licencji](LICENSE_EN.md).