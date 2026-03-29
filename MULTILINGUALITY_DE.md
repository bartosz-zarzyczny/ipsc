# 🌍 Mehrsprachige Unterstützung - Implementierungsdokumentation

## Option 3: Backend + Frontend Hybrid

Die Anwendung unterstützt das dynamische Sprachenwechsel ohne Neuladen der Seite. Das System kombiniert:
- **Backend**: Flask-Babel (speichert Benutzerpräferenz)  
- **Frontend**: i18next (dynamische Übersetzungen im Browser)

---

## 📦 Architekturdiagramm

```
┌─────────────────────────────────────────────────────────────┐
│                         BENUTZER                            │
└──────────────────┬──────────────────────────────────────────┘
                   │ Klickt auf Flagge 🇵🇱 🇬🇧 🇩🇪 🇨🇿 🇫🇷
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   SPRACHENWÄHLER                            │
│  (An Ecke fixiert, immer verfügbar)                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────┴──────┐
            ▼             ▼
      ┌──────────┐  ┌──────────────────┐
      │ Backend  │  │ Frontend         │
      ├──────────┤  ├──────────────────┤
      │ In       │  │ Ändern Sie die   │
      │ Cookie   │  │ Übersetzungen    │
      │ speichern│  │ in i18next       │
      └──────────┘  └──────────────────┘
            │             │
            └──────┬──────┘
                   ▼
         ┌──────────────────┐
         │ UI-TEXT          │
         │ AKTUALISIEREN    │
         │ Kein Neuladen    │
         └──────────────────┘
```

---

## 🔧 Installationsanweisung

### 1. Abhängigkeiten installieren:
```bash
pip install -r requirements.txt
```

### 2. (Optional) Neue Übersetzungen vorbereiten:
```bash
# Texte aus Vorlagen extrahieren
pybabel extract -F babel.cfg -o messages.pot .

# Datei für neue Sprache erstellen (z. B. ES)
pybabel init -i messages.pot -d . -l es

# Nach der Übersetzung kompilieren
pybabel compile -d .
```

---

## 📂 Dateistruktur

```
ipsc/
├── app.py                      # Backend mit Flask-Babel
├── babel.cfg                   # Babel-Konfiguration
├── requirements.txt            # Abhängigkeiten (Flask-Babel, Babel)
├── templates/
│   └── index.html             # Frontend mit i18next
├── static/
│   └── i18n/
│       ├── pl.json            # Polnische Übersetzungen
│       ├── en.json            # Englische Übersetzungen
│       ├── de.json            # Deutsche Übersetzungen
│       ├── cz.json            # Tschechische Übersetzungen
│       └── fr.json            # Französische Übersetzungen
```

---

## 🌐 Wie die API funktioniert

### `/api/set-language` (POST)
Ändert die Sprache und speichert die Vorliebe in einem Cookie:
```javascript
fetch('/api/set-language', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ language: 'en' })
});
```

**Antwort:**
```json
{ "status": "ok", "language": "en" }
```

### `/api/translations` (GET)
Ruft Übersetzungen für die ausgewählte Sprache ab:
```javascript
fetch('/api/translations?lang=en')
  .then(r => r.json())
  .then(translations => {
    console.log(translations.header.title); // "IPSC Results"
  });
```

---

## 🎨 Wie man neue Übersetzungen hinzufügt

### 1. JSON-Dateien in `static/i18n/` bearbeiten

**pl.json:**
```json
{
  "menu": {
    "ranking": "Ranking",
    "matches": "Wettkämpfe"
  },
  "messages": {
    "loading": "Datei wird verarbeitet…"
  }
}
```

### 2. Verwenden Sie das Attribut `data-i18n` in HTML-Vorlagen:
```html
<h1 data-i18n="header.title">IPSC-Ergebnisse</h1>
<button data-i18n="buttons.pdf">PDF</button>
```

### 3. JavaScript aktualisiert Text automatisch:
```javascript
updateUIText(); // Integrierte Funktion, wird bei jeder Sprachänderung aufgerufen
```

