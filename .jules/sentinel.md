## 2024-05-20 - Session Fixation and Cookie Security
**Vulnerability:** Session wasn't cleared on login/logout (only specific keys popped), and session cookies lacked HttpOnly and SameSite configurations.
**Learning:** In Flask, `session.pop` is insufficient to prevent session fixation. `session.clear()` must be used to renew the session fully. Additionally, secure cookie flags must be explicitly set.
**Prevention:** Always use `session.clear()` on privilege changes (login/logout) and set `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE="Lax"`.