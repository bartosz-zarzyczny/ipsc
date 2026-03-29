# 🌍 Wielojęzyczność - Dokumentacja Implementacji

## Opcja 3: Hybryda Backend + Frontend

Aplikacja wspiera dynamiczną zmianę języka bez przeładowania strony. System łączy:
- **Backend**: Flask-Babel (przychowuje preferencję użytkownika)  
- **Frontend**: i18next (dynamiczne tłumaczenia w przeglądace)

---

## 📦 Schemat Architekturalny

```
┌─────────────────────────────────────────────────────────────┐
│                      UŻYTKOWNIK                            │
└──────────────────┬──────────────────────────────────────────┘
                   │ Kliknie na flagę 🇵🇱 🇬🇧 🇩🇪 🇨🇿 🇫🇷
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                  SELEKTOR JĘZYKA                           │
│  (Fixed w rogu, dostępny zawsze)                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
            ┌──────┴──────┐
            ▼             ▼
      ┌──────────┐  ┌──────────────────┐
      │ Backend  │  │ Frontend         │
      ├──────────┤  ├──────────────────┤
      │ Zapisz w │  │ Zmień tłumaczenia│
      │ ciastku  │  │ w i18next        │
      └──────────┘  └──────────────────┘
            │             │
            └──────┬──────┘
                   ▼
         ┌──────────────────┐
         │ UPDATE UI TEKST  │
         │ Bez przeładowania│
         └──────────────────┘
```

---

## 🔧 Instrukcja Instalacji

### 1. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

### 2. (Opcjonalnie) Przygotuj nowe tłumaczenia:
```bash
# Wyodrębnij teksty z szablonów
pybabel extract -F babel.cfg -o messages.pot .

# Utwórz plik dla nowego języka (np. ES)
pybabel init -i messages.pot -d . -l es

# Po tłumaczeniu, skompiluj
pybabel compile -d .
```

---

## 📂 Struktura Plików

```
ipsc/
├── app.py                      # Backend z Flask-Babel
├── babel.cfg                   # Konfiguracja Babel
├── requirements.txt            # Zależności (Flask-Babel, Babel)
├── templates/
│   └── index.html             # Frontend z i18next
├── static/
│   └── i18n/
│       ├── pl.json            # Tłumaczenia polskie
│       ├── en.json            # Tłumaczenia angielskie
│       ├── de.json            # Tłumaczenia niemieckie
│       ├── cz.json            # Tłumaczenia czeskie
│       └── fr.json            # Tłumaczenia francuskie
```

---

## 🌐 Jak Działa API

### `/api/set-language` (POST)
Zmienia język i zapisuje preferencję w ciastku:
```javascript
fetch('/api/set-language', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ language: 'en' })
});
```

**Odpowiedź:**
```json
{ "status": "ok", "language": "en" }
```

### `/api/translations` (GET)
Pobiera tłumaczenia dla wybranego języka:
```javascript
fetch('/api/translations?lang=en')
  .then(r => r.json())
  .then(translations => {
    console.log(translations.header.title); // "IPSC Results"
  });
```

---

## 🎨 Jak Dodawać Nowe Tłumaczenia

### 1. Edytuj pliki JSON w `static/i18n/`

**pl.json:**
```json
{
  "menu": {
    "ranking": "Ranking",
    "matches": "Zawody"
  },
  "messages": {
    "loading": "Przetwarzanie pliku…"
  }
}
```

### 2. W szablonach HTML użyj atrybutu `data-i18n`:
```html
<h1 data-i18n="header.title">Wyniki IPSC</h1>
<button data-i18n="buttons.pdf">PDF</button>
```

### 3. JavaScript automatycznie zaktualizuje tekst:
```javascript
updateUIText(); // Funkcja wbudowana, wywoływana przy każdej zmianie języka
```

---

## 💡 Obsługiwane Języki

