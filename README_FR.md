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

- **Sélection de compétition** – liste des compétitions enregistrées ; clic pour charger les résultats
- **En-tête de compétition** – nom, date, niveau (L1/L2/L3), nombre d'étapes et participants
- **Podium** – cartes des 3 premiers avec Hit Factor / points / temps
- **Vue d'ensemble générale** – tableau triable de tous les participants
- **Onglet Divisions** – tableaux séparés par division avec classement
- **Onglet Étapes** – classement sur l'étape sélectionnée
- **Filtres** – recherche par nom, filtre par division, filtre par catégorie
- **Export CSV** – généré côté client, ouvert dans Excel (UTF-8 avec BOM)
- **Lien vers le panneau** – bouton dans le coin supérieur menant à `/admin`

### Panneau d'administration

Disponible sur `/admin` – nécessite une connexion.

#### Onglet: Compétitions
- **Téléchargement de fichier** – glisser-déposer ou clic sur formulaire ; détection automatique
- **Liste des compétitions** – tableau de toutes les compétitions enregistrées
- **Suppression de compétitions** – boutons pour supprimer les compétitions individuelles

#### Onglet: Classements
- **Créer classement** – nom + sélection multiple de compétitions
- **Modifier classement** – modifier le nom et les compétitions assignées
- **Supprimer classement** – possible uniquement si le classement n'a pas de compétitions
- **Liste des classements** – aperçu des noms et des affectations

#### Onglet: Utilisateurs
- **Changer le mot de passe** – formulaire pour modifier le mot de passe de l'utilisateur connecté
- **Gérer les utilisateurs** – tableau de tous les utilisateurs
  - Créer un nouvel utilisateur
  - Supprimer un utilisateur (protection – ne peut pas supprimer le dernier utilisateur)

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
