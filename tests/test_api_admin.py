"""
test_api_admin.py — testy kontraktowe administracyjnych endpointów API

Pokrycie:
  - Ochrona autentykacją (401 bez sesji)
  - Kompetytory: GET/POST/DELETE /admin/api/competitors/<match_id>
  - Division mappings: GET/POST /admin/api/divisions-mapping
  - Division mappings copy: POST /admin/api/divisions-mapping/copy
  - Standard divisions CRUD: GET/POST/PUT/DELETE /admin/api/standard-divisions
  - Users API: GET /admin/users
  - DELETE /api/matches/<id> (wymaga admina)
"""
import json
import pytest
import jsonschema
import pathlib


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "spec" / "schemas"


def _validate(data, schema_name: str):
    schema = json.loads((SCHEMAS_DIR / schema_name).read_text())
    store = {}
    for p in SCHEMAS_DIR.glob("*.json"):
        s = json.loads(p.read_text())
        store[s["$id"]] = s
    resolver = jsonschema.RefResolver(
        base_uri=f"file://{SCHEMAS_DIR}/",
        referrer=schema,
        store={f"file://{SCHEMAS_DIR}/{k}": v for k, v in store.items()},
    )
    errors = list(jsonschema.Draft202012Validator(schema, resolver=resolver).iter_errors(data))
    assert not errors, f"Schema '{schema_name}' błędy:\n" + "\n".join(
        f"  {e.json_path}: {e.message}" for e in errors
    )


SAMPLE_MATCH = {
    "match": {"name": "Admin Test Match", "date": "2026-03-01", "level": 2},
    "stages": [
        {"id": "1", "name": "Stage 1", "max_points": 60, "max_hf_by_div": {"Open": 6.0}},
    ],
    "competitors": [
        {
            "rank": 1, "comp_id": "301",
            "firstname": "Tomasz", "lastname": "Maj", "name": "Maj Tomasz",
            "division": "Open", "div_id": "1", "category": "", "female": False,
            "squad": "A", "is_disq": False,
            "total_points": 60.0, "total_points_overall": 60.0, "total_points_in_division": 60.0,
            "total_time": 10.0, "overall_hf": 6.0, "pct": 100.0,
            "stage_scores": [{"pts": 60.0, "time": 10.0, "hf": 6.0,
                               "A": 6, "B": 0, "C": 0, "D": 0, "M": 0, "PE": 0, "NS": 0, "disq": False}],
        },
        {
            "rank": 2, "comp_id": "302",
            "firstname": "Zofia", "lastname": "Kamień", "name": "Kamień Zofia",
            "division": "Standard", "div_id": "2", "category": "Lady", "female": True,
            "squad": "B", "is_disq": False,
            "total_points": 45.0, "total_points_overall": 45.0, "total_points_in_division": 45.0,
            "total_time": 12.0, "overall_hf": 3.75, "pct": 75.0,
            "stage_scores": [{"pts": 45.0, "time": 12.0, "hf": 3.75,
                               "A": 4, "B": 1, "C": 0, "D": 0, "M": 0, "PE": 0, "NS": 0, "disq": False}],
        },
    ],
}


@pytest.fixture()
def match_id(app):
    from database import save_match
    with app.app_context():
        return save_match(SAMPLE_MATCH)


# ---------------------------------------------------------------------------
# Auth protection — endpointy wymagają sesji
# ---------------------------------------------------------------------------

