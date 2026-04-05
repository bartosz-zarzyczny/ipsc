# ADR 003: Strategia autentykacji i zarządzania sesjami

- Status: accepted
- Data: 2026-04-05
- Powiązane: [database.py](../../database.py) — funkcje `add_user()`, `verify_user()`,
  `change_password()`; [app.py](../../app.py) — dekorator `@admin_required`, `admin_login()`

## Kontekst

Aplikacja ma dwa poziomy dostępu:
- **Publiczny** — przeglądanie wyników zawodów i rankingów (bez autentykacji).
- **Administrator** — import danych, zarządzanie rankingami, edycja zawodników,
  mapowanie dywizji, zarządzanie użytkownikami (wymaga sesji).

Baza użytkowników jest mała (1–10 kont); aplikacja działa jako single-tenant lub
jako kilka izolowanych instancji (per Docker container). Nie ma wymagania SSO,
OAuth ani zewnętrznego IdP.

## Decyzje

### 1. Hashowanie haseł — PBKDF2-SHA256 (Werkzeug)

Nowe hasła są hashowane przez `werkzeug.security.generate_password_hash()` z metodą
`pbkdf2:sha256`. Zapewnia to iterowane rozciąganie klucza odporne na ataki słownikowe.

**Wsparcie dla haseł legacy (SHA-256 hex):** Stare instalacje mogły używać prostego
`hashlib.sha256(password).hexdigest()`. Funkcja `verify_user()` wykrywa 64-znakowy
hex bez separatora `:` i:
1. Weryfikuje przez bezpieczne `hmac.compare_digest()` (ochrona przed timing attacks).
2. Przy sukcesie automatycznie upgraduje hash do PBKDF2 w tej samej transakcji.
3. Zwraca `user_id` — przezroczyste dla wywołującego.

Format legacy jest wyłącznie do migracji — żadna nowa ścieżka kodu nie generuje SHA-256 hex.

### 2. Sesje — Flask server-side session cookie

Sesja przechowywana w podpisanym ciasteczku (`itsdangerous` przez Flask). Klucz sesji
(`SECRET_KEY`) musi być ustawiony przez zmienną środowiskową. Jeśli brak — generowany
losowo przy starcie (`secrets.token_hex(32)`), co unieważnia sesje po restarcie.

**W środowisku produkcyjnym `SECRET_KEY` musi być trwały** (zmienna env w Docker Compose).

Pola sesji po zalogowaniu:
- `session["admin"] = True` — flaga sprawdzana przez `@admin_required`
- `session["username"]` — nazwa użytkownika (używana przy zmianie hasła)
- `session["user_id"]` — id z bazy (używane przy zmianie hasła)

### 3. Ochrona przed brute-force — Flask-Limiter

Endpoint `POST /admin/login` ograniczony do **10 prób na minutę per IP** przez
`@limiter.limit("10 per minute")`. Pozostałe endpointy nie mają domyślnego limitu
(`default_limits=[]`) — można je dodać per-endpoint.

### 4. CSRF — Flask-WTF CSRFProtect

Wszystkie formularzowe `POST`/`PUT`/`DELETE` wymagają tokenu CSRF. Wyłączane przez
`WTF_CSRF_ENABLED = False` tylko w trybie `TESTING` (testy integracyjne).

### 5. Zarządzanie użytkownikami

- `add_user()` — PBKDF2 hash, `UNIQUE` constraint na `username`.
- `delete_user()` — odmawia usunięcia ostatniego użytkownika (blokada w kodzie,
  nie na poziomie DB), zapobiegając zablokowaniu dostępu.
- `change_password()` — wymaga weryfikacji aktualnego hasła przez `verify_user()`.

## Zasady wynikające z tej decyzji

1. **`SECRET_KEY` z env** — `os.environ.get("SECRET_KEY", secrets.token_hex(32))`.
   Deployment bez ustawionej zmiennej środowiskowej jest akceptowalny wyłącznie lokalnie.
2. **Nie przechowywać wrażliwych danych w sesji** poza `admin`, `username`, `user_id`.
3. **Format SHA-256 hex jest deprecated** — usunąć obsługę gdy wszystkie instancje
   produkcyjne przejdą przez co najmniej jedno logowanie po aktualizacji do obecnej wersji.
4. **`@admin_required` zwraca 401 JSON** dla zapytań AJAX (`is_json` lub
   `X-Requested-With: XMLHttpRequest`); przekierowanie do `/admin/login` dla requestów HTML.
5. **Nie implementować remember-me / długich sesji** bez uprzedniego dodania rotacji tokenów.

## Konsekwencje

- Restart kontenera bez trwałego `SECRET_KEY` wyloguje wszystkich użytkowników —
  akceptowalne dla użycia evenementowego (zawody), nieakceptowalne dla systemów ciągłych.
- Brak 2FA — akceptowalne dla obecnego profilu ryzyka (aplikacja lokalna / LAN).
- Przy skalowaniu poziomym (wiele instancji za load balancerem) wymagany jest
  shared `SECRET_KEY` lub zewnętrzny session store — obecna architektura tego nie obsługuje.
