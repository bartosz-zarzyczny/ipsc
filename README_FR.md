# IPSC — Résultats IPSC

Un outil pour extraire et afficher les résultats des compétitions de tir IPSC à partir de fichiers WinMSS `.cab`.

## Structure du projet

```
├── WinMSS.cab                    # Fichier avec données de compétition (export WinMSS)
├── data/                         # Dossier avec base de données et configuration (persistant dans Docker)
│   ├── config.json               # Configuration d'instance générée automatiquement
│   └── {instance_id}.db          # Base de données SQLite (nommée de manière unique par instance)
├── winmss_results.py             # Script CLI – résultats dans le terminal / export CSV
├── app.py                        # Serveur Flask – interface utilisateur web
├── database.py                   # Couche de base de données (ORM)
├── docker-compose.yml            # Configuration Docker Compose
├── Dockerfile                    # Spécification du conteneur
├── static/i18n/                  # Fichiers de traduction (support multilingue)
└── templates/
    ├── index.html                # Frontend (navigateur de résultats)
    ├── admin.html                # Panneau d'administration (compétitions + classements + utilisateurs)
    └── admin_login.html          # Formulaire de connexion
```

## Exigences

- **Python 3.9+**
- **Flask** — `pip install flask`
- **cabextract** — pour extraire les fichiers `.cab`
  ```bash
  brew install cabextract   # macOS
  ```

## Lancement de l'application

### Localement (sans Docker)

```bash
python3 app.py
# → le navigateur s'ouvrira sur http://localhost:5000
```

### Dans un conteneur Docker

#### Option 1: Docker Compose (recommandé)

```bash
# Instance par défaut – port 3000, nom de conteneur par défaut
docker-compose up --build

# Ou en arrière-plan
docker-compose up -d
```

**Exécuter plusieurs instances sur un VPS:**

Pour éviter les conflits entre instances, utilisez l'indicateur `-p` (project-name). Chaque projet doit avoir un nom unique:

```bash
# Instance 1 – port 3001, projet ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 DATA_DIR=./data-3001 docker-compose -p ipsc1 up -d

# Instance 2 – port 3002, projet ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 DATA_DIR=./data-3002 docker-compose -p ipsc2 up -d

# Instance 3 – port 3003, projet ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 DATA_DIR=./data-3003 docker-compose -p ipsc3 up -d
```

**Gérer les instances:**

```bash
# Afficher tous les conteneurs en cours d'exécution
docker ps

# Arrêter une instance spécifique
docker-compose -p ipsc1 down

# Voir les logs d'instance
docker-compose -p ipsc1 logs -f

# Redémarrer une instance spécifique
docker-compose -p ipsc1 restart
```

#### Variables d'environnement

Dans `docker-compose.yml` vous pouvez personnaliser:

| Variable | Description | Défaut |
|----------|-------------|---------|
| `PORT` | Port hôte pour mappage | `3000` |
| `DATA_DIR` | Répertoire de données pour base de données | `./data` |
| `CONTAINER_NAME` | Nom du conteneur Docker | `ipsc-app` |
| `SECRET_KEY` | Clé de session Flask (SHA-256) | `default-secret-key-change-me` |

## Script CLI (`winmss_results.py`)

Extrait les données du fichier `.cab` et affiche les résultats dans le terminal.

## Interface web (`app.py`)

### Panneau d'administration

**Compte par défaut:**
- **Nom d'utilisateur:** `bartek`
- **Mot de passe:** `IP$c2023` (CHANGEZ-LE APRÈS LA PREMIÈRE CONNEXION!)

#### Nouvelles fonctionnalités

**🌐 Support multilingue**
- Sélecteur de langue dans le coin supérieur droit (PL, EN, DE, FR, CZ)
- Traduction automatique de l'interface

**📄 Export PDF**
- Export des résultats en PDF divisés par divisions
- En-têtes de division colorés selon les standards IPSC
- Orientation paysage pour une meilleure lisibilité

**⚙️ Mappage des divisions**
- Mappage intelligent des noms de divisions importées vers les standards IPSC
- Divisions standard: Open, Standard, Modified, etc.

