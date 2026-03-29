# 🌍 Multilingual Support - Implementation Documentation

## Option 3: Backend + Frontend Hybrid

The application supports dynamic language switching without page reload. The system combines:
- **Backend**: Flask-Babel (saves user preference)  
- **Frontend**: i18next (dynamic translations in browser)

---

## 📦 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                               │
└──────────────────┬──────────────────────────────────────────┘
                   │ Clicks on flag 🇵🇱 🇬🇧 🇩🇪 🇨🇿 🇫🇷
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   LANGUAGE SELECTOR                         │
│  (Fixed in corner, always available)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────┴──────┐
            ▼             ▼
      ┌──────────┐  ┌──────────────────┐
      │ Backend  │  │ Frontend         │
      ├──────────┤  ├──────────────────┤
      │ Save in  │  │ Change           │
      │ Cookie   │  │ translations     │
      └──────────┘  │ in i18next       │
            │       └──────────────────┘
            │             │
            └──────┬──────┘
                   ▼
         ┌──────────────────┐
         │ UPDATE UI TEXT   │
         │ No page reload   │
         └──────────────────┘
```

---

## 🔧 Installation Instructions

### 1. Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. (Optional) Prepare new translations:
```bash
# Extract texts from templates
pybabel extract -F babel.cfg -o messages.pot .

# Create file for new language (e.g. ES)
pybabel init -i messages.pot -d . -l es

# After translation, compile
pybabel compile -d .
```

---

## 📂 File Structure

```
ipsc/
├── app.py                      # Backend with Flask-Babel
├── babel.cfg                   # Babel configuration
├── requirements.txt            # Dependencies (Flask-Babel, Babel)
├── templates/
│   └── index.html             # Frontend with i18next
├── static/
│   └── i18n/
│       ├── pl.json            # Polish translations
│       ├── en.json            # English translations
│       ├── de.json            # German translations
│       ├── cz.json            # Czech translations
│       └── fr.json            # French translations
```

---

## 🌐 How the API Works

### `/api/set-language` (POST)
Changes language and saves preference in a cookie:
```javascript
fetch('/api/set-language', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ language: 'en' })
});
```

**Response:**
```json
{ "status": "ok", "language": "en" }
```

### `/api/translations` (GET)
Retrieves translations for selected language:
```javascript
fetch('/api/translations?lang=en')
  .then(r => r.json())
  .then(translations => {
    console.log(translations.header.title); // "IPSC Results"
  });
```

---

## 🎨 How to Add New Translations

### 1. Edit JSON files in `static/i18n/`

**pl.json:**
```json
{
  "menu": {
    "ranking": "Ranking",
    "matches": "Competitions"
  },
  "messages": {
    "loading": "Processing file…"
  }
}
```

### 2. Use the `data-i18n` attribute in HTML templates:
```html
<h1 data-i18n="header.title">IPSC Results</h1>
<button data-i18n="buttons.pdf">PDF</button>
```

### 3. JavaScript automatically updates text:
```javascript
updateUIText(); // Built-in function, called on every language change
```

---

## 💡 Supported Languages

| Flag | Code | Language | Available | Status |
|------|------|----------|-----------|--------|
| 🇵🇱 | `pl` | Polski | ✅ Yes | Full |
| 🇬🇧 | `en` | English | ✅ Yes | Full |
| 🇩🇪 | `de` | Deutsch | ✅ Yes | Full |
| 🇨🇿 | `cz` | Čeština | ✅ Yes | Full |
| 🇫🇷 | `fr` | Français | ✅ Yes | Full |

---

## 🔀 How the Language Selector Works

1. **Position**: Fixed in corner of page (`top: 12px; right: 12px;`)
2. **Flag**: Shows current language (e.g. 🇵🇱)
3. **Dropdown**: Click on flag opens panel with all options
4. **Animation**: Button scales on hover

---

## ⚙️ Language Preference Priority

### 1. URL Parameter
```
http://localhost:5000/?lang=en
```

### 2. Cookie (remembered)
```javascript
document.cookie = "language=de; max-age=31536000"
```

### 3. Accept-Language header (from browser)
```
Accept-Language: de, pl;q=0.9, en;q=0.8
```

### 4. Default
```
Polish (pl)
```

---

## 🧪 Testing

### Test 1: Change Language
1. Open application: http://localhost:5000
2. Click on flag 🇵🇱 in corner
3. Select 🇬🇧 EN
4. Page changes to English **without reloading**
5. Refresh page → language should be preserved

### Test 2: Add New Language
1. Create `static/i18n/es.json` (Spanish)
2. Add to `app.py`:
   ```python
   SUPPORTED_LANGUAGES = ['pl', 'en', 'de', 'cz', 'fr', 'es']
   ```
3. Add button in HTML:
   ```html
   <button class="lang-option" data-lang="es" onclick="changeLanguage('es')">🇪🇸 ES</button>
   ```

---

## 📊 Performance

- **Translations**: Loaded in memory (no additional requests)
- **Cookies**: 1 year expiration
- **Selector**: Always available (fixed position)
- **I18next**: ~50KB CDN, fast
- **Language Change**: Instant (~2ms)

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Text doesn't change | Make sure element has `data-i18n` attribute |
| 404 on translations | Check if file exists in `static/i18n/` |
| Cookie not saving | Open dev tools → Application → Cookies |
| i18next errors in console | Install `pip install -r requirements.txt` |

---

## 🚀 Future Improvements

### Possible Enhancements:
1. ✅ Add more languages (ES, IT, RU, etc.)
2. ✅ Backend translations (error messages)
3. ✅ Import/Export translations
4. ✅ Admin interface for translation management
5. ✅ RTL support (Arabic, Hebrew)

---

## 📝 Summary

**Advantages of this hybrid approach:**
- ✅ Language change without page reload
- ✅ User preference is remembered
- ✅ Easy to add new languages
- ✅ Separation of translations (JSON vs Backend)
- ✅ Performance (~50KB total library)

**Backend (Flask-Babel):**
- Stores preferences in cookie
- Can be expanded for dynamic texts (API errors)
