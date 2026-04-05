"""
test_api_public.py — testy kontraktowe publicznych endpointów API

Weryfikuje że:
  - kształt odpowiedzi jest zgodny ze spec/schemas/match.json i ranking.json
  - kody HTTP są poprawne (200, 404)
  - endpointy są dostępne bez autentykacji
"""
import json
import pytest
import jsonschema
import pathlib


# ---------------------------------------------------------------------------
# Helpers — walidacja JSON Schema
# ---------------------------------------------------------------------------

SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "spec" / "schemas"

def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text())


def _validate(data, schema_name: str):
    """Waliduje dane względem schematu. Rzuca AssertionError przy błędzie."""
    schema = _load_schema(schema_name)
    # Budujemy resolver dla $ref między plikami schematów
    store = {}
    for p in SCHEMAS_DIR.glob("*.json"):
        s = json.loads(p.read_text())
        store[s["$id"]] = s
    resolver = jsonschema.RefResolver(
        base_uri=f"file://{SCHEMAS_DIR}/",
        referrer=schema,
        store={f"file://{SCHEMAS_DIR}/{k}": v for k, v in store.items()},
    )
    validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
    errors = list(validator.iter_errors(data))
    assert not errors, f"Schema '{schema_name}' błędy:\n" + "\n".join(
        f"  {e.json_path}: {e.message}" for e in errors
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MATCH = {
    "match": {"name": "Public Test Match", "date": "2026-02-10", "level": 2},
    "stages": [
        {"id": "1", "name": "Stage Alpha", "max_points": 60, "max_hf_by_div": {"Open": 7.5}},
    ],
    "competitors": [
        {
            "rank": 1, "comp_id": "201",
            "firstname": "Marek", "lastname": "Zieliński", "name": "Zieliński Marek",
            "division": "Open", "div_id": "1", "category": "", "female": False,
            "squad": "A", "is_disq": False,
            "total_points": 60.0, "total_points_overall": 60.0, "total_points_in_division": 60.0,
            "total_time": 8.0, "overall_hf": 7.5, "pct": 100.0,
            "stage_scores": [{"pts": 60.0, "time": 8.0, "hf": 7.5,
                               "A": 6, "B": 0, "C": 0, "D": 0, "M": 0, "PE": 0, "NS": 0, "disq": False}],
        },
    ],
}


@pytest.fixture()
def seeded_match_id(app):
    """Zapisuje SAMPLE_MATCH w DB i zwraca jego id."""
    from database import save_match
    with app.app_context():
        return save_match(SAMPLE_MATCH)


@pytest.fixture()
def seeded_ranking_id(app, seeded_match_id):
    """Tworzy ranking z jednym przypisanym meczem."""
    from database import add_ranking, add_match_to_ranking
    with app.app_context():
        rid = add_ranking("Public Ranking", top_matches_count=0)
        add_match_to_ranking(rid, seeded_match_id)
        return rid


# ---------------------------------------------------------------------------
# GET /api/matches
# ---------------------------------------------------------------------------

class TestListMatches:
    def test_returns_200(self, client):
        r = client.get("/api/matches")
        assert r.status_code == 200

    def test_returns_list(self, client):
        data = r = client.get("/api/matches")
        assert isinstance(client.get("/api/matches").get_json(), list)

    def test_saved_match_in_list(self, client, seeded_match_id):
        data = client.get("/api/matches").get_json()
        assert any(m["id"] == seeded_match_id for m in data)

    def test_empty_when_no_matches(self, client):
        assert client.get("/api/matches").get_json() == []

    def test_match_summary_has_required_fields(self, client, seeded_match_id):
        data = client.get("/api/matches").get_json()
        m = next(x for x in data if x["id"] == seeded_match_id)
        for field in ("id", "name", "date", "level", "multiplier", "created_at", "ranking_ids"):
            assert field in m, f"Brak pola '{field}'"


# ---------------------------------------------------------------------------
# GET /api/matches/<id>
# ---------------------------------------------------------------------------

class TestGetMatch:
    def test_returns_200_for_existing(self, client, seeded_match_id):
        r = client.get(f"/api/matches/{seeded_match_id}")
        assert r.status_code == 200

    def test_returns_404_for_nonexistent(self, client):
        r = client.get("/api/matches/99999")
        assert r.status_code == 404

    def test_404_body_conforms_to_error_schema(self, client):
        data = client.get("/api/matches/99999").get_json()
        _validate(data, "error.json")

    def test_response_conforms_to_match_schema(self, client, seeded_match_id):
        data = client.get(f"/api/matches/{seeded_match_id}").get_json()
        _validate(data, "match.json")

    def test_id_injected_in_response(self, client, seeded_match_id):
        data = client.get(f"/api/matches/{seeded_match_id}").get_json()
        assert data["match"]["id"] == seeded_match_id

    def test_stages_present(self, client, seeded_match_id):
        data = client.get(f"/api/matches/{seeded_match_id}").get_json()
        assert len(data["stages"]) == 1
        assert data["stages"][0]["name"] == "Stage Alpha"

    def test_competitors_present(self, client, seeded_match_id):
        data = client.get(f"/api/matches/{seeded_match_id}").get_json()
        assert len(data["competitors"]) == 1
        assert data["competitors"][0]["comp_id"] == "201"

    def test_stage_score_fields_present(self, client, seeded_match_id):
        data = client.get(f"/api/matches/{seeded_match_id}").get_json()
        sc = data["competitors"][0]["stage_scores"][0]
        for field in ("pts", "time", "hf", "A", "B", "C", "D", "M", "PE", "NS", "disq"):
            assert field in sc, f"Brak pola '{field}' w stage_score"


# ---------------------------------------------------------------------------
# GET /api/rankings
# ---------------------------------------------------------------------------

class TestListRankings:
    def test_returns_200(self, client):
        r = client.get("/api/rankings")
        assert r.status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/rankings").get_json(), list)

    def test_saved_ranking_in_list(self, client, seeded_ranking_id):
        data = client.get("/api/rankings").get_json()
        assert any(r["id"] == seeded_ranking_id for r in data)

    def test_ranking_summary_has_required_fields(self, client, seeded_ranking_id):
        data = client.get("/api/rankings").get_json()
        r = next(x for x in data if x["id"] == seeded_ranking_id)
        for field in ("id", "name", "top_matches_count", "created_at", "updated_at", "match_count"):
            assert field in r, f"Brak pola '{field}'"


# ---------------------------------------------------------------------------
# GET /api/rankings/<id>
# ---------------------------------------------------------------------------

class TestGetRanking:
    def test_returns_200_for_existing(self, client, seeded_ranking_id):
        r = client.get(f"/api/rankings/{seeded_ranking_id}")
        assert r.status_code == 200

    def test_returns_404_for_nonexistent(self, client):
        r = client.get("/api/rankings/99999")
        assert r.status_code == 404

    def test_404_body_conforms_to_error_schema(self, client):
        data = client.get("/api/rankings/99999").get_json()
        _validate(data, "error.json")

    def test_response_conforms_to_ranking_schema(self, client, seeded_ranking_id):
        data = client.get(f"/api/rankings/{seeded_ranking_id}").get_json()
        _validate(data, "ranking.json")

    def test_matches_embedded(self, client, seeded_ranking_id, seeded_match_id):
        data = client.get(f"/api/rankings/{seeded_ranking_id}").get_json()
        assert len(data["matches"]) == 1
        assert data["matches"][0]["match"]["id"] == seeded_match_id

    def test_match_ids_list_correct(self, client, seeded_ranking_id, seeded_match_id):
        data = client.get(f"/api/rankings/{seeded_ranking_id}").get_json()
        assert seeded_match_id in data["match_ids"]


# ---------------------------------------------------------------------------
# GET /api/translations
# ---------------------------------------------------------------------------

class TestTranslations:
    def test_default_language_returns_200(self, client):
        r = client.get("/api/translations")
        assert r.status_code == 200

    def test_returns_dict(self, client):
        data = client.get("/api/translations").get_json()
        assert isinstance(data, dict)

    def test_polish_language_explicit(self, client):
        r = client.get("/api/translations?lang=pl")
        assert r.status_code == 200

    def test_english_language(self, client):
        r = client.get("/api/translations?lang=en")
        assert r.status_code == 200

    def test_unknown_language_falls_back_to_pl(self, client):
        # Nieznany język — fallback do pl (nie 404)
        r = client.get("/api/translations?lang=xx")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/check-local
# ---------------------------------------------------------------------------

class TestCheckLocal:
    def test_returns_200(self, client):
        r = client.get("/api/check-local")
        assert r.status_code == 200

    def test_returns_exists_field(self, client):
        data = client.get("/api/check-local").get_json()
        assert "exists" in data
        assert isinstance(data["exists"], bool)