## Dernières mises à jour (2026)

### v2.4 - Mappage des divisions et Export PDF
- ✅ **Export PDF** — export des résultats en PDF divisés par divisions
- ✅ **Mappage des divisions** — mappage intelligent vers les standards IPSC
- ✅ **Support multilingue** — support de 5 langues (PL, EN, DE, FR, CZ)
- ✅ **Coloration des divisions** — couleurs IPSC standard dans l'interface
- ✅ **Filtrage avancé** — filtres multi-sélection pour divisions et catégories

## Support multilingue

L'application prend en charge le changement de langue dynamique sans rechargement de page. Langues disponibles:

- 🇵🇱 Polonais
- 🇬🇧 Anglais
- 🇩🇪 Allemand
- 🇨🇿 Tchèque
- 🇫🇷 Français

Documentation détaillée sur l'implémentation multilingue disponible dans [MULTILINGUALITY_FR.md](MULTILINGUALITY_FR.md).

## Licence

Ce logiciel est fourni **gratuitement** sur une base "tel quel". Les conditions de licence complètes sont disponibles dans [LICENSE_FR.md](LICENSE_FR.md).

### Important:
- **Aucune garantie** — l'auteur n'est pas responsable des erreurs ou dommages
- **Chaque utilisateur** utilise le logiciel **à ses propres risques**
- **Exigence de maintien** — la section "Suivez-nous sur les médias sociaux" doit rester sur la page principale de l'application
  ```

## Exécution de l'application

### Localement (sans Docker)

```bash
python3 app.py
# → le navigateur s'ouvrira sur http://localhost:5000
```

### Dans un conteneur Docker

#### Option 1 : Docker Compose (recommandé)

```bash
# Instance par défaut – port 3001, nom de conteneur par défaut
docker-compose up --build

# Ou en arrière-plan
docker-compose up -d
```

**Exécution de plusieurs instances sur un seul VPS:**

Pour éviter les conflits entre instances, utilisez le drapeau `-p` (project-name). Chaque projet doit avoir un nom unique :

```bash
# Instance 1 – port 3001, projet ipsc1
CONTAINER_NAME=ipsc-app-1 PORT=3001 docker-compose -p ipsc1 up -d

# Instance 2 – port 3002, projet ipsc2
CONTAINER_NAME=ipsc-app-2 PORT=3002 docker-compose -p ipsc2 up -d

# Instance 3 – port 3003, projet ipsc3
CONTAINER_NAME=ipsc-app-3 PORT=3003 docker-compose -p ipsc3 up -d
```

**Gestion des instances :**

```bash
# Lister tous les conteneurs en cours d'exécution
docker ps

# Arrêter une instance spécifique
docker-compose -p ipsc1 down

# Afficher les journaux de l'instance
docker-compose -p ipsc1 logs -f

# Redémarrer une instance spécifique
docker-compose -p ipsc1 restart
```

**À propos du drapeau `-p`:**

Le drapeau `-p` isole chaque projet avec ses propres conteneurs, réseaux et volumes. Sans lui, toutes les instances partagent le même project-name, ce qui provoque des conflits et empêche l'exécution simultanée de plusieurs instances.

Chaque instance créera automatiquement :
- `config.json` unique (ID d'instance)
- Base de données unique (`data/{instance_id}.db`)
- Données séparées sans conflits

La base de données (`{instance_id}.db`) sera stockée dans le répertoire `./data/` sur l'hôte et **persistera entre les redémarrages**.

#### Option 2 : Docker directement

```bash
# Construire l'image
docker build -t ipsc:latest .

# Exécuter le conteneur
docker run -d \
  --name ipsc-app \
  -p 3001:5000 \
  -v $(pwd)/data:/app/data \
  ipsc:latest

