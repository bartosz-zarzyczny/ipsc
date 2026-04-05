# ADR 004: Kontrakt odpowiedzi błędów API

- Status: accepted
- Data: 2026-04-05
- Powiązane: [app.py](../../app.py) — helper `_error_response()`
- Powiązane: [spec/schemas/error.json](../schemas/error.json)

## Kontekst

Przed wprowadzeniem `_error_response()` endpointy zwracały błędy w różnych formatach:
```python
return jsonify({"error": "Nie znaleziono zawodów"}), 404      # standard
return jsonify({"error": "Brak danych"}), 400                  # standard
return jsonify({"error": "Nie udało się..."}), 500             # standard
```
Wszystkie używały tego samego kształtu, ale bez mechanizmu egzekwowania — każdy nowy
endpoint mógł wprowadzić inny format. Klienci (JS w `index.html`, `admin.html`)
sprawdzali obecność klucza `error` bez walidacji struktury.

## Decyzja

Wszystkie endpointy JSON zwracające błąd używają helpera `_error_response()` i formatu
zgodnego z [spec/schemas/error.json](../schemas/error.json):

```python
def _error_response(message: str, code: str | None = None, http_status: int = 400):
    body = {"error": message}
    if code is not None:
        body["code"] = code
    return jsonify(body), http_status
```

Pole `code` (snake_case, opcjonalne) przeznaczone jest dla klientów programistycznych
wymagających lokalizacji lub obsługi konkretnych przypadków. Pole `error` jest zawsze
po polsku (spójne z istniejącym UI).

## Decyzje dotyczące kodów HTTP

| Sytuacja | Kod | Uzasadnienie |
|---|---|---|
| Zasób nie istnieje (brak rekordu w DB) | `404` | Semantycznie poprawne; klient może buforować odpowiedź |
| Brakujące lub nieprawidłowe pola wejściowe | `400` | Błąd klienta, możliwy do naprawienia przez klienta |
| Wartość prawidłowa syntaktycznie, ale naruszająca regułę biznesową | `400` | Brak `422` w Flask bez dodatkowej biblioteki; `400` jest wystarczające dla obecnych klientów |
| Brak autentykacji (brak sesji) | `401` | Standard HTTP |
| Nieudana operacja DB (constraint, conflict) | `400` | Błąd wywołany przez dane klienta |
| Nieoczekiwany wyjątek serwera | `500` | Błąd serwera; logowany przez `app.logger.error()` |

**Nie używamy `403 Forbidden`** — aplikacja rozróżnia tylko: zalogowany admin / nikt.
Brak `403` upraszcza klienty, które nie muszą rozróżniać "brak sesji" od "brak uprawnień".

**Nie używamy `422 Unprocessable Entity`** mimo że semantycznie trafniejszy dla walidacji —
Flask-WTF nie obsługuje go natywnie, a spójność `400` dla wszystkich błędów walidacji
upraszcza obsługę po stronie klienta.

## Zasady wynikające z tej decyzji

1. **Każdy endpoint JSON zwracający błąd używa `_error_response()`** — nie `jsonify({"error": ...})` bezpośrednio.
2. **Endpointy formularzowe (redirect)** nie podlegają tej regule — zwracają `302`
   z parametrami `?error=` lub `?success=` w URL.
3. **`code` jest opcjonalny** ale zalecany dla nowych endpointów:
   rekomendowane wartości: `not_found`, `missing_file`, `auth_required`, `invalid_input`,
   `constraint_violation`, `server_error`.
4. **Pole `error` pozostaje po polsku** — zmiana wymaga aktualizacji tłumaczeń w `static/i18n/`.
5. **Logowanie błędów `500`** — używać `app.logger.error("kontekst: %s", exc)` przed
   zwróceniem odpowiedzi; nigdy nie ujawniać stack trace w odpowiedzi.

## Konsekwencje

- Klienci JS mogą polegać na `response.error` jako zawsze obecnym kluczu przy błędach.
- Testy kontraktowe mogą walidować każdą odpowiedź błędną względem
  [spec/schemas/error.json](../schemas/error.json) bez case-by-case sprawdzania.
- Migracja istniejących endpointów do `_error_response()` jest przeprowadzana stopniowo —
  helper jest kompatybilny wstecznie (ta sama struktura JSON).
