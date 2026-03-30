# IPSC — Výsledky IPSC

Nástroj pro extrakci a prohlížení výsledků střeleckých soutěží IPSC ze souborů WinMSS `.cab`.

## Struktura projektu

```
├── WinMSS.cab                    # Soubor s daty o soutěži (export WinMSS)
├── data/                         # Složka s databází a konfigurací (trvalá v Dockeru)
│   ├── config.json               # Automaticky vygenerovaná konfigurace instance
│   └── {instance_id}.db          # Databáze SQLite (jedinečně pojmenovaná pro každou instanci)
├── winmss_results.py             # CLI skript – výsledky v terminálu / export CSV
├── app.py                        # Flask server – webové uživatelské rozhraní
├── database.py                   # Vrstva databáze (ORM)
├── docker-compose.yml            # Konfigurace Docker Compose
├── Dockerfile                    # Specifikace kontejneru
└── templates/
    ├── index.html                # Frontend (prohlížeč výsledků)
    ├── admin.html                # Panel správce (soutěže + žebříčky + uživatelé)
    └── admin_login.html          # Přihlašovací formulář
```

## Požadavky

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — pro extrakci souborů `.cab`
  ```bash
  brew install cabextract   # macOS
  ```

## Spuštění aplikace

### Lokálně (bez Dockeru)

```bash
python3 app.py
# → prohlížeč se otevře na http://localhost:5000
```

### V kontejneru Docker

#### Možnost 1: Docker Compose (doporučeno)

```bash
# Výchozí instance – port 3001, výchozí název kontejneru
docker-compose up --build

# Nebo na pozadí
docker-compose up -d
```

**Spuštění více instancí na jednom VPS:**

Aby se zabránilo konfliktům mezi instancemi, použijte příznak `-p` (project-name). Každý projekt musí mít jedinečný název:

```bash
# Instance 1 – port 3001, projekt ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 docker-compose -p ipsc1 up -d

# Instance 2 – port 3002, projekt ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 docker-compose -p ipsc2 up -d

# Instance 3 – port 3003, projekt ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 docker-compose -p ipsc3 up -d
```

**Správa instancí:**

```bash
# Zobrazit všechny spuštěné kontejnery
docker ps

# Zastavit konkrétní instanci
docker-compose -p ipsc1 down

# Zobrazit protokoly instance
docker-compose -p ipsc1 logs -f

# Restartovat konkrétní instanci
docker-compose -p ipsc1 restart
```

**O příznaku `-p`:**

Příznak `-p` izoluje každý projekt s jeho vlastními kontejnery, sítěmi a svazky. Bez něj všechny instance sdílejí stejný project-name, což vede ke konfliktům a brání souběžnému spuštění více instancí.

Každá instance automaticky vytvoří:
- Jedinečný `config.json` (ID instance)
- Jedinečnou databázi (`data/{instance_id}.db`)
- Oddělená data bez konfliktů

Databáze (`{instance_id}.db`) se uloží do adresáře `./data/` na hostiteli a **zůstane mezi restarty**.

#### Možnost 2: Docker přímo

```bash
# Builds image
docker build -t ipsc:latest .

# Spuštění kontejneru
docker run -d \
  --name ipsc-app \
  -p 3001:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Zastavení
docker stop ipsc-app
docker rm ipsc-app
```

#### Proměnné prostředí

V `docker-compose.yml` můžete přizpůsobit:

| Proměnná | Popis | Výchozí hodnota |
|---------|------|----------|
| `PORT` | Mapování portu hostitele | `3001` |
| `CONTAINER_NAME` | Název Docker kontejneru | `ipsc-app` |
| `SECRET_KEY` | Klíč relace Flask (SHA-256) | `default-secret-key-change-me` |

**Příklad:**
```bash
CONTAINER_NAME=my-app PORT=8080 SECRET_KEY="můj-super-tajný-klíč" docker-compose up -d
```

## CLI skript (`winmss_results.py`)

Extrahuje data ze souboru `.cab` a zobrazuje výsledky v terminálu.

