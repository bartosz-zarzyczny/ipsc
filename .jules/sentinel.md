## 2024-05-07 - Secure Flask Session Management
**Vulnerability:** Session fixation and lack of secure session cookie attributes.
**Learning:** Flask's default session cookies are not protected with `HttpOnly` and `SameSite` attributes by default in this setup, which can lead to XSS attacks stealing cookies and CSRF attacks. Also, failing to clear the session upon authentication state changes (login/logout) can allow session fixation attacks.
**Prevention:** Always configure `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE="Lax"` in Flask configurations. Use `session.clear()` when a user logs in or out to generate a new session identifier and wipe old state.
