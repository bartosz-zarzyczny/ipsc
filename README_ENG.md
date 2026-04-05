# IPSC — IPSC Results

A tool for extracting and viewing IPSC shooting competition results from WinMSS `.cab` files.

## Project Structure

```
├── WinMSS.cab                    # File with competition data (WinMSS export)
├── data/                         # Folder with database and configuration (persistent in Docker)
│   ├── config.json               # Auto-generated instance configuration
│   └── {instance_id}.db          # SQLite database (uniquely named for each instance)
├── winmss_results.py             # CLI script – results in terminal / CSV export
├── app.py                        # Flask server – browser UI
├── database.py                   # Database layer (ORM)
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Container specification
├── .env                          # Environment variables (SECRET_KEY – do NOT commit to repo)
├── .env_copy                     # Template for .env (copy as .env and fill in)
├── static/i18n/                  # Translation files (multilingual support)
└── templates/
    ├── index.html                # Frontend (results browser)
    ├── admin.html                # Admin panel (competitions + rankings + users)
    └── admin_login.html          # Login form
```

## Requirements

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — for extracting `.cab` files
  ```bash
  brew install cabextract   # macOS
  ```

## Running the Application

### Locally (without Docker)

```bash
python3 app.py
# → browser will open at http://localhost:5000
```

### In Docker Container

#### Option 1: Docker Compose (recommended)

```bash
# Default instance – port 3000, default container name
docker-compose up --build

# Or in background
docker-compose up -d
```

**Running multiple instances on one VPS:**

To avoid conflicts between instances, use the `-p` flag (project-name). Each project must have a unique name:

```bash
# Instance 1 – port 3001, project ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 DATA_DIR=./data-3001 docker-compose -p ipsc1 up -d

# Instance 2 – port 3002, project ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 DATA_DIR=./data-3002 docker-compose -p ipsc2 up -d

# Instance 3 – port 3003, project ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 DATA_DIR=./data-3003 docker-compose -p ipsc3 up -d
```

**Managing instances:**

```bash
# Display all running containers
docker ps

# Stop specific instance
docker-compose -p ipsc1 down

# View instance logs
docker-compose -p ipsc1 logs -f

# Restart specific instance
docker-compose -p ipsc1 restart
```

**Why use `-p` flag:**

The `-p` flag isolates each project with its containers, networks, and volumes. Without it, all instances share the same project-name, leading to conflicts and preventing multiple instances from running simultaneously.

Each instance automatically creates:
- Unique `config.json` (instance ID)
- Unique database (`data/{instance_id}.db`)
- Separate data without conflicts

The database (`{instance_id}.db`) will be stored in the `./data/` directory on the host and **persists between restarts**.

#### Option 2: Docker directly

```bash
# Build image
docker build -t ipsc:latest .

# Run container
docker run -d \
  --name ipsc-app \
  -p 3000:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Stop
docker stop ipsc-app
docker rm ipsc-app
```

#### Environment Variables

In `docker-compose.yml` you can customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Host port for mapping | `3000` |
| `DATA_DIR` | Data directory for database | `./data` |
| `CONTAINER_NAME` | Docker container name | `ipsc-app` |
| `SECRET_KEY` | Flask session key (**required**) | — no default; set in `.env` |

**Example:**
```bash
CONTAINER_NAME=my-app PORT=8080 DATA_DIR=./data-custom SECRET_KEY="my-super-secret-key" docker-compose up -d
```

**How to generate `SECRET_KEY` for `.env`:**
```bash
openssl rand -hex 32
# or
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Then put the result into `.env` in this format:
```dotenv
SECRET_KEY=your_generated_value_here
```

## CLI Script (`winmss_results.py`)

Extracts data from `.cab` file and displays results in terminal.

```bash
# Overall summary + tables per division
python3 winmss_results.py

# Overall summary only
python3 winmss_results.py --overall

# With stage details
python3 winmss_results.py --stages

# Ranking per stage (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Export to CSV (Excel compatible)
python3 winmss_results.py --csv results.csv