# Arrêter
docker stop ipsc-app
docker rm ipsc-app
```

#### Variables d'environnement

Dans `docker-compose.yml`, vous pouvez personnaliser :

| Variable | Description | Par défaut |
|----------|-----------|---------|
| `PORT` | Mappage de port hôte | `3001` |
| `CONTAINER_NAME` | Nom du conteneur Docker | `ipsc-app` |
| `SECRET_KEY` | Clé de session Flask (SHA-256) | `default-secret-key-change-me` |

**Exemple:**
```bash
CONTAINER_NAME=my-app PORT=8080 SECRET_KEY="ma-clé-super-secrète" docker-compose up -d
```

## Script CLI (`winmss_results.py`)

Extrait les données du fichier `.cab` et affiche les résultats dans le terminal.

```bash
# Vue d'ensemble générale + tableaux par division
python3 winmss_results.py

# Vue d'ensemble générale uniquement
python3 winmss_results.py --overall

# Avec détails des étapes
python3 winmss_results.py --stages

# Classement sur chaque étape (A/B/C/D/M/PE)
python3 winmss_results.py --stage-detail

# Exporter vers CSV (ouvert dans Excel)
python3 winmss_results.py --csv resultats.csv

# Autre fichier .cab
python3 winmss_results.py autre_competition.cab --csv resultats.csv
```

## Interface web (`app.py`)

### Panneau de connexion administrateur

L'accès au panneau d'administration nécessite une connexion.

**Compte par défaut:**
- **Connexion:** `bartek`
- **Mot de passe:** `IP$c2023` (CHANGEZ-LE APRÈS LA PREMIÈRE CONNEXION!)

Les comptes d'utilisateur sont stockés dans la base de données SQLite avec hachage SHA-256.

### Page d'accueil – Navigateur de résultats

#### Fonctionnalités de base
- **Sélection de compétition** – liste des compétitions enregistrées dans la base de données ; clic charge les résultats
- **En-tête de compétition** – nom, date, niveau (L1/L2/L3), nombre d'étapes et participants
- **Podium** – cartes des 3 premiers avec Hit Factor / points / temps
- **Vue d'ensemble générale** – tableau triable de tous les participants ; clic sur une ligne développe les détails d'étape
- **Onglet Divisions** – tableaux séparés par division avec classement et % du leader de division
- **Onglet Étapes** – classement sur l'étape sélectionnée avec colonnes de tirs colorées

#### Nouvelles fonctionnalités

**🌐 Support multilingue**
- Sélecteur de langue dans le coin supérieur droit (PL, EN, DE, FR, CZ)
- Traduction automatique de l'interface
- Fichiers de langue dans le dossier `static/i18n/`

**🔍 Filtrage avancé**
- **Recherche** – par nom de famille ou prénom du compétiteur
- **Filtre par division** – possibilité de sélectionner une ou plusieurs divisions simultanément
- **Filtre par catégorie** – Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady
- **Portée** – les filtres fonctionnent sur tous les onglets (Général, Divisions, Étapes)
- **Recalcul automatique** – pourcentages recalculés pour les groupes filtrés

**📊 Export des résultats**
- **📄 Export PDF** – nouvelle fonctionnalité de génération de résultats en PDF
  - Séparation par divisions (chaque division sur une page séparée)
  - En-têtes de division colorés (Open-rouge, Standard-bleu, Modified-vert)
  - Orientation paysage pour une meilleure lisibilité
  - Mise en évidence des places 1-3 (or/argent/bronze)
  - Support pour les compétitions individuelles et les classements
- **📊 Export CSV** – généré côté client, ouvert dans Excel (UTF-8 avec BOM)

**🎨 Coloration des divisions**
- Couleurs IPSC standard pour les divisions dans toute l'interface
- Distinction visuelle des divisions dans les tableaux et en-têtes

### Panneau d'administration

Disponible sur `/admin` – nécessite une connexion.

#### Onglet: Compétitions
- **Téléchargement de fichier** – glisser-déposer ou clic sur formulaire ; détection automatique
- **Liste des compétitions** – tableau de toutes les compétitions enregistrées
- **Suppression de compétitions** – boutons pour supprimer les compétitions individuelles

#### Onglet: Compétiteurs
- **Modification des données du compétiteur** – sélectionner une compétition, puis modifier pour chaque compétiteur:
  - Prénom et nom
  - Catégorie (Senior / Super Senior / Grand Senior / Junior / Lady / Senior Lady)
- **Liste des compétiteurs** – aperçu tabulaire de tous les compétiteurs
- **Enregistrement des modifications** – bouton "Enregistrer" pour chaque compétiteur

#### Onglet: Classements
- **Créer classement** – nom + sélection multiple de compétitions
- **Modifier classement** – modifier le nom et les compétitions assignées
- **Supprimer classement** – possible uniquement si le classement n'a pas de compétitions
- **Liste des classements** – aperçu des noms et des affectations

#### ⚙️ Onglet: Mappage des Divisions (NOUVEAU!)

Nouvelle fonctionnalité permettant de mapper les noms de divisions importés vers les divisions IPSC standard.

**Fonctionnalités:**
- **Sélection de compétition** – sélecteur de compétitions pour mapper les divisions
- **Détection automatique** – le système collecte automatiquement tous les noms de divisions uniques des compétitions importées
- **Mappage vers les standards** – possibilité d'assigner chaque division importée à l'une des divisions IPSC standard
- **Copie des mappages** – possibilité de copier tous les mappages d'une compétition à une autre
- **Divisions standard** supportées:
  - **Pistolets:** Open, Standard, Standard Manual, Modified, Classic, Revolver, Optics
  - **Fusils:** Mini Rifle, Production, Production Optics, PCC Optics, PCC Standard
  - **Fusil de chasse:** Karabin Open, Karabin Standard
  - **Spécialisé:** PC Optic

**Points de terminaison API:**
- `GET /admin/api/divisions-mapping` – obtenir les mappages pour les compétitions
- `POST /admin/api/divisions-mapping` – sauvegarder/supprimer le mappage de division
- `POST /admin/api/divisions-mapping/copy` – copier les mappages entre compétitions

**Avantages:**
- Standardisation des noms de divisions entre différentes compétitions
- Meilleure gestion des classements inter-compétitions
- Application automatique des mappages dans les résultats et classements

#### Onglet: Utilisateurs
- **Changer le mot de passe** – formulaire pour modifier le mot de passe de l'utilisateur connecté
- **Gérer les utilisateurs** – tableau de tous les utilisateurs
  - Créer un nouvel utilisateur
  - Supprimer un utilisateur (protection – ne peut pas supprimer le dernier utilisateur)
---

## Dernières mises à jour (2026)

### v2.4 - Mappage des Divisions et Export PDF
- ✅ **Export PDF** – export des résultats en PDF avec séparation par divisions
- ✅ **Mappage des Divisions** – mappage intelligent des divisions importées vers les standards IPSC
- ✅ **Support multilingue** – support de 5 langues (PL, EN, DE, FR, CZ)
- ✅ **Coloration des divisions** – couleurs IPSC standard dans l'interface
- ✅ **Filtrage avancé** – filtres multi-sélection pour divisions et catégories
- ✅ **Recalcul automatique** – pourcentages pour groupes filtrés
## Support multilingue

L'application prend en charge le changement dynamique de langue sans rechargement de page. Langues disponibles:

- 🇵🇱 Polski
- 🇬🇧 English
- 🇩🇪 Deutsch
- 🇨🇿 Čeština
- 🇫🇷 Français

La documentation détaillée sur le support multilingue se trouve dans [MULTILINGUALITY_FR.md](MULTILINGUALITY_FR.md).

## Licence

Ce logiciel est fourni **gratuitement**. Les conditions de licence complètes sont disponibles dans le fichier [LICENSE_FR.md](LICENSE_FR.md).

### Important:
- **Aucune garantie** – L'auteur n'est pas responsable des erreurs ou des dommages
- **Chaque utilisateur** utilise le logiciel **à ses propres risques**
- **Exigence de maintenance** – La section "Suivez-nous sur les réseaux sociaux" doit rester sur la page principale de l'application

Une [version française de la licence](LICENSE_FR.md) est également disponible.
