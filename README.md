# IPSC — Wyniki IPSC

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
├── .env                          # Zmienne środowiskowe (SECRET_KEY – NIE commitować do repo)
├── .env_copy                     # Szablon pliku .env (skopiuj jako .env i uzupełnij)
├── static/i18n/                  # Pliki tłumaczeń (wielojęzyczność)
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
| `SECRET_KEY` | Klucz sesji Flask (**wymagany**) | — brak domyślnego; ustaw w `.env` |

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
- **Login:** `admin`
- **Hasło:** generowane losowo przy pierwszym uruchomieniu — wypisywane jednorazowo w logach.

```bash
# Podejrzyj hasło startowe:
docker-compose logs | grep "Hasło startowe"
```

> Zmień hasło po pierwszym logowaniu: panel Admin → zakładka Użytkownicy.

Konta użytkowników przechowywane są w bazie danych SQLite (`ipsc.db`) z zabezpieczeniem PBKDF2-SHA256.

### Główna strona — przeglądarka wyników

#### Podstawowe funkcjonalności
- **Wybór zawodów** — lista zapisanych zawodów w bazie; kliknięcie ładuje wyniki
- **Nagłówek zawodów** — nazwa, data, poziom (L1/L2/L3), liczba torów i zawodników
- **Podium** — karty top 3 z Hit Factor / punktami / czasem
- **Zestawienie ogólne** — sortowalna tabela wszystkich zawodników; kliknięcie wiersza rozwija szczegóły torów (A/B/C/D/M/PE, HF, % w dywizji)
- **Zakładka Dywizje** — osobne tabele per dywizja z rankingiem i % do lidera dywizji
- **Zakładka Tory** — ranking na wybranym torze z kolorowanymi kolumnami strzelań; procenty liczone w ramach dywizji

#### Nowe funkcjonalności

**🌐 Wielojęzyczność**
- Selektor języka w prawym górnym rogu (PL, EN, DE, FR, CZ)
- Automatyczne tłumaczenie interfejsu
- Pliki językowe w folderze `static/i18n/`

**🔍 Zaawansowane filtrowanie**
- **Wyszukiwanie** — po nazwisku lub imieniu zawodnika
- **Filtr dywizji** — możliwość wyboru jednej lub wielu dywizji jednocześnie
- **Filtr kategorii** — Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady
- **Zakres działania** — filtry działają na wszystkich zakładkach (Ogólne, Dywizje, Tory)
- **Automatyczna recalkulacja** — percentages przeliczane na nowo dla przefiltrowanej grupy

**📊 Eksport wyników**
- **📄 PDF Export** — nowa funkcjonalność generowania wyników w PDF
  - Podział na dywizje (każda dywizja na osobnej stronie)
  - Kolorowe nagłówki dywizji (Open-czerwony, Standard-niebieski, Modified-zielony)
  - Orientacja pozioma dla lepszej czytelności
  - Highlighting miejsc 1-3 (złoty/srebrny/brązowy)
  - Obsługa zarówno pojedynczych zawodów jak i rankingów
- **📊 CSV Export** — generowany po stronie przeglądarki, otwieralny w Excelu (UTF-8 z BOM)

**🎨 Kolorowanie dywizji**
- Standardowe kolory IPSC dla dywizji w całym interfejsie
- Wizualne rozróżnienie dywizji w tabelach i nagłówkach

### Panel administracyjny

Dostępny pod `/admin` — wymaga zalogowania.

#### Tab: Zawody
- **Wgrywanie pliku** — drag & drop lub klik na formularz; automatyczne wykrywanie `WinMSS.cab` w bieżącym katalogu
- **Lista zawodów** — tabela wszystkich zapisanych zawodów (ID, nazwa, data, poziom)
- **Usuwanie zawodów** — przyciski do usunięcia pojedynczych zawodów z bazy