class TestAuthProtection:
    PROTECTED_ROUTES = [
        ("GET",    "/admin/api/competitors/1"),
        ("POST",   "/admin/api/competitors/1"),
        ("DELETE", "/admin/api/competitors/1/comp1"),
        ("GET",    "/admin/api/divisions-mapping"),
        ("POST",   "/admin/api/divisions-mapping"),
        ("POST",   "/admin/api/divisions-mapping/copy"),
        ("GET",    "/admin/api/standard-divisions"),
        ("POST",   "/admin/api/standard-divisions"),
        ("PUT",    "/admin/api/standard-divisions/1"),
        ("DELETE", "/admin/api/standard-divisions/1"),
        ("GET",    "/admin/users"),
        ("DELETE", "/api/matches/1"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
    def test_unauthenticated_returns_401(self, client, method, path):
        r = client.open(path, method=method,
                        content_type="application/json", data="{}")
        assert r.status_code == 401, f"{method} {path} powinno zwrócić 401, dostało {r.status_code}"


# ---------------------------------------------------------------------------
# DELETE /api/matches/<id>
# ---------------------------------------------------------------------------

class TestDeleteMatch:
    def test_admin_can_delete_match(self, admin_client, match_id):
        r = admin_client.delete(f"/api/matches/{match_id}")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_delete_nonexistent_returns_404(self, admin_client):
        r = admin_client.delete("/api/matches/99999")
        assert r.status_code == 404
        _validate(r.get_json(), "error.json")


# ---------------------------------------------------------------------------
# GET/POST/DELETE /admin/api/competitors/<match_id>
# ---------------------------------------------------------------------------

class TestCompetitorsApi:
    def test_get_competitors_returns_200(self, admin_client, match_id):
        r = admin_client.get(f"/admin/api/competitors/{match_id}")
        assert r.status_code == 200

    def test_get_competitors_structure(self, admin_client, match_id):
        data = admin_client.get(f"/admin/api/competitors/{match_id}").get_json()
        assert "competitors" in data
        assert isinstance(data["competitors"], list)
        assert len(data["competitors"]) == 2

    def test_competitor_fields_present(self, admin_client, match_id):
        data = admin_client.get(f"/admin/api/competitors/{match_id}").get_json()
        c = data["competitors"][0]
        for field in ("comp_id", "firstname", "lastname", "name", "division", "category"):
            assert field in c

    def test_get_competitors_nonexistent_match_404(self, admin_client):
        r = admin_client.get("/admin/api/competitors/99999")
        assert r.status_code == 404
        _validate(r.get_json(), "error.json")

    def test_update_competitor_name(self, admin_client, match_id):
        r = admin_client.post(
            f"/admin/api/competitors/{match_id}",
            json={"comp_id": "301", "firstname": "Tomek", "lastname": "Majewski"},
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_update_competitor_persists(self, admin_client, match_id, client):
        admin_client.post(
            f"/admin/api/competitors/{match_id}",
            json={"comp_id": "301", "firstname": "Nowe", "lastname": "Nazwisko"},
        )
        match_data = client.get(f"/api/matches/{match_id}").get_json()
        updated = next(c for c in match_data["competitors"] if c["comp_id"] == "301")
        assert updated["firstname"] == "Nowe"
        assert updated["lastname"] == "Nazwisko"

    def test_update_competitor_missing_fields_returns_400(self, admin_client, match_id):
        r = admin_client.post(
            f"/admin/api/competitors/{match_id}",
            json={"comp_id": "301"},  # brak firstname i lastname
        )
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")

    def test_update_nonexistent_competitor_returns_404(self, admin_client, match_id):
        r = admin_client.post(
            f"/admin/api/competitors/{match_id}",
            json={"comp_id": "9999", "firstname": "X", "lastname": "Y"},
        )
        assert r.status_code == 404

    def test_delete_competitor(self, admin_client, match_id):
        r = admin_client.delete(f"/admin/api/competitors/{match_id}/301")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_deleted_competitor_not_in_match(self, admin_client, match_id, client):
        admin_client.delete(f"/admin/api/competitors/{match_id}/301")
        match_data = client.get(f"/api/matches/{match_id}").get_json()
        comp_ids = [c["comp_id"] for c in match_data["competitors"]]
        assert "301" not in comp_ids

    def test_delete_nonexistent_competitor_returns_404(self, admin_client, match_id):
        r = admin_client.delete(f"/admin/api/competitors/{match_id}/9999")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET/POST /admin/api/divisions-mapping
# ---------------------------------------------------------------------------

class TestDivisionsMappingApi:
    def test_get_returns_200(self, admin_client, match_id):
        r = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id}")
        assert r.status_code == 200

    def test_get_response_structure(self, admin_client, match_id):
        data = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id}").get_json()
        assert "standard_divisions" in data
        assert "mappings" in data
        assert "imported_divisions" in data

    def test_standard_divisions_populated(self, admin_client, match_id):
        data = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id}").get_json()
        assert len(data["standard_divisions"]) == 17

    def test_set_mapping_returns_ok(self, admin_client, match_id):
        r = admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "Open", "mapped_division_id": 2},
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_set_mapping_persists(self, admin_client, match_id):
        admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "STD", "mapped_division_id": 3},
        )
        data = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id}").get_json()
        assert "STD" in data["mappings"]
        assert data["mappings"]["STD"]["mapped_division_id"] == 3

    def test_set_mapping_with_color(self, admin_client, match_id):
        admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "OPN",
                  "mapped_division_id": 2, "mapped_division_color": "#aabbcc"},
        )
        data = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id}").get_json()
        assert data["mappings"]["OPN"]["color"] == "#aabbcc"

    def test_missing_match_id_returns_400(self, admin_client):
        r = admin_client.post(
            "/admin/api/divisions-mapping",
            json={"source_division": "Open", "mapped_division_id": 2},
        )
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")

    def test_missing_source_division_returns_400(self, admin_client, match_id):
        r = admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "mapped_division_id": 2},
        )
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")


# ---------------------------------------------------------------------------
# POST /admin/api/divisions-mapping/copy
# ---------------------------------------------------------------------------