# Different .cab file
python3 winmss_results.py other_match.cab --csv results.csv
```

## Web Interface (`app.py`)

### Admin Login Panel

Access to the admin panel requires login.

**Default account:**
- **Username:** `bartek`
- **Password:** `IP$c2023` (CHANGE IT AFTER FIRST LOGIN!)

User accounts are stored in SQLite database (`{instance_id}.db`) with PBKDF2-SHA256 protection.

### Main Page — Results Browser

#### Basic Features
- **Match selection** — list of saved matches in database; click loads results
- **Match header** — name, date, level (L1/L2/L3), number of stages and competitors
- **Podium** — top 3 cards with Hit Factor / points / time
- **Overall standings** — sortable table of all competitors; click row expands stage details (A/B/C/D/M/PE, HF, % in division)
- **Divisions tab** — separate tables per division with ranking and % to division leader
- **Stages tab** — ranking on selected stage with colored shooting columns; percentages calculated within divisions

#### New Features

**🌐 Multilingual Support**
- Language selector in top right corner (PL, EN, DE, FR, CZ)
- Automatic interface translation
- Language files in `static/i18n/` folder

**🔍 Advanced Filtering**
- **Search** — by competitor's last name or first name
- **Division filter** — ability to select one or multiple divisions simultaneously
- **Category filter** — Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady
- **Scope** — filters work on all tabs (Overall, Divisions, Stages)
- **Automatic recalculation** — percentages recalculated for filtered group

**📊 Results Export**
- **📄 PDF Export** — new PDF generation functionality
  - Divided by divisions (each division on separate page)
  - Colored division headers (Open-red, Standard-blue, Modified-green)
  - Landscape orientation for better readability
  - Highlighting of places 1-3 (gold/silver/bronze)
  - Support for both individual matches and rankings
- **📊 CSV Export** — generated browser-side, Excel compatible (UTF-8 with BOM)

**🎨 Division Coloring**
- Standard IPSC colors for divisions throughout interface
- Visual division distinction in tables and headers

### Admin Panel

Available at `/admin` — requires login.

#### Tab: Matches
- **File upload** — drag & drop or click on form; automatic detection of `WinMSS.cab` in current directory
- **Match list** — table of all saved matches (ID, name, date, level)
- **Delete matches** — buttons to delete individual matches from database

#### Tab: Competitors
- **Edit competitor data** — select matches, then edit for each competitor:
  - First and last name
  - Category (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Competitor list** — tabular view of all competitors from matches
- **Save changes** — "Save" button for each competitor, changes immediately affect rankings

#### Tab: Rankings
- **Add ranking** — ranking name + selection of multiple matches that form ranking group
- **Edit ranking** — change name and assigned matches
- **Delete ranking** — possible only when ranking has no assigned matches
- **Rankings list** — view names, number of matches and full ranking assignments

#### ⚙️ Tab: Division Mapping (NEW!)

New functionality allowing mapping of imported division names to standard IPSC divisions.

**Features:**
- **Match selection** — selector for matches to map divisions
- **Automatic detection** — system automatically collects all unique division names from imported matches
- **Standard mapping** — ability to assign each imported division to one of standard IPSC divisions
- **Copy mappings** — ability to copy all mappings from one match to another
- **Standard divisions** supported:
  - **Pistols:** Open, Standard, Standard Manual, Modified, Classic, Revolver, Optics
  - **Rifles:** Mini Rifle, Production, Production Optics, PCC Optics, PCC Standard
  - **Shotgun:** Rifle Open, Rifle Standard
  - **Specialized:** PC Optic

**API endpoints:**
- `GET /admin/api/divisions-mapping` — get all mappings and available divisions
- `POST /admin/api/divisions-mapping` — create/update/delete mapping

**Benefits:**
- Unification of division names between different matches
- Better management of inter-match rankings
- Automatic application of mappings in results and rankings

#### Tab: Users
- **Change password** — form to change logged user's password (requires old password)

## Competitor Data

| Field | Description |
|-------|-------------|
| Place | Overall ranking (based on HF) |
| No | Start number |
| Last Name First Name | Competitor data |
| Division | Open / Standard / Standard Manual / Modified |
| Category | Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady |
| Points Total | Sum of points from all stages |
| Time Total | Sum of times |
| Overall HF | Hit Factor = points / time |
| % Leader | Percentage to best HF |

## Database (`database.py`)

Application uses SQLite to store matches and manage users.

### New tables for division mapping

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

**Fields in `division_mappings` table:**
- **match_id** — match ID for which mapping applies
- **source_division** — original division name from import
- **mapped_division_id** — standard IPSC division ID
- **mapped_division_color** — division color (hex)

### Functions for managing division mapping

- `get_division_mapping(match_id, source_division)` — get mapping for division
- `set_division_mapping(match_id, source_division, mapped_id, color)` — set mapping
- `get_all_division_mappings(match_id)` — get all mappings for match
- `copy_division_mappings(source_match_id, target_match_id)` — copy mappings
- `apply_division_mappings(data, match_id)` — apply mappings in results data

---

## Latest Updates (2026)

### v2.4 - Division Mapping and PDF Export
- ✅ **PDF Export** — export results to PDF divided by divisions  
- ✅ **Division Mapping** — intelligent mapping of imported divisions to IPSC standards
- ✅ **Multilingual Support** — support for 5 languages (PL, EN, DE, FR, CZ)
- ✅ **Division Coloring** — standard IPSC colors in interface
- ✅ **Advanced Filtering** — multi-select filters for divisions and categories
- ✅ **Automatic Recalculation** — percentages for filtered groups

## Multilingual Support

The application supports dynamic language switching without page reload. Available languages:

- 🇵🇱 Polish
- 🇬🇧 English  
- 🇩🇪 German
- 🇨🇿 Czech
- 🇫🇷 French

Detailed documentation on multilingual implementation is available in [MULTILINGUALITY_ENG.md](MULTILINGUALITY_ENG.md).

## License

This software is provided **free of charge** on an "as is" basis. Full license terms are available in [LICENSE_EN.md](LICENSE_EN.md).

### Important:
- **No warranty** — author is not responsible for any errors or damages
- **Each user** uses the software **at their own risk**  
- **Requirement to maintain** — "Follow us on social media" section must remain on the main application page

Also available in [Polish license version](LICENSE.md).
docker-compose up -d
```

