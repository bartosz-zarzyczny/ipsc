"""
test_parser.py — testy kontraktowe modułu winmss_results.py

Testujemy funkcje "pure" (bez pliku .cab):
  - parse_winmss_xml()
  - build_results()
  - rank_competitors()
  - add_percent_of_best()
  - DIVISION_NAMES / CATEGORY_NAMES mappings

Testy wymagające rozpakowania .cab pomijamy (brak narzędzia w CI) — objęte
osobnym testem integracyjnym gdy narzędzie cabextract jest dostępne.
"""
import pytest
import tempfile
import os
from winmss_results import (
    parse_winmss_xml,
    build_results,
    rank_competitors,
    add_percent_of_best,
    DIVISION_NAMES,
    CATEGORY_NAMES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_xml_file(rows: list[dict]) -> str:
    """Zapisuje listę słowników jako plik XML w formacie rowset WinMSS i zwraca ścieżkę."""
    attrs = ""
    for row in rows:
        attr_str = " ".join(f"{k}='{v}'" for k, v in row.items())
        attrs += f"  <z:row {attr_str}/>\n"
    content = f"<xml xmlns:z='#RowsetSchema'>\n{attrs}</xml>"
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


def _minimal_data(*, n_stages=2, n_competitors=2) -> dict:
    """Buduje minimalny słownik danych kompatybilny z build_results()."""
    match = [{"MatchName": "Test Match L2", "MatchDt": "2026-01-15", "MatchLevel": "2"}]
    stages = [
        {"StageId": str(i + 1), "StageName": f"Stage {i+1}", "MaxPoints": "60"}
        for i in range(n_stages)
    ]
    members = [
        {"MemberId": str(m + 1), "Lastname": f"Last{m}", "Firstname": f"First{m}", "Female": "false"}
        for m in range(n_competitors)
    ]
    enrolled = [
        {"MemberId": str(m + 1), "CompId": str(100 + m), "DivId": "1", "CatId": "0", "IsDisq": "False", "SquadId": "A"}
        for m in range(n_competitors)
    ]
    scores = []
    for m in range(n_competitors):
        for s in range(n_stages):
            hf_base = (n_competitors - m) * 3.0 + s  # wyższy rank = wyższy HF
            time = 10.0 + m * 2 + s
            pts = int(hf_base * time)
            scores.append({
                "MemberId": str(m + 1),
                "StageId": str(s + 1),
                "ScoreA": "6", "ScoreB": "0", "ScoreC": "0", "ScoreD": "0",
                "Misses": "0", "ProcError": "0", "Penalties": "0",
                "ShootTime": str(time),
                "FinalScore": str(pts),
                "IsDisq": "False",
            })
    return {
        "match": match, "stages": stages, "members": members,
        "enrolled": enrolled, "scores": scores,
        "clubs": [], "squads": [],
    }


# ---------------------------------------------------------------------------
# parse_winmss_xml
# ---------------------------------------------------------------------------

class TestParseWinmssXml:
    def test_empty_file_returns_empty_list(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False)
        f.write("<xml></xml>")
        f.close()
        try:
            result = parse_winmss_xml(f.name)
            assert result == []
        finally:
            os.unlink(f.name)

    def test_parses_single_row(self):
        path = _make_xml_file([{"MemberId": "1", "Lastname": "Smith", "Firstname": "John"}])
        try:
            rows = parse_winmss_xml(path)
            assert len(rows) == 1
            assert rows[0]["MemberId"] == "1"
            assert rows[0]["Lastname"] == "Smith"
            assert rows[0]["Firstname"] == "John"
        finally:
            os.unlink(path)

    def test_parses_multiple_rows(self):
        path = _make_xml_file([
            {"StageId": "1", "StageName": "Alpha"},
            {"StageId": "2", "StageName": "Bravo"},
            {"StageId": "3", "StageName": "Charlie"},
        ])
        try:
            rows = parse_winmss_xml(path)
            assert len(rows) == 3
            assert [r["StageId"] for r in rows] == ["1", "2", "3"]
        finally:
            os.unlink(path)

    def test_handles_special_characters_in_values(self):
        path = _make_xml_file([{"MatchName": "Zawody Strzeleckie 2026", "MatchLevel": "2"}])
        try:
            rows = parse_winmss_xml(path)
            assert rows[0]["MatchName"] == "Zawody Strzeleckie 2026"
        finally:
            os.unlink(path)

    def test_handles_missing_file(self):
        with pytest.raises((FileNotFoundError, OSError)):
            parse_winmss_xml("/nonexistent/path/file.xml")

    def test_multiline_attributes(self):
        # Rowset z wieloma atrybutami w jednym wierszu
        path = _make_xml_file([{
            "MemberId": "42", "Lastname": "Doe", "Firstname": "Jane",
            "Female": "true", "RegionId": "PL",
        }])
        try:
            rows = parse_winmss_xml(path)
            assert rows[0]["Female"] == "true"
            assert rows[0]["RegionId"] == "PL"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# DIVISION_NAMES / CATEGORY_NAMES
# ---------------------------------------------------------------------------

class TestMappingTables:
    def test_division_names_has_open(self):
        assert "Open" in DIVISION_NAMES.values()

    def test_division_names_has_standard(self):
        assert "Standard" in DIVISION_NAMES.values()

    def test_division_names_keys_are_strings(self):
        for k in DIVISION_NAMES:
            assert isinstance(k, str), f"Klucz {k!r} powinien być str"

    def test_category_names_has_empty_default(self):
        assert CATEGORY_NAMES.get("0") == ""

    def test_category_names_lady(self):
        assert CATEGORY_NAMES.get("1") == "Lady"

    def test_known_division_ids(self):
        # Najważniejsze ID które muszą być zmapowane
        for div_id in ("1", "2", "4", "5"):
            assert div_id in DIVISION_NAMES, f"Brak div_id={div_id}"


# ---------------------------------------------------------------------------
# build_results
# ---------------------------------------------------------------------------

class TestBuildResults:
    def test_returns_tuple_of_three(self):
        data = _minimal_data(n_stages=2, n_competitors=2)
        result = build_results(data)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_match_info_is_dict(self):
        data = _minimal_data()
        match_info, _, _ = build_results(data)
        assert isinstance(match_info, dict)
        assert "MatchName" in match_info

    def test_stages_list_length(self):
        data = _minimal_data(n_stages=3, n_competitors=1)
        _, stages, _ = build_results(data)
        assert len(stages) == 3

    def test_competitors_list_length(self):
        data = _minimal_data(n_stages=2, n_competitors=4)
        _, _, comps = build_results(data)
        assert len(comps) == 4

    def test_competitor_has_required_fields(self):
        data = _minimal_data(n_stages=2, n_competitors=1)
        _, _, comps = build_results(data)
        c = comps[0]
        for field in ("comp_id", "firstname", "lastname", "division", "div_id",
                      "category", "female", "is_disq", "stage_scores",
                      "total_points", "total_time", "overall_hf"):
            assert field in c, f"Brak pola '{field}' w zawodniku"

    def test_stage_scores_length_matches_stages(self):
        data = _minimal_data(n_stages=3, n_competitors=2)
        _, stages, comps = build_results(data)
        for c in comps:
            assert len(c["stage_scores"]) == len(stages)

    def test_stage_score_has_required_fields(self):
        data = _minimal_data(n_stages=1, n_competitors=1)
        _, _, comps = build_results(data)
        sc = comps[0]["stage_scores"][0]
        assert sc is not None
        for field in ("A", "B", "C", "D", "M", "PE", "NS", "time", "hf", "pts", "disq"):
            assert field in sc, f"Brak pola '{field}' w stage_score"

    def test_missing_score_gives_none(self):
        data = _minimal_data(n_stages=2, n_competitors=1)
        # Usuń jeden score żeby stage_score był None
        data["scores"] = [s for s in data["scores"] if s["StageId"] != "2"]
        _, _, comps = build_results(data)
        assert comps[0]["stage_scores"][1] is None

    def test_disqualified_competitor(self):
        data = _minimal_data(n_stages=2, n_competitors=1)
        data["enrolled"][0]["IsDisq"] = "True"
        _, _, comps = build_results(data)
        assert comps[0]["is_disq"] is True

    def test_female_flag_parsed(self):
        data = _minimal_data(n_stages=1, n_competitors=1)
        data["members"][0]["Female"] = "true"
        _, _, comps = build_results(data)
        assert comps[0]["female"] is True

    def test_empty_match_list_gives_empty_match_info(self):
        data = _minimal_data(n_stages=1, n_competitors=1)
        data["match"] = []
        match_info, _, _ = build_results(data)
        assert match_info == {}

    def test_total_points_overall_present(self):
        data = _minimal_data(n_stages=2, n_competitors=2)
        _, _, comps = build_results(data)
        for c in comps:
            assert "total_points_overall" in c
            assert "total_points_in_division" in c


# ---------------------------------------------------------------------------
# rank_competitors
# ---------------------------------------------------------------------------

class TestRankCompetitors:
    def test_rank_field_assigned(self):
        data = _minimal_data(n_stages=2, n_competitors=3)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        ranks = [c["rank"] for c in ranked]
        assert sorted(ranks) == list(range(1, len(comps) + 1))

    def test_higher_points_gets_better_rank(self):
        data = _minimal_data(n_stages=2, n_competitors=2)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        # Zawodnik z wyższymi punktami powinien mieć rank=1
        rank1 = next(c for c in ranked if c["rank"] == 1)
        rank2 = next(c for c in ranked if c["rank"] == 2)
        assert rank1["total_points"] >= rank2["total_points"]

    def test_returns_list(self):
        data = _minimal_data(n_stages=1, n_competitors=1)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        assert isinstance(ranked, list)


# ---------------------------------------------------------------------------
# add_percent_of_best
# ---------------------------------------------------------------------------

class TestAddPercentOfBest:
    def test_pct_field_present(self):
        data = _minimal_data(n_stages=2, n_competitors=2)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        result = add_percent_of_best(ranked)
        for c in result:
            assert "pct" in c

    def test_best_competitor_has_100_pct(self):
        data = _minimal_data(n_stages=2, n_competitors=3)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        result = add_percent_of_best(ranked)
        rank1 = next(c for c in result if c["rank"] == 1)
        assert rank1["pct"] == pytest.approx(100.0, abs=0.01)

    def test_pct_between_0_and_100(self):
        data = _minimal_data(n_stages=2, n_competitors=3)
        _, _, comps = build_results(data)
        ranked = rank_competitors(comps)
        result = add_percent_of_best(ranked)
        for c in result:
            assert 0.0 <= c["pct"] <= 100.0
