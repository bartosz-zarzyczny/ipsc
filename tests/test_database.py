"""
test_database.py — testy kontraktowe warstwy bazy danych

Pokrycie:
  - save_match / get_match / list_matches / delete_match
  - add_ranking / get_ranking / update_ranking / delete_ranking
  - add_match_to_ranking / ranking lifecycle
  - set_division_mapping / get_all_division_mappings / copy_division_mappings
  - apply_division_mappings (transformacja efemeryczna)
  - add_user / verify_user / list_users / delete_user
"""
import json
import pytest
import database as db


# ---------------------------------------------------------------------------
# Fixtures lokalne
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_match_data():
    """Minimalny poprawny wynik zawodów zgodny ze spec/schemas/match.json."""
    return {
        "match": {"name": "Test Match", "date": "2026-01-15", "level": 2},
        "stages": [
            {"id": "1", "name": "Stage 1", "max_points": 60, "max_hf_by_div": {"Open": 8.0}},
        ],
        "competitors": [
            {
                "rank": 1, "comp_id": "101",
                "firstname": "Jan", "lastname": "Kowalski", "name": "Kowalski Jan",
                "division": "Open", "div_id": "1", "category": "", "female": False,
                "squad": "A", "is_disq": False,
                "total_points": 60.0, "total_points_overall": 60.0, "total_points_in_division": 60.0,
                "total_time": 10.0, "overall_hf": 6.0, "pct": 100.0,
                "stage_scores": [{"pts": 60.0, "time": 10.0, "hf": 6.0,
                                   "A": 6, "B": 0, "C": 0, "D": 0, "M": 0, "PE": 0, "NS": 0, "disq": False}],
            },
            {
                "rank": 2, "comp_id": "102",
                "firstname": "Anna", "lastname": "Nowak", "name": "Nowak Anna",
                "division": "Open", "div_id": "1", "category": "Lady", "female": True,
                "squad": "B", "is_disq": False,
                "total_points": 45.0, "total_points_overall": 45.0, "total_points_in_division": 45.0,
                "total_time": 12.5, "overall_hf": 3.6, "pct": 75.0,
                "stage_scores": [{"pts": 45.0, "time": 12.5, "hf": 3.6,
                                   "A": 4, "B": 1, "C": 1, "D": 0, "M": 0, "PE": 0, "NS": 0, "disq": False}],
            },
        ],
    }


@pytest.fixture()
def saved_match_id(app, sample_match_data):
    """Zapisuje `sample_match_data` w testowej DB i zwraca id."""
    with app.app_context():
        return db.save_match(sample_match_data)


# ---------------------------------------------------------------------------
# save_match / get_match
# ---------------------------------------------------------------------------