**Running multiple instances on a single VPS:**

To avoid conflicts between instances, use the `-p` flag (project-name). Each project must have a unique name:

```bash
# Instance 1 – port 3001, project ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 docker-compose -p ipsc1 up -d

# Instance 2 – port 3002, project ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 docker-compose -p ipsc2 up -d

# Instance 3 – port 3003, project ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 docker-compose -p ipsc3 up -d
```

**Managing instances:**

```bash
# List all running containers
docker ps

# Stop a specific instance
docker-compose -p ipsc1 down

# View instance logs
docker-compose -p ipsc1 logs -f

# Restart a specific instance
docker-compose -p ipsc1 restart
```

**About the `-p` flag:**

The `-p` flag isolates each project with its own containers, networks, and volumes. Without it, all instances share the same project-name, which causes conflicts and prevents running multiple instances simultaneously.

Each instance will automatically create:
- Unique `config.json` (instance ID)
- Unique database (`data/{instance_id}.db`)
- Separate data without conflicts

The database (`{instance_id}.db`) will be stored in the `./data/` directory on the host and **persists between restarts**.

#### Option 2: Docker directly

```bash
# Building the image
docker build -t ipsc:latest .

# Running the container
docker run -d \
  --name ipsc-app \
  -p 3001:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Stopping
docker stop ipsc-app
docker rm ipsc-app
```

#### Environment Variables

In `docker-compose.yml` you can customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Host port mapping | `3001` |
| `CONTAINER_NAME` | Docker container name | `ipsc-app` |
| `SECRET_KEY` | Flask session key (**required**) | — no default; set in `.env` |

**Example:**
```bash
CONTAINER_NAME=my-app PORT=8080 SECRET_KEY="my-super-secret-key" docker-compose up -d
```

