# 🌍 Support multilingue - Documentation de mise en œuvre

## Option 3 : Hybride Backend + Frontend

L'application prend en charge le changement dynamique de langue sans rechargement de page. Le système combine :
- **Backend** : Flask-Babel (enregistre les préférences de l'utilisateur)  
- **Frontend** : i18next (traductions dynamiques dans le navigateur)

---

## 📦 Diagramme architectural

```
┌─────────────────────────────────────────────────────────────┐
│                      UTILISATEUR                            │
└──────────────────┬──────────────────────────────────────────┘
                   │ Clique sur l'indicateur 🇵🇱 🇬🇧 🇩🇪 🇨🇿 🇫🇷
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   SÉLECTEUR DE LANGUE                       │
│  (Fixé au coin, toujours disponible)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────┴──────┐
            ▼             ▼
      ┌──────────┐  ┌──────────────────┐
      │ Backend  │  │ Frontend         │
      ├──────────┤  ├──────────────────┤
      │ Enregistre│  │ Modifier les     │
      │ dans le  │  │ traductions      │
      │ cookie   │  │ dans i18next     │
      └──────────┘  └──────────────────┘
            │             │
            └──────┬──────┘
                   ▼
         ┌──────────────────┐
         │ MISE À JOUR DU   │
         │ TEXTE DE         │
         │ L'INTERFACE      │
         │ Pas de           │
         │ rechargement     │
         └──────────────────┘
```

---

## 🔧 Instructions d'installation

### 1. Installez les dépendances :
```bash
pip install -r requirements.txt
```

### 2. (Optionnel) Préparez les nouvelles traductions :
```bash
# Extrayez les textes des modèles
pybabel extract -F babel.cfg -o messages.pot .

# Créez un fichier pour la nouvelle langue (par exemple ES)
pybabel init -i messages.pot -d . -l es

# Après la traduction, compilez
pybabel compile -d .
```

---

## 📂 Structure des fichiers

```
ipsc/
├── app.py                      # Backend avec Flask-Babel
├── babel.cfg                   # Configuration de Babel
├── requirements.txt            # Dépendances (Flask-Babel, Babel)
├── templates/
│   └── index.html             # Frontend avec i18next
├── static/
│   └── i18n/
│       ├── pl.json            # Traductions polonaises
│       ├── en.json            # Traductions anglaises
│       ├── de.json            # Traductions allemandes
│       ├── cz.json            # Traductions tchèques
│       └── fr.json            # Traductions françaises
```

---

## 🌐 Fonctionnement de l'API

### `/api/set-language` (POST)
Change la langue et enregistre la préférence dans un cookie :
```javascript
fetch('/api/set-language', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ language: 'en' })
});
```

**Réponse :**
```json
{ "status": "ok", "language": "en" }
```

### `/api/translations` (GET)
Récupère les traductions pour la langue sélectionnée :
```javascript
fetch('/api/translations?lang=en')
  .then(r => r.json())
  .then(translations => {
    console.log(translations.header.title); // "Résultats IPSC"
  });
```

---

## 🎨 Comment ajouter de nouvelles traductions

### 1. Modifiez les fichiers JSON dans `static/i18n/`

**pl.json :**
```json
{
  "menu": {
    "ranking": "Classement",
    "matches": "Compétitions"
  },
  "messages": {
    "loading": "Traitement du fichier…"
  }
}
```

### 2. Utilisez l'attribut `data-i18n` dans les modèles HTML :
```html
<h1 data-i18n="header.title">Résultats IPSC</h1>
<button data-i18n="buttons.pdf">PDF</button>
```

### 3. JavaScript met à jour automatiquement le texte :
```javascript
updateUIText(); // Fonction intégrée, appelée à chaque changement de langue
```

---

## 💡 Langues supportées

| Indicateur | Code | Langue | Disponible | Statut |
|------|------|---------|-----------|--------|
| 🇵🇱 | `pl` | Polski | ✅ Oui | Complet |
| 🇬🇧 | `en` | English | ✅ Oui | Complet |
| 🇩🇪 | `de` | Deutsch | ✅ Oui | Complet |
| 🇨🇿 | `cz` | Čeština | ✅ Oui | Complet |
| 🇫🇷 | `fr` | Français | ✅ Oui | Complet |

---

## 🔀 Fonctionnement du sélecteur de langue

1. **Position** : Fixé au coin de la page (`top: 12px; right: 12px;`)
2. **Indicateur** : Affiche la langue actuelle (par ex. 🇵🇱)
3. **Menu déroulant** : Cliquer sur l'indicateur ouvre un panneau avec toutes les options
4. **Animation** : Le bouton s'agrandit au survol

---

## ⚙️ Priorité de préférence de langue

### 1. Paramètre d'URL
```
http://localhost:5000/?lang=en
```

### 2. Cookie (mémorisé)
```javascript
document.cookie = "language=de; max-age=31536000"
```

### 3. En-tête Accept-Language (du navigateur)
```
Accept-Language: de, pl;q=0.9, en;q=0.8
```

### 4. Par défaut
```
Français (fr)
```

---

## 🧪 Tests

### Test 1 : Changer la langue
1. Ouvrez l'application : http://localhost:5000
2. Cliquez sur l'indicateur 🇵🇱 au coin
3. Sélectionnez 🇬🇧 EN
4. La page passe à l'anglais **sans rechargement**
5. Actualisez la page → la langue doit être conservée

### Test 2 : Ajouter une nouvelle langue
1. Créez `static/i18n/es.json` (espagnol)
2. Ajoutez à `app.py` :
   ```python
   SUPPORTED_LANGUAGES = ['pl', 'en', 'de', 'cz', 'fr', 'es']
   ```
3. Ajoutez un bouton en HTML :
   ```html
   <button class="lang-option" data-lang="es" onclick="changeLanguage('es')">🇪🇸 ES</button>
   ```

---

## 📊 Performances

- **Traductions** : Chargées en mémoire (pas de requêtes supplémentaires)
- **Cookies** : Expiration 1 an
- **Sélecteur** : Toujours disponible (position fixe)
- **I18next** : ~50KB CDN, rapide
- **Changement de langue** : Instantané (~2ms)

---

## 🐛 Dépannage

| Problème | Solution |
|---------|----------|
| Le texte ne change pas | Assurez-vous que l'élément a l'attribut `data-i18n` |
| 404 sur les traductions | Vérifiez que le fichier existe dans `static/i18n/` |
| Le cookie ne s'enregistre pas | Ouvrez dev tools → Application → Cookies |
| Erreurs i18next dans la console | Installez `pip install -r requirements.txt` |

---

## 🚀 Améliorations futures

### Améliorations possibles :
1. ✅ Ajouter plus de langues (ES, IT, RU, etc.)
2. ✅ Traductions backend (messages d'erreur)
3. ✅ Import/Export des traductions
4. ✅ Interface d'administration pour la gestion des traductions
5. ✅ Support RTL (arabe, hébreu)

---

## 📝 Résumé

**Avantages de cette approche hybride :**
- ✅ Changement de langue sans rechargement de page
- ✅ La préférence de l'utilisateur est mémorisée
- ✅ Facile d'ajouter de nouvelles langues
- ✅ Séparation des traductions (JSON vs Backend)
- ✅ Performances (~50KB total library)

**Backend (Flask-Babel) :**
- Enregistre les préférences dans un cookie
- Peut être étendu pour les textes dynamiques (erreurs API)