class TestSaveAndGetMatch:
    def test_save_returns_integer_id(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
        assert isinstance(mid, int)
        assert mid >= 1

    def test_get_match_returns_same_structure(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
            result = db.get_match(mid)
        assert result is not None
        assert result["match"]["name"] == "Test Match"
        assert len(result["stages"]) == 1
        assert len(result["competitors"]) == 2

    def test_get_match_nonexistent_returns_none(self, app):
        with app.app_context():
            assert db.get_match(99999) is None

    def test_multiple_saves_give_unique_ids(self, app, sample_match_data):
        with app.app_context():
            ids = [db.save_match(sample_match_data) for _ in range(3)]
        assert len(set(ids)) == 3


# ---------------------------------------------------------------------------
# list_matches
# ---------------------------------------------------------------------------

class TestListMatches:
    def test_empty_db_returns_empty_list(self, app):
        with app.app_context():
            assert db.list_matches() == []

    def test_saved_match_appears_in_list(self, app, saved_match_id):
        with app.app_context():
            matches = db.list_matches()
        assert any(m["id"] == saved_match_id for m in matches)

    def test_list_has_expected_fields(self, app, saved_match_id):
        with app.app_context():
            matches = db.list_matches()
        m = next(x for x in matches if x["id"] == saved_match_id)
        for field in ("id", "name", "date", "level", "multiplier", "created_at", "ranking_ids"):
            assert field in m, f"Brak pola '{field}' w list_matches()"


# ---------------------------------------------------------------------------
# delete_match
# ---------------------------------------------------------------------------

class TestDeleteMatch:
    def test_delete_existing_returns_true(self, app, saved_match_id):
        with app.app_context():
            result = db.delete_match(saved_match_id)
        assert result is True

    def test_deleted_match_not_retrievable(self, app, saved_match_id):
        with app.app_context():
            db.delete_match(saved_match_id)
            assert db.get_match(saved_match_id) is None

    def test_delete_nonexistent_returns_false(self, app):
        with app.app_context():
            assert db.delete_match(99999) is False


# ---------------------------------------------------------------------------
# Rankings CRUD
# ---------------------------------------------------------------------------

class TestRankings:
    def test_add_ranking_returns_id(self, app):
        with app.app_context():
            rid = db.add_ranking("Liga 2026")
        assert isinstance(rid, int) and rid >= 1

    def test_get_ranking_returns_correct_data(self, app):
        with app.app_context():
            rid = db.add_ranking("Liga", top_matches_count=3)
            r = db.get_ranking(rid)
        assert r["name"] == "Liga"
        assert r["top_matches_count"] == 3
        assert r["match_ids"] == []
        assert r["match_count"] == 0

    def test_get_ranking_nonexistent_returns_none(self, app):
        with app.app_context():
            assert db.get_ranking(99999) is None

    def test_update_ranking_name(self, app):
        with app.app_context():
            rid = db.add_ranking("Stara Nazwa")
            db.update_ranking(rid, "Nowa Nazwa")
            r = db.get_ranking(rid)
        assert r["name"] == "Nowa Nazwa"

    def test_delete_empty_ranking(self, app):
        with app.app_context():
            rid = db.add_ranking("Do usunięcia")
            assert db.delete_ranking(rid) is True
            assert db.get_ranking(rid) is None

    def test_delete_nonempty_ranking_refused(self, app, saved_match_id):
        with app.app_context():
            rid = db.add_ranking("Z zawodami")
            db.add_match_to_ranking(rid, saved_match_id)
            assert db.delete_ranking(rid) is False

    def test_list_rankings_includes_new_ranking(self, app):
        with app.app_context():
            rid = db.add_ranking("Widoczny")
            rankings = db.list_rankings()
        assert any(r["id"] == rid for r in rankings)


# ---------------------------------------------------------------------------
# add_match_to_ranking
# ---------------------------------------------------------------------------

class TestMatchToRanking:
    def test_match_appears_in_ranking(self, app, saved_match_id):
        with app.app_context():
            rid = db.add_ranking("Test")
            db.add_match_to_ranking(rid, saved_match_id)
            r = db.get_ranking(rid)
        assert saved_match_id in r["match_ids"]
        assert r["match_count"] == 1

    def test_duplicate_add_is_idempotent(self, app, saved_match_id):
        with app.app_context():
            rid = db.add_ranking("Test2")
            db.add_match_to_ranking(rid, saved_match_id)
            db.add_match_to_ranking(rid, saved_match_id)
            r = db.get_ranking(rid)
        assert r["match_count"] == 1


# ---------------------------------------------------------------------------
# Division Mappings
# ---------------------------------------------------------------------------

class TestDivisionMappings:
    def test_set_and_get_mapping(self, app, saved_match_id):
        with app.app_context():
            db.set_division_mapping(saved_match_id, "STD", mapped_division_id=3)
            mappings = db.get_all_division_mappings(saved_match_id)
        assert "STD" in mappings
        assert mappings["STD"]["mapped_division_id"] == 3

    def test_set_mapping_with_color(self, app, saved_match_id):
        with app.app_context():
            db.set_division_mapping(saved_match_id, "OPN", mapped_division_id=2, color="#ff0000")
            mappings = db.get_all_division_mappings(saved_match_id)
        assert mappings["OPN"]["color"] == "#ff0000"

    def test_overwrite_mapping_is_idempotent(self, app, saved_match_id):
        with app.app_context():
            db.set_division_mapping(saved_match_id, "MOD", mapped_division_id=1)
            db.set_division_mapping(saved_match_id, "MOD", mapped_division_id=4)
            mappings = db.get_all_division_mappings(saved_match_id)
        assert mappings["MOD"]["mapped_division_id"] == 4

    def test_null_id_and_no_color_deletes_mapping(self, app, saved_match_id):
        with app.app_context():
            db.set_division_mapping(saved_match_id, "TMP", mapped_division_id=2)
            db.set_division_mapping(saved_match_id, "TMP", mapped_division_id=None, color=None)
            mappings = db.get_all_division_mappings(saved_match_id)
        assert "TMP" not in mappings

    def test_empty_db_returns_empty_mappings(self, app, saved_match_id):
        with app.app_context():
            mappings = db.get_all_division_mappings(saved_match_id)
        assert mappings == {}

    def test_copy_mappings_to_new_match(self, app, sample_match_data):
        with app.app_context():
            mid1 = db.save_match(sample_match_data)
            mid2 = db.save_match(sample_match_data)
            db.set_division_mapping(mid1, "Open", mapped_division_id=2, color="#0000ff")
            db.set_division_mapping(mid1, "Standard", mapped_division_id=3)
            db.copy_division_mappings(mid1, mid2)
            mappings2 = db.get_all_division_mappings(mid2)
        assert "Open" in mappings2
        assert "Standard" in mappings2
        assert mappings2["Open"]["color"] == "#0000ff"

    def test_copy_mappings_is_idempotent(self, app, sample_match_data):
        with app.app_context():
            mid1 = db.save_match(sample_match_data)
            mid2 = db.save_match(sample_match_data)
            db.set_division_mapping(mid1, "Open", mapped_division_id=2)
            db.copy_division_mappings(mid1, mid2)
            db.copy_division_mappings(mid1, mid2)  # drugi raz
            mappings2 = db.get_all_division_mappings(mid2)
        assert mappings2["Open"]["mapped_division_id"] == 2


# ---------------------------------------------------------------------------
# apply_division_mappings
# ---------------------------------------------------------------------------

class TestApplyDivisionMappings:
    def test_renames_division_when_mapped(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
            # "Open" (id=1 w default divisions) → mapujemy na Standard (id=3)
            db.set_division_mapping(mid, "Open", mapped_division_id=3)
            result = db.apply_division_mappings(sample_match_data, mid)
        open_comps = [c for c in result["competitors"] if c.get("_original_division") == "Open"]
        assert all(c["division"] == "Standard" for c in open_comps)

    def test_original_division_preserved(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
            db.set_division_mapping(mid, "Open", mapped_division_id=3)
            result = db.apply_division_mappings(sample_match_data, mid)
        for c in result["competitors"]:
            if c.get("_original_division"):
                assert c["_original_division"] == "Open"

    def test_no_mappings_returns_unchanged_data(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
            result = db.apply_division_mappings(sample_match_data, mid)
        divisions = [c["division"] for c in result["competitors"]]
        assert "Open" in divisions

    def test_does_not_mutate_input(self, app, sample_match_data):
        import copy
        original = copy.deepcopy(sample_match_data)
        with app.app_context():
            mid = db.save_match(sample_match_data)
            db.set_division_mapping(mid, "Open", mapped_division_id=3)
            db.apply_division_mappings(sample_match_data, mid)
        # Oryginał nie zmieniony
        assert sample_match_data["competitors"][0]["division"] == original["competitors"][0]["division"]

    def test_color_injected_into_competitor(self, app, sample_match_data):
        with app.app_context():
            mid = db.save_match(sample_match_data)
            db.set_division_mapping(mid, "Open", mapped_division_id=2, color="#ff0000")
            result = db.apply_division_mappings(sample_match_data, mid)
        open_comps = [c for c in result["competitors"] if c.get("_original_division") == "Open"]
        assert all(c.get("division_color") == "#ff0000" for c in open_comps)

    def test_none_match_id_returns_unchanged(self, app, sample_match_data):
        with app.app_context():
            result = db.apply_division_mappings(sample_match_data, None)
        # Bez match_id nie można wyszukać mapowań — dane niezmienione
        assert result["match"]["name"] == sample_match_data["match"]["name"]


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

class TestUserManagement:
    def test_add_user_returns_id(self, app):
        with app.app_context():
            uid = db.add_user("testuser", "password123")
        assert isinstance(uid, int) and uid >= 1

    def test_verify_user_correct_password(self, app):
        with app.app_context():
            db.add_user("alice", "secret42")
            uid = db.verify_user("alice", "secret42")
        assert uid is not None

    def test_verify_user_wrong_password_returns_none(self, app):
        with app.app_context():
            db.add_user("bob", "correct")
            result = db.verify_user("bob", "wrong")
        assert result is None

    def test_verify_nonexistent_user_returns_none(self, app):
        with app.app_context():
            assert db.verify_user("no_such_user", "pass") is None

    def test_delete_user_succeeds_when_multiple_exist(self, app):
        with app.app_context():
            uid1 = db.add_user("user1", "pw1")
            db.add_user("user2", "pw2")
            result = db.delete_user(uid1)
        assert result is True

    def test_delete_last_user_refused(self, app):
        # conftest już tworzy jednego admina — usuń go i spróbuj usunąć ostatniego
        with app.app_context():
            users = db.list_users()
            if len(users) == 1:
                result = db.delete_user(users[0]["id"])
                assert result is False