class TestDivisionsMappingCopy:
    @pytest.fixture()
    def match_id2(self, app):
        from database import save_match
        with app.app_context():
            return save_match(SAMPLE_MATCH)

    def test_copy_returns_ok(self, admin_client, match_id, match_id2):
        admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "Open", "mapped_division_id": 2},
        )
        r = admin_client.post(
            "/admin/api/divisions-mapping/copy",
            json={"source_match_id": match_id, "target_match_id": match_id2},
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_copy_propagates_mappings(self, admin_client, match_id, match_id2):
        admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "Open", "mapped_division_id": 2},
        )
        admin_client.post(
            "/admin/api/divisions-mapping/copy",
            json={"source_match_id": match_id, "target_match_id": match_id2},
        )
        data = admin_client.get(f"/admin/api/divisions-mapping?match_id={match_id2}").get_json()
        assert "Open" in data["mappings"]

    def test_same_id_source_target_returns_400(self, admin_client, match_id):
        r = admin_client.post(
            "/admin/api/divisions-mapping/copy",
            json={"source_match_id": match_id, "target_match_id": match_id},
        )
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")

    def test_missing_ids_returns_400(self, admin_client):
        r = admin_client.post(
            "/admin/api/divisions-mapping/copy",
            json={"source_match_id": 1},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Standard Divisions CRUD
# ---------------------------------------------------------------------------

class TestStandardDivisionsApi:
    def test_get_returns_17_divisions(self, admin_client):
        data = admin_client.get("/admin/api/standard-divisions").get_json()
        assert len(data["standard_divisions"]) == 17

    def test_each_division_conforms_to_schema(self, admin_client):
        data = admin_client.get("/admin/api/standard-divisions").get_json()
        schema = json.loads((SCHEMAS_DIR / "division.json").read_text())
        for div in data["standard_divisions"]:
            jsonschema.validate(div, schema)

    def test_add_division_returns_ok(self, admin_client):
        r = admin_client.post(
            "/admin/api/standard-divisions",
            json={"id": 99, "name": "Test Division"},
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_added_division_appears_in_list(self, admin_client):
        admin_client.post(
            "/admin/api/standard-divisions",
            json={"id": 98, "name": "Visible Division"},
        )
        data = admin_client.get("/admin/api/standard-divisions").get_json()
        names = [d["name"] for d in data["standard_divisions"]]
        assert "Visible Division" in names

    def test_add_duplicate_id_returns_400(self, admin_client):
        r = admin_client.post(
            "/admin/api/standard-divisions",
            json={"id": 1, "name": "Duplicate"},  # id=1 (Modified) już istnieje
        )
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")

    def test_add_missing_name_returns_400(self, admin_client):
        r = admin_client.post(
            "/admin/api/standard-divisions",
            json={"id": 97},
        )
        assert r.status_code == 400

    def test_update_division_returns_ok(self, admin_client):
        r = admin_client.put(
            "/admin/api/standard-divisions/1",
            json={"name": "Modified Updated"},
        )
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_update_persists(self, admin_client):
        admin_client.put("/admin/api/standard-divisions/2", json={"name": "Open v2"})
        data = admin_client.get("/admin/api/standard-divisions").get_json()
        div = next(d for d in data["standard_divisions"] if d["id"] == 2)
        assert div["name"] == "Open v2"

    def test_update_missing_name_returns_400(self, admin_client):
        r = admin_client.put("/admin/api/standard-divisions/1", json={})
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")

    def test_delete_unused_division(self, admin_client):
        # Dodaj nową i usuń ją (bez mapowań)
        admin_client.post("/admin/api/standard-divisions", json={"id": 96, "name": "To Delete"})
        r = admin_client.delete("/admin/api/standard-divisions/96")
        assert r.status_code == 200
        assert r.get_json()["ok"] is True

    def test_deleted_division_not_in_list(self, admin_client):
        admin_client.post("/admin/api/standard-divisions", json={"id": 95, "name": "Gone"})
        admin_client.delete("/admin/api/standard-divisions/95")
        data = admin_client.get("/admin/api/standard-divisions").get_json()
        assert all(d["id"] != 95 for d in data["standard_divisions"])

    def test_delete_division_used_in_mapping_returns_400(self, admin_client, match_id):
        # Ustaw mapowanie na dywizję id=3 (Standard)
        admin_client.post(
            "/admin/api/divisions-mapping",
            json={"match_id": match_id, "source_division": "STD", "mapped_division_id": 3},
        )
        r = admin_client.delete("/admin/api/standard-divisions/3")
        assert r.status_code == 400
        _validate(r.get_json(), "error.json")


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

class TestUsersApi:
    def test_returns_200(self, admin_client):
        r = admin_client.get("/admin/users")
        assert r.status_code == 200

    def test_returns_list(self, admin_client):
        data = admin_client.get("/admin/users").get_json()
        assert isinstance(data, list)

    def test_user_fields_present(self, admin_client):
        data = admin_client.get("/admin/users").get_json()
        assert len(data) >= 1
        u = data[0]
        for field in ("id", "username", "created_at"):
            assert field in u

    def test_no_password_hash_in_response(self, admin_client):
        data = admin_client.get("/admin/users").get_json()
        for u in data:
            assert "password_hash" not in u