#### Tab: Zawodnicy
- **Edycja danych zawodnika** — wybór zawodów, następnie edycja dla każdego zawodnika:
  - Imię i nazwisko
  - Kategoria (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Lista zawodników** — tabelaryczny przegląd wszystkich zawodników z zawodów
- **Zapisywanie zmian** — przycisk "Zapisz" dla każdego zawodnika, zmiany natychmiast wpływają na rankingi

#### Tab: Ranking
- **Dodawanie rankingu** — nazwa rankingu + wybór wielu zawodów, które tworzą grupę rankingową
- **Edycja rankingu** — zmiana nazwy oraz przypisanych zawodów
- **Usuwanie rankingu** — możliwe tylko wtedy, gdy ranking nie ma przypisanych zawodów
- **Lista rankingów** — podgląd nazw, liczby zawodów i pełnych przypisań do rankingu

#### ⚙️ Tab: Mapowanie Dywizji (NOWE!)

Nowa funkcjonalność umożliwiająca mapowanie importowanych nazw dywizji na standardowe dywizje IPSC.

**Funkcjonalności:**
- **Wybór zawodów** — selektor zawodów do mapowania dywizji
- **Automatyczne wykrywanie** — system automatycznie zbiera wszystkie unikalne nazwy dywizji z zaimportowanych zawodów
- **Mapowanie na standardy** — możliwość przypisania każdej importowanej dywizji do jednej ze standardowych dywizji IPSC
- **Kopiowanie mapowań** — możliwość skopiowania wszystkich mapowań z jednych zawodów do drugich
- **Standardowe dywizje** obsługiwane:
  - **Pistolety:** Open, Standard, Standard Manual, Modified, Classic, Rewolwer, Optics
  - **Karabiny:** Mini Rifle, Production, Production Optics, PCC Optics, PCC Standard
  - **Shotgun:** Karabin Open, Karabin Standard
  - **Specjalistyczne:** PC Optic

**API endpoints:**
- `GET /admin/api/divisions-mapping` — pobierz mapowania dla zawodów
- `POST /admin/api/divisions-mapping` — zapisz/usuń mapowanie dywizji
- `POST /admin/api/divisions-mapping/copy` — kopiuj mapowania między zawodami

**Korzyści:**
- Ujednolicenie nazw dywizji między różnymi zawodami
- Lepsze zarządzanie rankingami międzyzawodowymi
- Automatyczne stosowanie mapowań w wynikach i rankingach

#### Tab: Użytkownicy
- **Zmiana hasła** — formularz do zmiany hasła zalogowanego użytkownika (wymaga starego hasła)

## Dane zawodników

| Pole | Opis |
|------|------|
| Miejsce | Ranking ogólny (na podstawie HF) |
| Nr | Numer startowy |
| Nazwisko Imię | Dane zawodnika |
| Dywizja | Open / Standard / Standard Manual / Modified |
| Kategoria | Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady |
| Punkty Total | Suma punktów ze wszystkich torów |
| Czas Total | Suma czasów |
| HF Ogólny | Hit Factor = punkty / czas |
| % Lidera | Procent do najlepszego HF |

## Baza danych (`database.py`)

Aplikacja wykorzystuje SQLite do przechowywania zawodów i zarządzania użytkownikami.

### Nowe tabele dla mapowania dywizji

```sql
CREATE TABLE division_mappings (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL,
    source_division TEXT NOT NULL,
    mapped_division_id TEXT,
    mapped_division_color TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE,
    UNIQUE(match_id, source_division)
)
```

**Pola tabeli `division_mappings`:**
- **match_id** — ID zawodów, dla których stosowane jest mapowanie
- **source_division** — oryginalna nazwa dywizji z importu
- **mapped_division_id** — ID standardowej dywizji IPSC
- **mapped_division_color** — kolor dywizji (hex)

### Funkcje do zarządzania mapowaniem dywizji

- `get_division_mapping(match_id, source_division)` — pobierz mapowanie dla dywizji
- `set_division_mapping(match_id, source_division, mapped_id, color)` — ustaw mapowanie
- `get_all_division_mappings(match_id)` — pobierz wszystkie mapowania dla zawodów
- `copy_division_mappings(source_match_id, target_match_id)` — kopiuj mapowania
- `apply_division_mappings(data, match_id)` — zastosuj mapowania w danych wyników

---

## Ostatnie aktualizacje (2026)

### v2.4 - Mapowanie Dywizji i PDF Export
- ✅ **PDF Export** — export wyników do PDF z podziałem na dywizje
- ✅ **Mapowanie Dywizji** — inteligentne mapowanie importowanych dywizji na standardy IPSC
- ✅ **Wielojęzyczność** — obsługa 5 języków (PL, EN, DE, FR, CZ)
- ✅ **Kolorowanie dywizji** — standardowe kolory IPSC w interfejsie
- ✅ **Zaawansowane filtrowanie** — multi-select filtrów dywizji i kategorii
- ✅ **Automatyczna recalkulacja** — percentages dla przefiltrowanych grup

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
| `SECRET_KEY` | Klucz sesji Flask (**wymagany**) | — brak domyślnego; ustaw w `.env` |

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

Konta użytkowników przechowywane są w bazie danych SQLite (`ipsc.db`) z zabezpieczeniem PBKDF2-SHA256.

### Główna strona — przeglądarka wyników

- **Wybór zawodów** — lista zapisanych zawodów w bazie; kliknięcie ładuje wyniki
- **Nagłówek zawodów** — nazwa, data, poziom (L1/L2/L3), liczba torów i zawodników
- **Podium** — karty top 3 z Hit Factor / punktami / czasem
- **Zestawienie ogólne** — sortowalna tabela wszystkich zawodników; kliknięcie wiersza rozwija szczegóły torów (A/B/C/D/M/PE, HF, % w dywizji)
- **Zakładka Dywizje** — osobne tabele per dywizja z rankingiem i % do lidera dywizji
- **Zakładka Tory** — ranking na wybranym torze z kolorowanymi kolumnami strzelań; procenty liczone w ramach dywizji
- **Filtry** — wyszukiwanie po nazwisku, filtr po dywizji, filtr po kategorii (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady); filtry działają na wszystkich zakładkach włącznie z torami
- **Recalkulacja percentages** — gdy kategoria filtrowana, percentages automatycznie przeliczane na 100% dla lidera tej kategorii w danej dywizji
- **Eksport CSV** — generowany po stronie przeglądarki, otwieralny w Excelu (UTF-8 z BOM)
- **Link do panelu** — przycisk w górnym rogu odsyła do `/admin`

### Panel administracyjny

Dostępny pod `/admin` — wymaga zalogowania.

#### Tab: Zawody
- **Wgrywanie pliku** — drag & drop lub klik na formularz; automatyczne wykrywanie `WinMSS.cab` w bieżącym katalogu
- **Lista zawodów** — tabela wszystkich zapisanych zawodów (ID, nazwa, data, poziom)
- **Usuwanie zawodów** — przyciski do usunięcia pojedynczych zawodów z bazy

#### Tab: Zawodnicy
- **Edycja danych zawodnika** — wybór zawodów, następnie edycja dla każdego zawodnika:
  - Imię i nazwisko
  - Kategoria (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Lista zawodników** — tabelariczny przegląd wszystkich zawodników z zawodów
- **Zapisywanie zmian** — przycisk "Zapisz" dla każdego zawodnika, zmiany natychmiast wpływają na rankingi

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
| Kategoria | Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady |
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
| `/admin/api/competitors/<match_id>` | GET | Lista zawodników z zawodów (JSON) |
| `/admin/api/competitors/<match_id>` | POST | Edycja imienia, nazwiska, kategorii zawodnika |
| `/admin/api/competitors/<match_id>/<comp_id>` | DELETE | Usunięcie zawodnika z zawodów |
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

## Mapowanie kategorii (WinMSS)

| CatId | Kategoria |
|-------|-----------|
| 0 | (pusta) |
| 1 | Lady |
| 2 | Junior |
| 3 | Senior |
| 4 | Super Senior |
| 5 | Super Junior |

**Dodatkowe kategorie wspierane przez system (bez mapowania z WinMSS):**
- Grand Senior
- Senior Lady

Kategorie można edytować lub przypisywać ręcznie w panelu administracyjnym (Tab: Zawodnicy).

Mapowanie można zmienić w `winmss_results.py` → słownik `CATEGORY_NAMES`.

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

## Wielojęzyczność

Aplikacja wspiera dynamiczną zmianę języka bez przeładowania strony. Dostępne są następujące języki:

- 🇵🇱 Polski
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇨🇿 Čeština
- 🇫🇷 Français

Szczegółowa dokumentacja dotycząca implementacji wielojęzyczności dostępna jest w pliku [MULTILINGUALITY.md](MULTILINGUALITY.md).

## Licencja

Niniejsze oprogramowanie jest udostępniane **za darmo** na zasadzie "jest jaki jest". Pełne warunki licencji dostępne są w pliku [LICENSE.md](LICENSE.md).

### Ważne:
- **Brak gwarancji** — autor nie odpowiada za żadne błędy lub szkody
- **Każdy użytkownik** korzysta z oprogramowania **na własną odpowiedzialność**
- **Wymóg zachowania** — sekcja "Śledź nas w mediach społecznych" musi pozostać na głównej stronie aplikacji

Dostępna również [wersja angielska licencji](LICENSE_EN.md).