---

## 💡 Unterstützte Sprachen

| Flagge | Code | Sprache | Verfügbar | Status |
|------|------|---------|-----------|--------|
| 🇵🇱 | `pl` | Polski | ✅ Ja | Vollständig |
| 🇬🇧 | `en` | English | ✅ Ja | Vollständig |
| 🇩🇪 | `de` | Deutsch | ✅ Ja | Vollständig |
| 🇨🇿 | `cz` | Čeština | ✅ Ja | Vollständig |
| 🇫🇷 | `fr` | Français | ✅ Ja | Vollständig |

---

## 🔀 Wie der Sprachenwähler funktioniert

1. **Position**: An der Ecke der Seite fixiert (`top: 12px; right: 12px;`)
2. **Flagge**: Zeigt aktuelle Sprache an (z. B. 🇵🇱)
3. **Dropdown**: Klick auf Flagge öffnet Panel mit allen Optionen
4. **Animation**: Knopf wird beim Hover skaliert

---

## ⚙️ Sprachpräferenz-Priorität

### 1. URL-Parameter
```
http://localhost:5000/?lang=en
```

### 2. Cookie (gespeichert)
```javascript
document.cookie = "language=de; max-age=31536000"
```

### 3. Accept-Language-Header (vom Browser)
```
Accept-Language: de, pl;q=0.9, en;q=0.8
```

### 4. Standard
```
Polnisch (pl)
```

---

## 🧪 Tests

### Test 1: Sprache ändern
1. Anwendung öffnen: http://localhost:5000
2. Auf Flagge 🇵🇱 in der Ecke klicken
3. 🇬🇧 EN auswählen
4. Seite wechselt zu Englisch **ohne Neuladen**
5. Seite aktualisieren → Sprache sollte gespeichert sein

### Test 2: Neue Sprache hinzufügen
1. `static/i18n/es.json` erstellen (Spanisch)
2. Zu `app.py` hinzufügen:
   ```python
   SUPPORTED_LANGUAGES = ['pl', 'en', 'de', 'cz', 'fr', 'es']
   ```
3. Knopf in HTML hinzufügen:
   ```html
   <button class="lang-option" data-lang="es" onclick="changeLanguage('es')">🇪🇸 ES</button>
   ```

---

## 📊 Leistung

- **Übersetzungen**: Im Speicher geladen (keine zusätzlichen Anfragen)
- **Cookies**: 1 Jahr Ablauf
- **Wähler**: Immer verfügbar (feste Position)
- **I18next**: ~50KB CDN, schnell
- **Sprachänderung**: Sofort (~2ms)

---

## 🐛 Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Text ändert sich nicht | Das Element muss das Attribut `data-i18n` haben |
| 404 bei Übersetzungen | Überprüfen Sie, ob die Datei in `static/i18n/` existiert |
| Cookie speichert nicht | Dev Tools öffnen → Application → Cookies |
| i18next-Fehler in Konsole | `pip install -r requirements.txt` installieren |

---

## 🚀 Zukünftige Verbesserungen

### Mögliche Verbesserungen:
1. ✅ Mehr Sprachen hinzufügen (ES, IT, RU, etc.)
2. ✅ Backend-Übersetzungen (Fehlermeldungen)
3. ✅ Import/Export von Übersetzungen
4. ✅ Admin-Oberfläche für Übersetzungsverwaltung
5. ✅ RTL-Unterstützung (Arabisch, Hebräisch)

---

## 📝 Zusammenfassung

**Vorteile dieses Hybrid-Ansatzes:**
- ✅ Sprachenwechsel ohne Neuladen der Seite
- ✅ Benutzerpräferenz wird gespeichert
- ✅ Leicht neue Sprachen hinzufügen
- ✅ Trennung von Übersetzungen (JSON vs Backend)
- ✅ Leistung (~50KB Gesamtbibliothek)

**Backend (Flask-Babel):**
- Speichert Vorlieben in Cookie
- Kann für dynamische Texte erweitert werden (API-Fehler)