```bash
# Celkový přehled + tabulky na divizi
python3 winmss_results.py

# Pouze celkový přehled
python3 winmss_results.py --overall

# S detaily etapy
python3 winmss_results.py --stages

# Ranking na každé etapě (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Export do CSV (otevřený v Excelu)
python3 winmss_results.py --csv vysledky.csv

# Jiný soubor .cab
python3 winmss_results.py jina_soutez.cab --csv vysledky.csv
```

## Webové rozhraní (`app.py`)

### Panel přihlášení správce

Přístup k panelu správce vyžaduje přihlášení.

**Výchozí účet:**
- **Přihlášení:** `bartek`
- **Heslo:** `IP$c2023` (ZMĚŇTE PO PRVNÍM PŘIHLÁŠENÍ!)

Uživatelské účty se ukládají v databázi SQLite s šifrováním SHA-256.

### Hlavní stránka – prohlížeč výsledků

- **Výběr soutěže** – seznam uložených soutěží; kliknutí načte výsledky
- **Záhlaví soutěže** – název, datum, úroveň (L1/L2/L3), počet etap a účastníků
- **Podium** – karty prvních 3 s Hit Factor / body / čas
- **Celkový přehled** – tříditelná tabulka všech účastníků; kliknutí na řádek rozbalí detaily etapy
- **Karta divize** – samostatné tabulky na divizi s žebříčkem a % k vedoucímu divize
- **Karta etapy** – žebřík na vybrané etapě s barevnými sloupci střelby
- **Filtry** – vyhledávání podle jména, filtr podle divize, filtr podle kategorie (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Přepočet procent** – když je kategorie filtrována, procenta se automaticky přepočítají na 100% pro vedoucího této kategorie v dané divizi
- **Export CSV** – generován na straně klienta, otevřený v Excelu (UTF-8 s BOM)
- **Odkaz na panel** – tlačítko v horním rohu vede na `/admin`

### Panel správce

Dostupný na `/admin` – vyžaduje přihlášení.

#### Karta: Soutěže
- **Nahrání souboru** – drag & drop nebo klik na formulář; automatická detekce
- **Seznam soutěží** – tabulka všech uložených soutěží
- **Smazání soutěží** – tlačítka pro smazání jednotlivých soutěží

#### Karta: Soutěžící
- **Úprava údajů soutěžícího** – vyberte soutěž, poté upravte pro každého soutěžícího:
  - Jméno a příjmení
  - Kategorie (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Seznam soutěžících** – tabelární přehled všech soutěžících
- **Uložení změn** – tlačítko "Uložit" pro každého soutěžícího

#### Karta: Žebříčky
- **Vytvorení žebříčku** – název + vícenásobný výběr soutěží
- **Úprava žebříčku** – změna názvu a přiřazených soutěží
- **Smazání žebříčku** – možné pouze pokud žebřík nemá soutěže
- **Seznam žebříčků** – přehled jmen a přiřazení

#### Karta: Uživatelé
- **Změna hesla** – formulář pro změnu hesla přihlášeného uživatele
- **Správa uživatelů** – tabulka všech uživatelů
  - Vytvoření nového uživatele
  - Smazání uživatele (ochrana – poslední uživatel se nemůže smazat)

## Multilingvální podpora

Aplikace podporuje dynamickou změnu jazyka bez obnovení stránky. Dostupné jazyky:

- 🇵🇱 Polski
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇨🇿 Čeština
- 🇫🇷 Français

Podrobnou dokumentaci o multilingvální podpoře najdete v [MULTILINGUALITY_CZ.md](MULTILINGUALITY_CZ.md).

## Licence

Tento software je poskytován **zdarma**. Úplné licenční podmínky naleznete v souboru [LICENSE_CZ.md](LICENSE_CZ.md).

### Důležité:
- **Bez záruky** – Autor neodpovídá za chyby nebo škody
- **Každý uživatel** si software používá **na své vlastní riziko**
- **Požadavek na zachování** – Sekce "Sledujte nás na sociálních sítích" musí zůstat na hlavní stránce aplikace

Dostupná je také [polská verze licence](LICENSE.md).
