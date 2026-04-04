# IPSC — IPSC-Ergebnisse

Ein Tool zum Extrahieren und Anzeigen von IPSC-Schießwettkampfergebnissen aus WinMSS `.cab`-Dateien.

## Projektstruktur

```
├── WinMSS.cab                    # Datei mit Wettkampfdaten (WinMSS-Export)
├── data/                         # Ordner mit Datenbank und Konfiguration (persistent in Docker)
│   ├── config.json               # Automatisch generierte Instanzkonfiguration
│   └── {instance_id}.db          # SQLite-Datenbank (eindeutig benannt pro Instanz)
├── winmss_results.py             # CLI-Skript – Ergebnisse im Terminal / CSV-Export
├── app.py                        # Flask-Server – Browser-Benutzeroberfläche
├── database.py                   # Datenbankebene (ORM)
├── docker-compose.yml            # Docker Compose-Konfiguration
├── Dockerfile                    # Container-Spezifikation
├── static/i18n/                  # Übersetzungsdateien (Mehrsprachigkeit)
└── templates/
    ├── index.html                # Frontend (Ergebnisanzeige)
    ├── admin.html                # Admin-Panel (Wettkämpfe + Rankings + Benutzer)
    └── admin_login.html          # Anmeldeformular
```

## Anforderungen

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — zum Entpacken von `.cab`-Dateien
  ```bash
  brew install cabextract   # macOS
  ```

## Anwendung starten

### Lokal (ohne Docker)

```bash
python3 app.py
# → Browser öffnet sich auf http://localhost:5000
```

### Im Docker-Container

#### Option 1: Docker Compose (empfohlen)

```bash
# Standard-Instanz – Port 3000, Standard-Container-Name
docker-compose up --build

# Oder im Hintergrund
docker-compose up -d
```

**Mehrere Instanzen auf einem VPS ausführen:**

Um Konflikte zwischen Instanzen zu vermeiden, verwenden Sie die `-p`-Flagge (project-name). Jedes Projekt muss einen eindeutigen Namen haben:

```bash
# Instanz 1 – Port 3001, Projekt ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 DATA_DIR=./data-3001 docker-compose -p ipsc1 up -d

# Instanz 2 – Port 3002, Projekt ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 DATA_DIR=./data-3002 docker-compose -p ipsc2 up -d

# Instanz 3 – Port 3003, Projekt ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 DATA_DIR=./data-3003 docker-compose -p ipsc3 up -d
```

**Instanzen verwalten:**

```bash
# Alle laufenden Container anzeigen
docker ps

# Spezifische Instanz stoppen
docker-compose -p ipsc1 down

# Instanz-Logs anzeigen
docker-compose -p ipsc1 logs -f

# Spezifische Instanz neu starten
docker-compose -p ipsc1 restart
```

#### Umgebungsvariablen

In `docker-compose.yml` können Sie anpassen:

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `PORT` | Host-Port für Zuordnung | `3000` |
| `DATA_DIR` | Datenverzeichnis für Datenbank | `./data` |
| `CONTAINER_NAME` | Docker-Container-Name | `ipsc-app` |
| `SECRET_KEY` | Flask-Session-Schlüssel (SHA-256) | `default-secret-key-change-me` |

## CLI-Skript (`winmss_results.py`)

Extrahiert Daten aus `.cab`-Datei und zeigt Ergebnisse im Terminal an.

## Web-Interface (`app.py`)

### Admin-Panel

**Standard-Konto:**
- **Benutzername:** `bartek`
- **Passwort:** `IP$c2023` (NACH ERSTER ANMELDUNG ÄNDERN!)

#### Neue Funktionalitäten

**🌐 Mehrsprachige Unterstützung**
- Sprachauswahl in der oberen rechten Ecke (PL, EN, DE, FR, CZ)
- Automatische Interface-Übersetzung

**📄 PDF-Export**
- Export der Ergebnisse in PDF unterteilt nach Divisionen
- Farbige Divisions-Header nach IPSC-Standards
- Querformat für bessere Lesbarkeit

**⚙️ Divisions-Zuordnung**
- Intelligente Zuordnung importierter Divisions-Namen zu IPSC-Standards
- Standard-Divisionen: Open, Standard, Modified, etc.

## Neueste Updates (2026)