## CLI Script (`winmss_results.py`)

Extracts data from `.cab` file and displays results in terminal.

```bash
# Overall summary + tables per division
python3 winmss_results.py

# Overall summary only
python3 winmss_results.py --overall

# With stage details
python3 winmss_results.py --stages

# Ranking on each stage (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Export to CSV (openable in Excel)
python3 winmss_results.py --csv results.csv

# Different .cab file
python3 winmss_results.py other_match.cab --csv results.csv
```

## Web Interface (`app.py`)

### Admin Login Panel

Access to the admin panel requires login.

**Default account:**
- **Login:** `admin`
- **Password:** randomly generated on first launch — printed once in the logs.

```bash
# View the startup password:
docker-compose logs | grep "startowe"
```

> Change your password after first login: Admin panel → Users tab.

User accounts are stored in SQLite database with SHA-256 hashing.

### Main Page — Results Browser

#### Basic Features
- **Competition Selection** — list of saved competitions in database; clicking loads results
- **Competition Header** — name, date, level (L1/L2/L3), number of stages and competitors
- **Podium** — cards of top 3 with Hit Factor / points / time
- **Overall Summary** — sortable table of all competitors; clicking row expands stage details (A/B/C/D/M/PE, HF, % in division)
- **Divisions Tab** — separate tables per division with ranking and % to division leader
- **Stages Tab** — ranking on selected stage with colored shot columns; percentages calculated within division

#### New Features

**🌐 Multilingual Support**
- Language selector in top-right corner (PL, EN, DE, FR, CZ)
- Automatic interface translation
- Language files in `static/i18n/` folder

**🔍 Advanced Filtering**
- **Search** — by competitor's last name or first name
- **Division Filter** — ability to select one or multiple divisions simultaneously
- **Category Filter** — Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady
- **Scope** — filters work on all tabs (Overall, Divisions, Stages)
- **Automatic Recalculation** — percentages recalculated for filtered groups

**📊 Results Export**
- **📄 PDF Export** — new functionality for generating results in PDF
  - Division-based separation (each division on separate page)
  - Colored division headers (Open-red, Standard-blue, Modified-green)
  - Landscape orientation for better readability
  - Highlighting of places 1-3 (gold/silver/bronze)
  - Support for both individual competitions and rankings
- **📊 CSV Export** — generated client-side, openable in Excel (UTF-8 with BOM)

**🎨 Division Coloring**
- Standard IPSC colors for divisions throughout the interface
- Visual distinction of divisions in tables and headers

### Admin Panel

Available at `/admin` — requires login.

#### Tab: Competitions
- **File Upload** — drag & drop or click form; auto-detects `WinMSS.cab` in current directory
- **Competitions List** — table of all saved competitions (ID, name, date, level)
- **Delete Competitions** — buttons to delete individual competitions from database

