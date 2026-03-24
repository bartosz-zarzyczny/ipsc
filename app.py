#!/usr/bin/env python3
"""
WinMSS Web UI – przeglądarkowy interfejs do wyników zawodów strzeleckich.

Uruchom:  python3 app.py
Otwórz:   http://localhost:5000
"""

from __future__ import annotations
import os
import tempfile
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify

from winmss_results import (
    load_data, build_results, rank_competitors, add_percent_of_best
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prepare(cab_path: str) -> dict:
    """Przetwarza plik .cab i zwraca słownik gotowy do serializacji JSON."""
    data = load_data(cab_path)
    match_info, stages, competitors = build_results(data)
    ranked = rank_competitors(competitors)
    ranked = add_percent_of_best(ranked)

    # Max HF per stage per division (potrzebne do % w torze w ramach dywizji)
    # stage_div_max_hf[stage_idx][division] = max HF
    stage_div_max_hf: list[dict[str, float]] = []
    for i, stg in enumerate(stages):
        div_hfs: dict[str, list[float]] = {}
        for c in ranked:
            if i < len(c["stage_scores"]) and c["stage_scores"][i] is not None:
                sc = c["stage_scores"][i]
                if not sc["disq"] and sc["hf"] > 0:
                    div_hfs.setdefault(c["division"], []).append(sc["hf"])
        stage_div_max_hf.append(
            {div: round(max(hfs), 4) for div, hfs in div_hfs.items()}
        )

    return {
        "match": {
            "name":  match_info.get("MatchName", "(brak nazwy)"),
            "date":  match_info.get("MatchDt", "")[:10],
            "level": int(match_info.get("MatchLevel", 0)) + 1,
        },
        "stages": [
            {
                "id":         s.get("StageId"),
                "name":       s.get("StageName", f"Stage {s.get('StageId')}"),
                "max_points": int(s.get("MaxPoints", 0)),
                "max_hf_by_div": stage_div_max_hf[i],
            }
            for i, s in enumerate(stages)
        ],
        "competitors": [
            {
                "rank":         c["rank"],
                "comp_id":      c["comp_id"],
                "name":         f"{c['lastname']} {c['firstname']}",
                "division":     c["division"],
                "div_id":       c["div_id"],
                "category":     c["category"],
                "female":       c["female"],
                "squad":        c["squad"],
                "is_disq":      c["is_disq"],
                "total_points": c["total_points"],
                "total_time":   round(c["total_time"], 2),
                "overall_hf":   round(c["overall_hf"], 4),
                "pct":          round(c.get("pct", 0.0), 2),
                "stage_scores": [
                    {
                        "pts":  sc["pts"],
                        "time": round(sc["time"], 2),
                        "hf":   round(sc["hf"], 4),
                        "A": sc["A"], "B": sc["B"],
                        "C": sc["C"], "D": sc["D"],
                        "M": sc["M"], "PE": sc["PE"],
                        "disq": sc["disq"],
                    } if sc else None
                    for sc in c["stage_scores"]
                ],
            }
            for c in ranked
        ],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "Brak pliku w żądaniu"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nie wybrano pliku"}), 400
    if not f.filename.lower().endswith(".cab"):
        return jsonify({"error": "Plik musi mieć rozszerzenie .cab"}), 400

    tmp = tempfile.NamedTemporaryFile(suffix=".cab", delete=False)
    try:
        f.save(tmp.name)
        tmp.close()
        result = _prepare(tmp.name)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Błąd przetwarzania: {exc}"}), 500
    finally:
        os.unlink(tmp.name)


@app.route("/api/analyze-local")
def analyze_local():
    """Analizuje WinMSS.cab z katalogu roboczego."""
    path = os.path.join(os.getcwd(), "WinMSS.cab")
    if not os.path.exists(path):
        return jsonify({"error": "Plik WinMSS.cab nie znaleziony w bieżącym katalogu"}), 404
    try:
        return jsonify(_prepare(path))
    except Exception as exc:
        return jsonify({"error": f"Błąd przetwarzania: {exc}"}), 500


@app.route("/api/check-local")
def check_local():
    exists = os.path.exists(os.path.join(os.getcwd(), "WinMSS.cab"))
    return jsonify({"exists": exists})


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    def _open():
        webbrowser.open("http://localhost:5050")

    threading.Timer(1.2, _open).start()
    print("WinMSS Web UI → http://localhost:5050  (Ctrl+C aby zatrzymać)")
    app.run(debug=False, port=5050)