### v2.4 - Divisions-Zuordnung und PDF-Export
- ✅ **PDF-Export** — Export der Ergebnisse in PDF unterteilt nach Divisionen
- ✅ **Divisions-Zuordnung** — intelligente Zuordnung zu IPSC-Standards
- ✅ **Mehrsprachige Unterstützung** — Unterstützung für 5 Sprachen (PL, EN, DE, FR, CZ)
- ✅ **Divisions-Farbgebung** — Standard-IPSC-Farben im Interface
- ✅ **Erweiterte Filterung** — Multi-Select-Filter für Divisionen und Kategorien

## Mehrsprachige Unterstützung

Die Anwendung unterstützt dynamischen Sprachwechsel ohne Seiten-Neuladen. Verfügbare Sprachen:

- 🇵🇱 Polnisch
- 🇬🇧 Englisch
- 🇩🇪 Deutsch
- 🇨🇿 Tschechisch
- 🇫🇷 Französisch

Detaillierte Dokumentation zur mehrsprachigen Implementierung ist verfügbar in [MULTILINGUALITY_DE.md](MULTILINGUALITY_DE.md).

## Lizenz

Diese Software wird **kostenlos** auf "Wie-Sie-Ist"-Basis bereitgestellt. Vollständige Lizenzbedingungen sind verfügbar in [LICENSE_DE.md](LICENSE_DE.md).

### Wichtig:
- **Keine Garantie** — Autor ist nicht verantwortlich für Fehler oder Schäden
- **Jeder Benutzer** verwendet die Software **auf eigene Verantwortung**
- **Erhaltungsanforderung** — Abschnitt "Folgen Sie uns in sozialen Medien" muss auf der Hauptseite der Anwendung verbleiben
  ```

## Anwendung ausführen

### Lokal (ohne Docker)

```bash
python3 app.py
# → Browser öffnet sich auf http://localhost:5000
```

### In Docker-Container

#### Option 1: Docker Compose (empfohlen)

```bash
# Standardinstanz – Port 3001, Standardcontainername
docker-compose up --build

# Oder im Hintergrund
docker-compose up -d
```

**Mehrere Instanzen auf einem VPS ausführen:**

Um Konflikte zwischen Instanzen zu vermeiden, verwenden Sie das `-p`-Flag (Projektname). Jedes Projekt muss einen eindeutigen Namen haben:

```bash
# Instanz 1 – Port 3001, Projekt ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 docker-compose -p ipsc1 up -d

# Instanz 2 – Port 3002, Projekt ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 docker-compose -p ipsc2 up -d

# Instanz 3 – Port 3003, Projekt ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 docker-compose -p ipsc3 up -d
```

**Instanzen verwalten:**

```bash
# Alle laufenden Container anzeigen
docker ps

# Spezifische Instanz stoppen
docker-compose -p ipsc1 down

# Protokolle der Instanz anzeigen
docker-compose -p ipsc1 logs -f

# Spezifische Instanz neustarten
docker-compose -p ipsc1 restart
```

**Über das `-p`-Flag:**

Das `-p`-Flag isoliert jedes Projekt mit seinen eigenen Containern, Netzwerken und Volumes. Ohne es teilen alle Instanzen denselben Projektnamen, was zu Konflikten führt und das gleichzeitige Ausführen mehrerer Instanzen verhindert.

Jede Instanz erstellt automatisch:
- Eindeutige `config.json` (Instanz-ID)
- Eindeutige Datenbank (`data/{instance_id}.db`)
- Separate Daten ohne Konflikte

Die Datenbank (`{instance_id}.db`) wird im Verzeichnis `./data/` auf dem Host gespeichert und **bleibt zwischen Neustarts erhalten**.

#### Option 2: Docker direkt

```bash
# Image bauen
docker build -t ipsc:latest .

# Container ausführen
docker run -d \
  --name ipsc-app \
  -p 3001:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Stoppen
docker stop ipsc-app
docker rm ipsc-app
```

#### Umgebungsvariablen

In `docker-compose.yml` können Sie anpassen:

| Variable | Beschreibung | Standardwert |
|----------|---------|---------|
| `PORT` | Host-Port-Zuordnung | `3001` |
| `CONTAINER_NAME` | Docker-Containername | `ipsc-app` |
| `SECRET_KEY` | Flask-Sitzungsschlüssel (SHA-256) | `default-secret-key-change-me` |

**Beispiel:**
```bash
CONTAINER_NAME=my-app PORT=8080 SECRET_KEY="mein-super-geheimer-schlüssel" docker-compose up -d
```

## CLI-Skript (`winmss_results.py`)

Extrahiert Daten aus der `.cab`-Datei und zeigt Ergebnisse im Terminal an.

```bash
# Gesamtübersicht + Tabellen pro Abteilung
python3 winmss_results.py

