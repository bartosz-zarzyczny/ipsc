"""
Shared pytest fixtures for the ipsc test suite.

Strategy: monkeypatch database.DB_PATH to a per-test temp file so each test
runs against a fresh, isolated SQLite database. The Flask app instance is
reused across tests (module-level import), but every get_db() call resolves
database.DB_PATH at call-time, so the patch is sufficient.
"""
import pytest
import database as db_module
from database import init_db, init_standard_divisions_from_json


DEFAULT_DIVISIONS = [
    {"id": 1, "name": "Modified"},
    {"id": 2, "name": "Open"},
    {"id": 3, "name": "Standard"},
    {"id": 4, "name": "Standard Manual"},
    {"id": 5, "name": "Classic"},
    {"id": 6, "name": "Rewolwer"},
    {"id": 7, "name": "Mini Rifle"},
    {"id": 8, "name": "Optics"},
    {"id": 9, "name": "PC Optic"},
    {"id": 10, "name": "Production"},
    {"id": 11, "name": "Production Optics"},
    {"id": 12, "name": "Mini Rifle Open"},
    {"id": 13, "name": "Mini Rifle Standard"},
    {"id": 14, "name": "PCC Optics"},
    {"id": 15, "name": "PCC Standard"},
    {"id": 16, "name": "Karabin Open"},
    {"id": 17, "name": "Karabin Standard"},
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """
    Flask application configured for testing.

    - Uses a fresh SQLite file under pytest's tmp_path (isolated per test).
    - CSRF protection disabled so test clients can POST without tokens.
    - SECRET_KEY fixed for deterministic session behaviour.
    """
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)

    # Initialise schema and seed reference data in the test DB.
    init_db()
    init_standard_divisions_from_json(DEFAULT_DIVISIONS)

    from app import app as flask_app

    flask_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
            "RATELIMIT_ENABLED": False,
        }
    )

    yield flask_app


@pytest.fixture()
def client(app):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    """
    Test client with an active admin session.

    Creates a temporary admin user and logs in so that admin-only endpoints
    can be exercised without manual session manipulation.
    """
    from database import add_user

    uid = add_user("test_admin", "test_password_123")

    with app.test_client() as c:
        # Ustaw sesję bezpośrednio — omijamy endpoint /admin/login
        # żeby nie wyczerpać rate-limitu (10 request/min) w trakcie suite.
        with c.session_transaction() as sess:
            sess["admin"] = True
            sess["username"] = "test_admin"
            sess["user_id"] = uid
        yield c
