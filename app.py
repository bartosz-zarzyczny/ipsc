#!/usr/bin/env python3
"""
WinMSS Web UI – przeglądarkowy interfejs do wyników zawodów strzeleckich.

Uruchom:  python3 app.py
Otwórz:   http://localhost:5000
"""

from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import tempfile
import threading
import webbrowser
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

from winmss_results import (
    load_data, build_results, rank_competitors, add_percent_of_best
)
from database import init_db, save_match, list_matches, get_match, delete_match, add_user, verify_user, list_users, delete_user, change_password

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

init_db()


def admin_required(f):
    """Decorator: wymaga zalogowania do panelu admina."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "Wymagane zalogowanie"}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


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
                "total_points_overall": c.get("total_points_overall", c["total_points"]),
                "total_points_in_division": c.get("total_points_in_division", c["total_points"]),
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
                        "NS": sc.get("NS", 0),
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
        match_id = save_match(result)
        result["match"]["id"] = match_id
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
        result = _prepare(path)
        match_id = save_match(result)
        result["match"]["id"] = match_id
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Błąd przetwarzania: {exc}"}), 500


@app.route("/api/check-local")
def check_local():
    exists = os.path.exists(os.path.join(os.getcwd(), "WinMSS.cab"))
    return jsonify({"exists": exists})


@app.route("/api/matches")
def api_list_matches():
    """Zwraca listę zapisanych zawodów."""
    return jsonify(list_matches())


@app.route("/api/matches/<int:match_id>")
def api_get_match(match_id):
    """Zwraca dane zapisanych zawodów."""
    result = get_match(match_id)
    if result is None:
        return jsonify({"error": "Nie znaleziono zawodów"}), 404
    result["match"]["id"] = match_id
    return jsonify(result)


@app.route("/api/matches/<int:match_id>", methods=["DELETE"])
@admin_required
def api_delete_match(match_id):
    """Usuwa zapisane zawody."""
    if delete_match(match_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Nie znaleziono zawodów"}), 404


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pwd  = request.form.get("password", "")
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        if verify_user(user, pwd_hash):
            session["admin"] = True
            session["username"] = user
            return redirect(url_for("admin_panel"))
        return render_template("admin_login.html", error="Nieprawidłowy login lub hasło")
    return render_template("admin_login.html", error=None)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("username", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_panel():
    matches = list_matches()
    users = list_users()
    return render_template("admin.html", matches=matches, users=users)


@app.route("/admin/upload", methods=["POST"])
@admin_required
def admin_upload():
    """Upload .cab z panelu admina."""
    f = request.files.get("file")
    if not f or not f.filename:
        return redirect(url_for("admin_panel"))
    if not f.filename.lower().endswith(".cab"):
        return redirect(url_for("admin_panel"))

    tmp = tempfile.NamedTemporaryFile(suffix=".cab", delete=False)
    try:
        f.save(tmp.name)
        tmp.close()
        result = _prepare(tmp.name)
        save_match(result)
    finally:
        os.unlink(tmp.name)
    return redirect(url_for("admin_panel"))


@app.route("/admin/delete/<int:match_id>", methods=["POST"])
@admin_required
def admin_delete(match_id):
    delete_match(match_id)
    return redirect(url_for("admin_panel"))


@app.route("/admin/users", methods=["GET"])
@admin_required
def admin_users_list():
    """List all users (API)."""
    return jsonify(list_users())


@app.route("/admin/users", methods=["POST"])
@admin_required
def admin_create_user():
    """Create a new user."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    
    if not username or not password:
        return redirect(url_for("admin_panel"))
    
    try:
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        add_user(username, pwd_hash)
    except Exception:
        pass  # Username already exists or other error
    
    return redirect(url_for("admin_panel"))


@app.route("/admin/users/<int:user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    """Delete a user."""
    delete_user(user_id)
    return redirect(url_for("admin_panel"))


@app.route("/admin/change-password", methods=["POST"])
@admin_required
def admin_change_password():
    """Change password for logged-in user."""
    username = session.get("username")
    current_pwd = request.form.get("current_password", "")
    new_pwd = request.form.get("new_password", "")
    confirm_pwd = request.form.get("confirm_password", "")
    
    # Validate inputs
    if not current_pwd or not new_pwd or not confirm_pwd:
        return redirect(url_for("admin_panel") + "?tab=users&error=Puste+pola")
    
    if new_pwd != confirm_pwd:
        return redirect(url_for("admin_panel") + "?tab=users&error=Has%C5%82a+nie+zgadzaj%C4%85+si%C4%99")
    
    # Verify current password
    current_hash = hashlib.sha256(current_pwd.encode()).hexdigest()
    if not verify_user(username, current_hash):
        return redirect(url_for("admin_panel") + "?tab=users&error=Nieprawid%C5%82owe+has%C5%82o")
    
    # Update password
    new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
    change_password(session.get("username"), new_hash)
    
    return redirect(url_for("admin_panel") + "?tab=users&success=Has%C5%82o+zmienione")


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    
    # Konfiguracja dla lokalnego uruchamiania vs Docker
    is_docker = os.path.exists('/.dockerenv')
    
    if not is_docker:
        # Lokalnie - otwórz przeglądarkę
        def _open():
            webbrowser.open("http://localhost:5000")
        threading.Timer(1.2, _open).start()
        print("WinMSS Web UI → http://localhost:5000  (Ctrl+C aby zatrzymać)")
    else:
        # Docker - słuchaj na 0.0.0.0
        print("WinMSS Web UI running in Docker on 0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