# Nur Gesamtübersicht
python3 winmss_results.py --overall

# Mit Stationsdetails
python3 winmss_results.py --stages

# Ranking auf jeder Station (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Export zu CSV (in Excel öffnbar)
python3 winmss_results.py --csv ergebnisse.csv

# Andere .cab-Datei
python3 winmss_results.py anderes_turnier.cab --csv ergebnisse.csv
```

## Web-Oberfläche (`app.py`)

### Admin-Anmeldepanel

Der Zugang zum Admin-Panel erfordert eine Anmeldung.

**Standardkonto:**
- **Benutzername:** `bartek`
- **Passwort:** `IP$c2023` (NACH DEM ERSTEN LOGIN ÄNDERN!)

Benutzerkonten werden in der SQLite-Datenbank mit SHA-256-Hashing gespeichert.

### Hauptseite – Ergebnisanzeige

#### Grundfunktionen
- **Wettkampfauswahl** – Liste gespeicherter Wettkämpfe in der Datenbank; Klick lädt Ergebnisse
- **Wettkampfkopf** – Name, Datum, Ebene (L1/L2/L3), Anzahl Stationen und Teilnehmer
- **Podium** – Karten der Top 3 mit Hit Factor / Punkten / Zeit
- **Gesamtübersicht** – Sortierbare Tabelle aller Teilnehmer; Klick auf Zeile erweitert Stationsdetails
- **Abteilungen-Tab** – Separate Tabellen pro Abteilung mit Ranking und % zum Abteilungsleiter
- **Stationen-Tab** – Ranking auf ausgewählter Station mit farbigen Schusskolonnen

#### Neue Funktionen

**🌐 Mehrsprachige Unterstützung**
- Sprachauswahl in der oberen rechten Ecke (PL, EN, DE, FR, CZ)
- Automatische Interface-Übersetzung
- Sprachdateien im Ordner `static/i18n/`

**🔍 Erweiterte Filterung**
- **Suche** – nach Nachnamen oder Vornamen des Teilnehmers
- **Divisionsfilter** – Möglichkeit, eine oder mehrere Divisionen gleichzeitig auszuwählen
- **Kategoriefilter** – Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady
- **Anwendungsbereich** – Filter funktionieren auf allen Tabs (Gesamt, Divisionen, Stationen)
- **Automatische Neuberechnung** – Prozentsätze werden für gefilterte Gruppen neu berechnet

**📊 Ergebnisse Export**
- **📄 PDF Export** – neue Funktionalität zur Generierung von Ergebnissen in PDF
  - Aufteilung nach Divisionen (jede Division auf separater Seite)
  - Farbige Divisionskopfzeilen (Open-rot, Standard-blau, Modified-grün)
  - Querformat für bessere Lesbarkeit
  - Hervorhebung der Plätze 1-3 (gold/silber/bronze)
  - Unterstützung sowohl für Einzelwettkämpfe als auch Rankings
- **📊 CSV Export** – Client-seitig generiert, in Excel öffenbar (UTF-8 mit BOM)

**🎨 Divisions-Farbgebung**
- Standard IPSC-Farben für Divisionen im gesamten Interface
- Visuelle Unterscheidung der Divisionen in Tabellen und Kopfzeilen

### Admin-Panel

Verfügbar unter `/admin` – erfordert Anmeldung.

#### Tab: Wettkämpfe
- **Datei-Upload** – Drag & Drop oder Formularklick; automatische Erkennung
- **Wettkampfliste** – Tabelle aller gespeicherten Wettkämpfe
- **Wettkämpfe löschen** – Schaltflächen zum Löschen einzelner Wettkämpfe

#### Tab: Teilnehmer
- **Teilnehmerdaten bearbeiten** – Wettkampf auswählen und für jeden Teilnehmer bearbeiten:
  - Vorname und Nachname
  - Kategorie (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Teilnehmerliste** – Tabellarischer Überblick aller Teilnehmer
- **Änderungen speichern** – "Speichern"-Schaltfläche für jeden Teilnehmer

#### Tab: Rankings
- **Ranking erstellen** – Name + Mehrfachauswahl von Wettkämpfen
- **Ranking bearbeiten** – Name und zugeordnete Wettkämpfe ändern
- **Ranking löschen** – Nur möglich, wenn das Ranking keine Wettkämpfe hat
- **Rankings-Liste** – Übersicht von Namen und Zuordnungen

#### ⚙️ Tab: Divisions-Mapping (NEU!)

Neue Funktionalität zur Zuordnung importierter Divisionsnamen zu Standard-IPSC-Divisionen.

**Funktionen:**
- **Wettkampfauswahl** – Selektor für Wettkämpfe zur Divisions-Zuordnung
- **Automatische Erkennung** – System sammelt automatisch alle eindeutigen Divisionsnamen aus importierten Wettkämpfen
- **Zuordnung zu Standards** – Möglichkeit, jede importierte Division einer der Standard-IPSC-Divisionen zuzuordnen
- **Zuordnungen kopieren** – Möglichkeit, alle Zuordnungen von einem Wettkampf zu einem anderen zu kopieren
- **Standard-Divisionen** unterstützt:
  - **Pistolen:** Open, Standard, Standard Manual, Modified, Classic, Revolver, Optics
  - **Gewehre:** Mini Rifle, Production, Production Optics, PCC Optics, PCC Standard
  - **Schrotflinte:** Karabin Open, Karabin Standard
  - **Spezialisiert:** PC Optic

**API-Endpunkte:**
- `GET /admin/api/divisions-mapping` – Zuordnungen für Wettkämpfe abrufen
- `POST /admin/api/divisions-mapping` – Divisionszuordnung speichern/löschen
- `POST /admin/api/divisions-mapping/copy` – Zuordnungen zwischen Wettkämpfen kopieren

**Vorteile:**
- Vereinheitlichung der Divisionsnamen zwischen verschiedenen Wettkämpfen
- Besseres Management von wettkampfübergreifenden Rankings
- Automatische Anwendung von Zuordnungen in Ergebnissen und Rankings

#### Tab: Benutzer
- **Passwort ändern** – Formular zum Ändern des Passworts
- **Benutzer verwalten** – Tabelle aller Benutzer
  - Neuen Benutzer erstellen
  - Benutzer löschen (Schutz – letzten Benutzer nicht löschen)
---

## Neueste Aktualisierungen (2026)

### v2.4 - Divisions-Mapping und PDF Export
- ✅ **PDF Export** – Export von Ergebnissen in PDF mit Aufteilung nach Divisionen
- ✅ **Divisions-Mapping** – intelligente Zuordnung importierter Divisionen zu IPSC-Standards
- ✅ **Mehrsprachigkeit** – Unterstützung für 5 Sprachen (PL, EN, DE, FR, CZ)
- ✅ **Divisions-Farbgebung** – Standard IPSC-Farben im Interface
- ✅ **Erweiterte Filterung** – Multi-Select-Filter für Divisionen und Kategorien
- ✅ **Automatische Neuberechnung** – Prozentsätze für gefilterte Gruppen
## Mehrsprachigkeit

Die Anwendung unterstützt die dynamische Sprachänderung ohne Neuladen der Seite. Verfügbare Sprachen:

- 🇵🇱 Polski
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇨🇿 Čeština
- 🇫🇷 Français

Detaillierte Dokumentation zur Mehrsprachigkeit finden Sie in [MULTILINGUALITY_DE.md](MULTILINGUALITY_DE.md).

## Lizenz

Diese Software wird **kostenlos** zur Verfügung gestellt. Die vollständigen Lizenzbedingungen finden Sie in der [LICENSE_DE.md](LICENSE_DE.md)-Datei.

### Wichtig:
- **Keine Gewährleistung** – Der Autor haftet nicht für Fehler oder Schäden
- **Jeder Benutzer** nutzt die Software **auf eigenes Risiko**
- **Anforderung zum Behalten** – Der Abschnitt "Folgen Sie uns in den sozialen Medien" muss auf der Hauptseite verbleiben

Eine [polnische Version der Lizenz](LICENSE.md) ist ebenfalls verfügbar.