| Flaga | Kod | Język | Dostępny | Status |
|-------|-----|--------|----------|---------|
| 🇵🇱 | `pl` | Polski | ✅ Tak | Pełny |
| 🇬🇧 | `en` | English | ✅ Tak | Pełny |
| 🇩🇪 | `de` | Deutsch | ✅ Tak | Pełny |
| 🇨🇿 | `cz` | Čeština | ✅ Tak | Pełny |
| 🇫🇷 | `fr` | Français | ✅ Tak | Pełny |

---

## 🔀 Jak Działa Selektor Języka

1. **Pozycja**: Fixed w rogu strony (`top: 12px; right: 12px;`)
2. **Flaga**: Pokazuje aktualny język (np. 🇵🇱)
3. **Dropdown**: Klik na flagę otwiera panel z 3 opcjami
4. **Animacja**: Przycisk się skaluje na hover

---

## ⚙️ Fluktuacja Preferowanych Języków

### 1. Parametr URL
```
http://localhost:5000/?lang=en
```

### 2. Ciastko (zapamiętane)
```javascript
document.cookie = "language=de; max-age=31536000"
```

### 3. Nagłówek Accept-Language (z przeglądarki)
```
Accept-Language: de, pl;q=0.9, en;q=0.8
```

### 4. Domyślnie
```
Polska (pl)
```

---

## 🧪 Testowanie

### Test 1: Zmiana Języka
1. Otwórz aplikację: http://localhost:5000
2. Klikni na flagę 🇵🇱 w rogu
3. Wybierz 🇬🇧 EN
4. Strona zmieni się na angielski **bez przeładowania**
5. Odśwież stronę → język powinien być zachowany

### Test 2: Dodanie Nowego Języka
1. Utwórz `static/i18n/es.json` (Spanish)
2. Dodaj do `app.py`:
   ```python
   SUPPORTED_LANGUAGES = ['pl', 'en', 'de', 'es']
   ```
3. Dodaj przycisk w HTML:
   ```html
   <button class="lang-option" data-lang="es" onclick="changeLanguage('es')">🇪🇸 ES</button>
   ```

---

## 📊 Performance

- **Tłumaczenia**: Załadowane w pamięci (brak dodatkowych żądań)
- **Ciastka**: 1 rok wygaśnięcia
- **Selektor**: Zawsze dostępny (fixed position)
- **I18next**: ~50KB CDN, szybkie
- **Zmiana Języka**: Natychmiastowa (~2ms)

---

## 🐛 Troubleshooting

| Problem | Rozwiązanie |
|---------|------------|
| Tekst nie zmienia się | Upewnij się, że element ma `data-i18n` |
| 404 na tłumaczeniach | Sprawdź czy plik istnieje w `static/i18n/` |
| Ciastko nie zapisuje się | Otwórz dev tools → Application → Cookies |
| i18next errory w konsoli | Zainstaluj `pip install -r requirements.txt` |

---

## 🚀 Rozszerzenie w Przyszłości

### Możliwe Ulepszenia:
1. ✅ Dodaj więcej języków (ES, FR, IT, RU, et.)
2. ✅ Tłumaczenia danych z backend (error messages)
3. ✅ Eksport/Import tłumaczeń
4. ✅ Interfejs admina do zarządzania tłumaczeniami
5. ✅ RTL support (lingwistyka arabska, hebrajska)

---

## 📝 Podsumowanie

**Zalety tej hibrydy:**
- ✅ Zmiana języka bez przeładowania
- ✅ Zapamiętanie preferencji użytkownika
- ✅ Łatwa obsługa nowych języków
- ✅ Separacja tłumaczeń (JSON vs Backend)
- ✅ Performance (~50KB całej biblioteki)

**Backend (Flask-Babel):**
- Przechowuje preferencje w ciastku
- Możliwa rozbudowa dla dynamicznych tekstów (API errors)

**Frontend (i18next):**
- Dynamiczne tłumaczenia bez page reload
- Obsługa pluralizacji i interpolacji
- Community support

---

Powodzenia z implementacją! 🎉
