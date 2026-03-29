# 🌍 Vícejazyčná podpora - Dokumentace implementace

## Možnost 3: Hybridní backend + frontend

Aplikace podporuje dynamickou změnu jazyka bez obnovení stránky. Systém kombinuje:
- **Backend**: Flask-Babel (ukládá uživatelské preference)  
- **Frontend**: i18next (dynamické překlady v prohlížeči)

---

## 📦 Schéma architektury

```
┌─────────────────────────────────────────────────────────────┐
│                       UŽIVATEL                              │
└──────────────────┬──────────────────────────────────────────┘
                   │ Klikne na vlajku 🇵🇱 🇬🇧 🇩🇪 🇨🇿 🇫🇷
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   VOLBA JAZYKA                              │
│  (Fixováno v rohu, vždy dostupné)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────┴──────┐
            ▼             ▼
      ┌──────────┐  ┌──────────────────┐
      │ Backend  │  │ Frontend         │
      ├──────────┤  ├──────────────────┤
      │ Uložit v │  │ Změnit překlady  │
      │ souboru  │  │ v i18next        │
      │ cookie   │  └──────────────────┘
      └──────────┘  
            │             │
            └──────┬──────┘
                   ▼
         ┌──────────────────┐
         │ AKTUALIZACE      │
         │ TEXTU V UŽIVATEL.│
         │ ROZHRANÍ         │
         │ Bez obnovení     │
         └──────────────────┘
```

---

## 🔧 Pokyny k instalaci

### 1. Nainstalujte závislosti:
```bash
pip install -r requirements.txt
```

### 2. (Volitelně) Připravte nové překlady:
```bash
# Extrahujte texty ze šablon
pybabel extract -F babel.cfg -o messages.pot .

# Vytvořte soubor pro nový jazyk (např. ES)
pybabel init -i messages.pot -d . -l es

# Po přeložení zkompilujte
pybabel compile -d .
```

---

## 📂 Struktura souborů

```
ipsc/
├── app.py                      # Backend s Flask-Babel
├── babel.cfg                   # Konfigurace Babel
├── requirements.txt            # Závislosti (Flask-Babel, Babel)
├── templates/
│   └── index.html             # Frontend s i18next
├── static/
│   └── i18n/
│       ├── pl.json            # Polské překlady
│       ├── en.json            # Anglické překlady
│       ├── de.json            # Německé překlady
│       ├── cz.json            # České překlady
│       └── fr.json            # Francouzské překlady
```

---

## 🌐 Jak funguje API

### `/api/set-language` (POST)
Změní jazyk a uloží předvolbu do souboru cookie:
```javascript
fetch('/api/set-language', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ language: 'en' })
});
```

**Odpověď:**
```json
{ "status": "ok", "language": "en" }
```

### `/api/translations` (GET)
Načte překlady pro vybraný jazyk:
```javascript
fetch('/api/translations?lang=en')
  .then(r => r.json())
  .then(translations => {
    console.log(translations.header.title); // "IPSC Results"
  });
```

---

## 🎨 Jak přidávat nové překlady

### 1. Upravte soubory JSON v `static/i18n/`

**pl.json:**
```json
{
  "menu": {
    "ranking": "Žebřík",
    "matches": "Závody"
  },
  "messages": {
    "loading": "Zpracování souboru…"
  }
}
```

### 2. Použijte atribut `data-i18n` v šablonách HTML:
```html
<h1 data-i18n="header.title">Výsledky IPSC</h1>
<button data-i18n="buttons.pdf">PDF</button>
```

### 3. JavaScript automaticky aktualizuje text:
```javascript
updateUIText(); // Vestavěná funkce, volána při každé změně jazyka
```

---

## 💡 Podporované jazyky

| Vlajka | Kód | Jazyk | Dostupné | Status |
|------|------|---------|-----------|--------|
| 🇵🇱 | `pl` | Polski | ✅ Ano | Úplný |
| 🇬🇧 | `en` | English | ✅ Ano | Úplný |
| 🇩🇪 | `de` | Deutsch | ✅ Ano | Úplný |
| 🇨🇿 | `cz` | Čeština | ✅ Ano | Úplný |
| 🇫🇷 | `fr` | Français | ✅ Ano | Úplný |

---

## 🔀 Jak funguje výběr jazyka

1. **Pozice**: Fixováno v rohu stránky (`top: 12px; right: 12px;`)
2. **Vlajka**: Zobrazuje aktuální jazyk (např. 🇵🇱)
3. **Rozbalovací nabídka**: Kliknutí na vlajku otevře panel se všemi možnostmi
4. **Animace**: Tlačítko se zvětší při najetí myší

---

## ⚙️ Priorita jazykové předvolby

### 1. Parametr URL
```
http://localhost:5000/?lang=en
```

### 2. Soubor cookie (pamatované)
```javascript
document.cookie = "language=de; max-age=31536000"
```

### 3. Hlavička Accept-Language (z prohlížeče)
```
Accept-Language: de, pl;q=0.9, en;q=0.8
```

### 4. Výchozí
```
Čeština (cz)
```

---

## 🧪 Testování

### Test 1: Změna jazyka
1. Otevřete aplikaci: http://localhost:5000
2. Klikněte na vlajku 🇵🇱 v rohu
3. Vyberte 🇬🇧 EN
4. Stránka se změní na angličtinu **bez obnovení**
5. Obnovte stránku → jazyk by měl zůstat zachován

### Test 2: Přidání nového jazyka
1. Vytvořte `static/i18n/es.json` (španělština)
2. Přidejte do `app.py`:
   ```python
   SUPPORTED_LANGUAGES = ['pl', 'en', 'de', 'cz', 'fr', 'es']
   ```
3. Přidejte tlačítko v HTML:
   ```html
   <button class="lang-option" data-lang="es" onclick="changeLanguage('es')">🇪🇸 ES</button>
   ```

---

## 📊 Výkon

- **Překlady**: Načteny v paměti (bez dalších požadavků)
- **Soubory cookie**: Vypršení po 1 roce
- **Výběr**: Vždy dostupné (fixní pozice)
- **I18next**: ~50KB CDN, rychle
- **Změna jazyka**: Okamžitá (~2ms)

---

## 🐛 Řešení problémů

| Problém | Řešení |
|---------|--------|
| Text se nezmění | Ujistěte se, že prvek má atribut `data-i18n` |
| 404 u překladů | Zkontrolujte, zda soubor existuje v `static/i18n/` |
| Soubor cookie se neuloží | Otevřete dev tools → Application → Cookies |
| Chyby i18next v konzoli | Nainstalujte `pip install -r requirements.txt` |

---

## 🚀 Budoucí vylepšení

### Možná vylepšení:
1. ✅ Přidat více jazyků (ES, IT, RU, atd.)
2. ✅ Překlady backendu (chybové zprávy)
3. ✅ Import/Export překladů
4. ✅ Administrativní rozhraní pro správu překladů
5. ✅ Podpora RTL (arabština, hebrejština)

---

## 📝 Shrnutí

**Výhody tohoto hybridního přístupu:**
- ✅ Změna jazyka bez obnovení stránky
- ✅ Uživatelská předvolba je zapamatirana
- ✅ Snadné přidávání nových jazyků
- ✅ Oddělení překladů (JSON vs Backend)
- ✅ Výkon (~50KB celkem knihovny)

**Backend (Flask-Babel):**
- Ukládá předvolby v souboru cookie
- Lze rozšířit pro dynamické texty (chyby API)