#### Tab: Competitors
- **Edit competitor data** — select competition, then edit for each competitor:
  - First name and last name
  - Category (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Competitors List** — tabular overview of all competitors from the competition
- **Save changes** — "Save" button for each competitor, changes immediately affect rankings

#### Tab: Rankings
- **Create ranking** — ranking name plus multi-select of competitions that form the ranking group
- **Edit ranking** — change the name and assigned competitions
- **Delete ranking** — available only when the ranking has no assigned competitions
- **Rankings list** — overview of names, competition counts, and full assignments

#### ⚙️ Tab: Division Mapping (NEW!)

New functionality allowing mapping of imported division names to standard IPSC divisions.

**Features:**
- **Competition Selection** — selector for competitions to map divisions
- **Automatic Detection** — system automatically collects all unique division names from imported competitions
- **Mapping to Standards** — ability to assign each imported division to one of the standard IPSC divisions
- **Copying Mappings** — ability to copy all mappings from one competition to another
- **Standard Divisions** supported:
  - **Pistols:** Open, Standard, Standard Manual, Modified, Classic, Revolver, Optics
  - **Rifles:** Mini Rifle, Production, Production Optics, PCC Optics, PCC Standard
  - **Shotgun:** Karabin Open, Karabin Standard
  - **Specialized:** PC Optic

**API endpoints:**
- `GET /admin/api/divisions-mapping` — get mappings for competitions
- `POST /admin/api/divisions-mapping` — save/delete division mapping
- `POST /admin/api/divisions-mapping/copy` — copy mappings between competitions

**Benefits:**
- Standardization of division names between different competitions
- Better management of inter-competition rankings
- Automatic application of mappings in results and rankings

#### Tab: Users
- **Change Password** — form to change logged-in user's password (requires old password)

### Competitor Data

| Field | Description |
|-------|-------------|
| Place | Overall ranking (overall HF) |
| No. | Start number |
| Last Name First Name | Competitor data |
| Division | Open / Standard / Standard Manual / Modified |
| Category | Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady |
| Total Points | Sum of points from all stages |
| Total Time | Sum of times |
| HF Overall | Hit Factor = points / time |
| % of Leader | Percent to best HF |

## Database (`database.py`)

The application uses SQLite to store competitions and manage users.

### Instance Configuration (`data/config.json`)

Each instance automatically generates a unique ID on first run and saves it to a configuration file:

```json
{
  "instance_id": "a1b2c3d4",
  "created_at": "2026-03-26T10:30:00"
}
```

**Configuration Fields:**
- **instance_id** — random 8-character identifier (first 8 characters of UUID, e.g. `"a1b2c3d4"`)
- **created_at** — timestamp of instance first run

**Database Naming:**

The database is automatically created in the `data/` folder with a name based on the `instance_id` from `config.json`:

```
data/{instance_id}.db
```

For example, if `instance_id = "a1b2c3d4"`, the database will be: `data/a1b2c3d4.db`

The `config.json` file **persists** between container restarts (located in Docker volume), so all data remains intact.
This solution allows running multiple instances on one VPS without conflicts — each has its own database with a unique name.

### Table: `matches`

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

- **id** — unique competition identifier
- **name** — competition name (from THEMATCH.XML)
- **date** — date (YYYY-MM-DD)
- **level** — level (1-3)
- **data_json** — full JSON data (structured results, stages, competitors)
- **created_at** — timestamp of addition

### Table: `rankings`

```sql
CREATE TABLE rankings (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
)
```

- **id** — unique ranking identifier
- **name** — ranking group name
- **created_at** — creation timestamp
- **updated_at** — last edit timestamp

### Table: `ranking_matches`

```sql
CREATE TABLE ranking_matches (
  ranking_id INTEGER NOT NULL,
  match_id INTEGER NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (ranking_id, match_id)
)
```

- **ranking_id** — reference to `rankings`
- **match_id** — reference to `matches`
- **created_at** — assignment timestamp

### New Tables for Division Mapping

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

**Fields of `division_mappings` table:**
- **match_id** — ID of competition for which mapping is applied
- **source_division** — original division name from import
- **mapped_division_id** — ID of standard IPSC division
- **mapped_division_color** — division color (hex)

### Division Mapping Management Functions

- `get_division_mapping(match_id, source_division)` — get mapping for division
- `set_division_mapping(match_id, source_division, mapped_id, color)` — set mapping
- `get_all_division_mappings(match_id)` — get all mappings for competition
- `copy_division_mappings(source_match_id, target_match_id)` — copy mappings
- `apply_division_mappings(data, match_id)` — apply mappings to result data

---

## Latest Updates (2026)

### v2.4 - Division Mapping and PDF Export
- ✅ **PDF Export** — export results to PDF with division separation
- ✅ **Division Mapping** — intelligent mapping of imported divisions to IPSC standards
- ✅ **Multilingual Support** — support for 5 languages (PL, EN, DE, FR, CZ)
- ✅ **Division Coloring** — standard IPSC colors in interface
- ✅ **Advanced Filtering** — multi-select filters for divisions and categories
- ✅ **Automatic Recalculation** — percentages for filtered groups

### Table: `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
)
```

- **id** — unique user identifier
- **username** — login (unique)
- **password_hash** — SHA-256 hash of password
- **created_at** — timestamp of creation

**Functions:**
- `add_user(username, password_hash)` — creates user
- `verify_user(username, password_hash)` — verifies password (timing-safe comparison)
- `list_users()` — retrieves list of all users
- `delete_user(user_id)` — deletes user (prevents deletion of last user)
- `change_password(user_id, password_hash)` — changes password
- `list_rankings()` — returns rankings with assigned competitions
- `add_ranking(name, match_ids)` — creates a ranking and assigns competitions
- `update_ranking(ranking_id, name, match_ids)` — updates a ranking and its assignments
- `delete_ranking(ranking_id)` — deletes an empty ranking

## API Routes

### Public

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Main page (results browser) |

### Logged-in User (admin)

| Route | Method | Description |
|-------|--------|-------------|
| `/admin` | GET | Admin panel |
| `/admin/login` | GET, POST | Login |
| `/admin/logout` | GET | Logout |
| `/admin/upload` | POST | Upload .cab file |
| `/admin/delete/<id>` | POST | Delete competition |
| `/admin/rankings` | POST | Create a ranking |
| `/admin/rankings/<id>` | POST | Edit a ranking |
| `/admin/rankings/<id>/delete` | POST | Delete an empty ranking |
| `/admin/api/competitors/<match_id>` | GET | List competitors from competition (JSON) |
| `/admin/api/competitors/<match_id>` | POST | Edit competitor's name, last name, category |
| `/admin/api/competitors/<match_id>/<comp_id>` | DELETE | Delete competitor from competition |
| `/admin/users` | GET | List users (JSON API) |
| `/admin/users` | POST | Create user |
| `/admin/users/<id>` | POST | Delete user |
| `/admin/change-password` | POST | Change password |

### Data API (JSON)

| Route | Method | Description |
|-------|--------|-------------|
| `/api/matches` | GET | List of available competitions |
| `/api/match/<id>` | GET | Data of specific competition |

## Division Mapping (Shotgun)

| DivId | Division |
|-------|----------|
| 10 | Open |
| 11 | Standard |
| 12 | Standard Manual |
| 13 | Modified |

Mapping can be changed in `winmss_results.py` → `DIVISION_NAMES` dictionary.

## Category Mapping (WinMSS)

| CatId | Category |
|-------|----------|
| 0 | (empty) |
| 1 | Lady |
| 2 | Junior |
| 3 | Senior |
| 4 | Super Senior |
| 5 | Super Junior |

**Additional categories supported by the system (without WinMSS mapping):**
- Grand Senior
- Senior Lady

Categories can be edited or assigned manually in the admin panel (Tab: Competitors).

Mapping can be changed in `winmss_results.py` → `CATEGORY_NAMES` dictionary.

## XML Files in `.cab` Archive

| File | Content |
|------|---------|
| `THEMATCH.XML` | Competition data (name, date, level) |
| `MEMBER.XML` | Competitor database |
| `ENROLLED.XML` | Competition registration (division, category, squad) |
| `STAGE.XML` | Stage definitions (name, max points, type) |
| `SCORE.XML` | Shooting results (A/B/C/D/M/PE, time, HF) |
| `CLUB.XML` | Clubs |
| `SQUAD.XML` | Squads |
| `TEAM.XML` | Teams |
| `CLASSIFY.XML` | Competitor classifications |
| `TAG.XML` | Tags (e.g. RO) |

## Multilingual Support

The application supports dynamic language switching without page reload. Available languages:

- 🇵🇱 Polski
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇨🇿 Čeština
- 🇫🇷 Français

Detailed documentation about multilingual support is available in the [MULTILINGUALITY_ENG.md](MULTILINGUALITY_ENG.md) file.

## License

This software is provided **free of charge** on an "as-is" basis. Full license terms are available in the [LICENSE_EN.md](LICENSE_EN.md) file.

### Important:
- **No warranty** — the author is not responsible for any errors or damages
- **Each user** uses the software **at their own risk**
- **Requirement to maintain** — the "Follow us on social media" section must remain on the application's main page

A [Polish version of the license](LICENSE.md) is also available.
