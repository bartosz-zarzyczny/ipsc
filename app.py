#!/usr/bin/env python3
"""
WinMSS Web UI – przeglądarkowy interfejs do wyników zawodów strzeleckich.

Uruchom:  python3 app.py
Otwórz:   http://localhost:5000
"""

from __future__ import annotations
import hashlib
import hmac
import json
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
from database import (
    init_db,
    save_match,
    list_matches,
    get_match,
    get_match_with_multiplier,
    delete_match,
    add_user,
    verify_user,
    list_users,
    delete_user,
    change_password,
    list_rankings,
    get_ranking,
    add_ranking,
    update_ranking,
    delete_ranking,
    add_match_to_ranking,
    update_match_rankings,
    update_match_multiplier,
    update_match_level,
    update_competitor_name,
    delete_competitor_from_match,
    get_division_mapping,
    set_division_mapping,
    get_all_division_mappings,
    get_imported_divisions,
    get_standard_divisions,
    get_standard_division,
    add_standard_division,
    update_standard_division,
    delete_standard_division,
    init_standard_divisions_from_json,
    apply_division_mappings,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

init_db()

# Dane dywizji są teraz w bazie danych (tabela standard_divisions)
# Zdedykowana funkcja do zapewnienia że są zawsze dostępne
def _ensure_standard_divisions_exist():
    """Ensure standard divisions exist in database. If not, create defaults."""
    existing = get_standard_divisions()
    if len(existing) > 0:
        print(f"✓ Dywizje już istniejące: {len(existing)} pozycji")
        return existing
    
    # Domyślne dywizje
    default_divisions = [
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
    
    print(f"[STARTUP] Baza nowa - wpisuję 17 domyślnych dywizji...")
    init_standard_divisions_from_json(default_divisions)
    return default_divisions

_ensure_standard_divisions_exist()


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

    # Wyodrębnij level z nazwy (szukaj różnych formatów)
    match_name = match_info.get("MatchName", "")
    import re
    
    def roman_to_int(roman):
        """Konwertuj cyfry rzymskie na arabskie"""
        roman_vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        total = 0
        prev_val = 0
        for char in reversed(roman.upper()):
            val = roman_vals.get(char, 0)
            if val < prev_val:
                total -= val
            else:
                total += val
            prev_val = val
        return total if total > 0 else None
    
    level = None
    
    # Spróbuj znaleźć wzory w tej kolejności (od Most specific do least specific):
    
    # 1. LEVEL 1, LEVEL 2, itd. (słowo + cyfra arabska)
    m = re.search(r'\bLEVEL\s+(\d+)\b', match_name, re.IGNORECASE)
    if m:
        level = int(m.group(1))
    
    # 2. LEVEL I, LEVEL II, itd. (słowo + cyfra rzymska)
    if not level:
        m = re.search(r'\bLEVEL\s+([IVX]+)\b', match_name, re.IGNORECASE)
        if m:
            roman_level = roman_to_int(m.group(1))
            if roman_level:
                level = roman_level
    
    # 3. L1, L2, L3, itd. (litera L + cyfra, unikając LEVEL)
    if not level:
        m = re.search(r'\bL\s*(\d+)(?!\w)', match_name, re.IGNORECASE)
        if m and not match_name[m.start():m.start()+5].upper().startswith('LEVEL'):
            level = int(m.group(1))
    
    # 4. L I, L II, L III, itd. (litera + cyfra rzymska)
    if not level:
        m = re.search(r'\bL\s+([IVX]+)\b', match_name, re.IGNORECASE)
        if m and not match_name[m.start():m.start()+5].upper().startswith('LEVEL'):
            roman_level = roman_to_int(m.group(1))
            if roman_level:
                level = roman_level
    
    # 5. Jeśli nie znalazł w nazwie, użyj wartości z danych
    if not level:
        level = int(match_info.get("MatchLevel", 1))
    
    return {
        "match": {
            "name":  match_name if match_name else "(brak nazwy)",
            "date":  match_info.get("MatchDt", "")[:10],
            "level": level,
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
                "firstname":    c["firstname"],
                "lastname":     c["lastname"],
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

@app.route("/api/set-language", methods=["POST"])
def set_language():
    """Ustaw język aplikacji i zapisz w ciastku"""
    data = request.get_json() or {}
    lang = data.get('language', 'pl')
    
    if lang not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Nieznany język"}), 400
    
    response = jsonify({"status": "ok", "language": lang})
    response.set_cookie('language', lang, max_age=31536000)  # 1 rok
    return response

@app.route("/api/translations", methods=["GET"])
def get_translations():
    """Pobierz tłumaczenia dla wybranego języka"""
    import json
    lang = request.args.get('lang', 'pl')
    
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'pl'
    
    translation_file = os.path.join(os.path.dirname(__file__), f'static/i18n/{lang}.json')
    
    try:
        with open(translation_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return jsonify(translations)
    except FileNotFoundError:
        return jsonify({"error": "Tłumaczenia nie znalezione"}), 404

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
    """Zwraca dane zapisanych zawodów (z aplikowanymi mapowaniami dywizji)."""
    result = get_match(match_id)
    if result is None:
        return jsonify({"error": "Nie znaleziono zawodów"}), 404
    result["match"]["id"] = match_id
    
    # Aplikuj mapowania dywizji
    result = apply_division_mappings(result)
    
    return jsonify(result)


@app.route("/api/matches/<int:match_id>", methods=["DELETE"])
@admin_required
def api_delete_match(match_id):
    """Usuwa zapisane zawody."""
    if delete_match(match_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Nie znaleziono zawodów"}), 404


@app.route("/api/rankings")
def api_list_rankings():
    """Zwraca listę zapisanych rankingów."""
    return jsonify(list_rankings())


@app.route("/api/rankings/<int:ranking_id>")
def api_get_ranking(ranking_id):
    """Zwraca dane zapisanego rankingu wraz z zawodami (z mnożnikami)."""
    result = get_ranking(ranking_id)
    if result is None:
        return jsonify({"error": "Nie znaleziono rankingu"}), 404
    
    # Pobierz dane dla wszystkich zawodów w rankingu (z multiplier)
    matches_data = []
    for match_id in result.get("match_ids", []):
        match_result = get_match_with_multiplier(match_id)
        if match_result:
            match_result["match"]["id"] = match_id
            matches_data.append(match_result)
    
    result["matches"] = matches_data
    return jsonify(result)


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pwd  = request.form.get("password", "")
        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        user_id = verify_user(user, pwd_hash)
        if user_id is not None:
            session["admin"] = True
            session["username"] = user
            session["user_id"] = user_id
            return redirect(url_for("admin_panel"))
        return render_template("admin_login.html", error="Nieprawidłowy login lub hasło")
    return render_template("admin_login.html", error=None)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("username", None)
    session.pop("user_id", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_panel():
    matches = list_matches()
    users = list_users()
    rankings = list_rankings()
    editing_ranking_id = request.args.get("edit_ranking_id", type=int)
    editing_ranking = get_ranking(editing_ranking_id) if editing_ranking_id else None
    return render_template(
        "admin.html",
        matches=matches,
        users=users,
        rankings=rankings,
        editing_ranking=editing_ranking,
    )


@app.route("/admin/upload", methods=["POST"])
@admin_required
def admin_upload():
    """Upload .cab z panelu admina oraz przypisanie do rankingu."""
    f = request.files.get("file")
    ranking_id = request.form.get("ranking_id", type=int)
    
    if not f or not f.filename:
        return redirect(url_for("admin_panel") + "?error=Nie+wybrano+pliku")
    if not f.filename.lower().endswith(".cab"):
        return redirect(url_for("admin_panel") + "?error=Plik+musi+mie%C4%87+rozszerzenie+.cab")
    if not ranking_id:
        return redirect(url_for("admin_panel") + "?error=Musisz+wybra%C4%87+ranking")

    tmp = tempfile.NamedTemporaryFile(suffix=".cab", delete=False)
    try:
        f.save(tmp.name)
        tmp.close()
        result = _prepare(tmp.name)
        match_id = save_match(result)
        # Przypisz zawody do wybranego rankingu
        add_match_to_ranking(ranking_id, match_id)
    except Exception as exc:
        return redirect(url_for("admin_panel") + f"?error=B%C5%82%C4%99d:+{str(exc)}")
    finally:
        os.unlink(tmp.name)
    return redirect(url_for("admin_panel") + "?success=Zawody+zaimportowane+i+przypisane+do+rankingu")


@app.route("/admin/matches/update", methods=["POST"])
@admin_required
def admin_update_match():
    """Update match level, ranking assignments and multiplier."""
    match_id = request.form.get("match_id", type=int)
    level = request.form.get("level", type=int) or 1
    ranking_ids = request.form.getlist("ranking_ids")
    multiplier = request.form.get("multiplier", type=float) or 1.0
    
    if not match_id:
        return redirect(url_for("admin_panel") + "?error=Brak+ID+zawodów")
    
    try:
        # Aktualizuj level
        update_match_level(match_id, level)
        
        # Aktualizuj ranking assignments i multiplier
        update_match_rankings(match_id, ranking_ids)
        update_match_multiplier(match_id, multiplier)
    except Exception as exc:
        return redirect(url_for("admin_panel") + f"?error=B%C5%82%C4%99d:+{str(exc)}")
    
    return redirect(url_for("admin_panel") + "?success=Zawody+zaktualizowane")


# Zachowaj stary endpoint dla kompatybilności
@app.route("/admin/matches/assign-rankings", methods=["POST"])
@admin_required
def admin_assign_rankings():
    """Update ranking assignments and multiplier for a match."""
    match_id = request.form.get("match_id", type=int)
    ranking_ids = request.form.getlist("ranking_ids")
    multiplier = request.form.get("multiplier", type=float) or 1.0
    
    if not match_id:
        return redirect(url_for("admin_panel") + "?error=Brak+ID+zawodów")
    
    try:
        update_match_rankings(match_id, ranking_ids)
        update_match_multiplier(match_id, multiplier)
    except Exception as exc:
        return redirect(url_for("admin_panel") + f"?error=B%C5%82%C4%99d:+{str(exc)}")
    
    return redirect(url_for("admin_panel") + "?success=Zawody+zaktualizowane")


@app.route("/admin/delete/<int:match_id>", methods=["POST"])
@admin_required
def admin_delete(match_id):
    delete_match(match_id)
    return redirect(url_for("admin_panel"))




@app.route("/admin/rankings", methods=["POST"])
@admin_required
def admin_create_ranking():
    name = request.form.get("name", "").strip()
    match_ids = request.form.getlist("match_ids")
    top_matches_count = request.form.get("top_matches_count", type=int) or 0

    if not name:
        return redirect(url_for("admin_panel", tab="rankings", error="Nazwa rankingu jest wymagana"))

    try:
        add_ranking(name, match_ids, top_matches_count)
    except Exception:
        return redirect(url_for("admin_panel", tab="rankings", error="Nie udało się dodać rankingu"))

    return redirect(url_for("admin_panel", tab="rankings", success="Ranking dodany"))


@app.route("/admin/rankings/<int:ranking_id>", methods=["POST"])
@admin_required
def admin_update_ranking_route(ranking_id):
    name = request.form.get("name", "").strip()
    match_ids = request.form.getlist("match_ids")
    top_matches_count = request.form.get("top_matches_count", type=int) or 0

    if not name:
        return redirect(url_for("admin_panel", tab="rankings", error="Nazwa rankingu jest wymagana"))

    try:
        updated = update_ranking(ranking_id, name, match_ids, top_matches_count)
    except Exception:
        return redirect(url_for("admin_panel", tab="rankings", error="Nie udało się zapisać rankingu"))

    if not updated:
        return redirect(url_for("admin_panel", tab="rankings", error="Nie znaleziono rankingu"))

    return redirect(url_for("admin_panel", tab="rankings", success="Ranking zapisany"))


@app.route("/admin/rankings/<int:ranking_id>/delete", methods=["POST"])
@admin_required
def admin_delete_ranking_route(ranking_id):
    ranking = get_ranking(ranking_id)
    if ranking is None:
        return redirect(url_for("admin_panel", tab="rankings", error="Nie znaleziono rankingu"))
    if ranking["match_count"] > 0:
        return redirect(url_for("admin_panel", tab="rankings", error="Nie można usunąć rankingu z przypisanymi zawodami"))
    if not delete_ranking(ranking_id):
        return redirect(url_for("admin_panel", tab="rankings", error="Nie udało się usunąć rankingu"))
    return redirect(url_for("admin_panel", tab="rankings", success="Ranking usunięty"))


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
    user_id = session.get("user_id")
    current_pwd = request.form.get("current_password", "")
    new_pwd = request.form.get("new_password", "")
    confirm_pwd = request.form.get("confirm_password", "")
    
    # Validate inputs
    if not current_pwd or not new_pwd or not confirm_pwd:
        return redirect(url_for("admin_panel") + "?tab=users&error=Puste+pola")
    
    if new_pwd != confirm_pwd:
        return redirect(url_for("admin_panel") + "?tab=users&error=Has%C5%82a+nie+zgadzaj%C4%85+si%C4%99")
    
    # Check session
    if not user_id or user_id is None:
        print(f"[ERROR] Zmiana hasła: brak user_id w sesji. username={username}")
        return redirect(url_for("admin_panel") + "?tab=users&error=B%C5%82%C4%85d+sesji")
    
    # Verify current password
    current_hash = hashlib.sha256(current_pwd.encode()).hexdigest()
    verify_result = verify_user(username, current_hash)
    if verify_result is None:
        return redirect(url_for("admin_panel") + "?tab=users&error=Nieprawid%C5%82owe+has%C5%82o")
    
    # Update password
    new_hash = hashlib.sha256(new_pwd.encode()).hexdigest()
    if change_password(user_id, new_hash):
        return redirect(url_for("admin_panel") + "?tab=users&success=Has%C5%82o+zmienione")
    else:
        print(f"[ERROR] Zmiana hasła nie powiodła się. user_id={user_id}")
        return redirect(url_for("admin_panel") + "?tab=users&error=Nie+uda%C5%82o+si%C4%99+zmieni%C4%87+has%C5%82a")


# ---------------------------------------------------------------------------
# Competitors (Admin API)
# ---------------------------------------------------------------------------

@app.route("/admin/api/competitors/<int:match_id>", methods=["GET"])
@admin_required
def admin_get_competitors(match_id):
    """Get all competitors for a match."""
    match_data = get_match(match_id)
    if match_data is None:
        return jsonify({"error": "Nie znaleziono zawodów"}), 404
    
    competitors = match_data.get("competitors", [])
    # Zwróć tylko potrzebne pola
    result = []
    for c in competitors:
        # Jeśli firstname/lastname są puste, rozbij name
        firstname = c.get("firstname", "").strip()
        lastname = c.get("lastname", "").strip()
        
        if not firstname or not lastname:
            # Rozbij name "Lastname Firstname" na części
            name = c.get("name", "").strip()
            if name and not firstname and not lastname:
                parts = name.rsplit(" ", 1)  # Rozbij na ostatnią spację
                if len(parts) == 2:
                    lastname, firstname = parts
                else:
                    lastname = parts[0]
        
        result.append({
            "comp_id": c.get("comp_id"),
            "firstname": firstname,
            "lastname": lastname,
            "name": c.get("name", ""),
            "division": c.get("division", ""),
            "category": c.get("category", ""),
        })
    return jsonify({"competitors": result})


@app.route("/admin/api/competitors/<int:match_id>", methods=["POST"])
@admin_required
def admin_update_competitor(match_id):
    """Update competitor's first name, last name, and optionally category."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Brak danych"}), 400
    
    comp_id = data.get("comp_id")
    firstname = data.get("firstname", "").strip()
    lastname = data.get("lastname", "").strip()
    category = data.get("category", "").strip() or None
    
    if not comp_id or not firstname or not lastname:
        return jsonify({"error": "Brak wymaganych pól: comp_id, firstname, lastname"}), 400
    
    if update_competitor_name(match_id, comp_id, firstname, lastname, category):
        return jsonify({"ok": True, "message": "Zawodnik zaktualizowany"})
    else:
        return jsonify({"error": "Nie znaleziono zawodnika"}), 404


@app.route("/admin/api/competitors/<int:match_id>/<comp_id>", methods=["DELETE"])
@admin_required
def admin_delete_competitor(match_id, comp_id):
    """Delete a competitor from a match."""
    if delete_competitor_from_match(match_id, comp_id):
        return jsonify({"ok": True, "message": "Zawodnik usunięty"})
    else:
        return jsonify({"error": "Nie znaleziono zawodnika"}), 404


# ---------------------------------------------------------------------------
# Division Mappings API
# ---------------------------------------------------------------------------

@app.route("/admin/api/divisions-mapping", methods=["GET"])
@admin_required
def admin_api_get_divisions_mapping():
    """Get all division mappings and available standard divisions."""
    # Pobierz dywizje z bazy
    standard_divs = get_standard_divisions()
    
    mappings = get_all_division_mappings()
    imported_divisions = get_imported_divisions()
    
    result = {
        "standard_divisions": standard_divs,
        "mappings": mappings,
        "imported_divisions": imported_divisions,
    }
    return jsonify(result)


@app.route("/admin/api/divisions-mapping", methods=["POST"])
@admin_required
def admin_api_set_divisions_mapping():
    """Set or update a division mapping."""
    data = request.get_json() or {}
    source_division = data.get("source_division", "").strip()
    mapped_division_id = data.get("mapped_division_id")
    
    if not source_division:
        return jsonify({"error": "source_division jest wymagany"}), 400
    
    # Jeśli mapped_division_id jest pusty, usuń mapowanie
    if mapped_division_id is not None:
        try:
            mapped_division_id = int(mapped_division_id)
        except (TypeError, ValueError):
            return jsonify({"error": "mapped_division_id musi być liczbą"}), 400
    
    if set_division_mapping(source_division, mapped_division_id):
        return jsonify({
            "ok": True,
            "message": f"Mapowanie dla '{source_division}' zaktualizowane"
        })
    else:
        return jsonify({"error": "Nie udało się zapisać mapowania"}), 500


@app.route("/admin/api/standard-divisions", methods=["GET"])
@admin_required
def admin_api_get_standard_divisions():
    """Get all standard divisions."""
    divisions = get_standard_divisions()
    return jsonify({"standard_divisions": divisions})


@app.route("/admin/api/standard-divisions", methods=["POST"])
@admin_required
def admin_api_add_standard_division():
    """Add a new standard division."""
    data = request.get_json() or {}
    division_id = data.get("id")
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    
    if not division_id or not name:
        return jsonify({"error": "id i name są wymagane"}), 400
    
    try:
        division_id = int(division_id)
    except (TypeError, ValueError):
        return jsonify({"error": "id musi być liczbą"}), 400
    
    if add_standard_division(division_id, name, description):
        return jsonify({
            "ok": True,
            "message": f"Dywizja '{name}' dodana",
            "division": {"id": division_id, "name": name, "description": description}
        })
    else:
        return jsonify({"error": "Nie udało się dodać dywizji (ID może już istnieć lub nazwa zajęta)"}), 400


@app.route("/admin/api/standard-divisions/<int:division_id>", methods=["PUT"])
@admin_required
def admin_api_update_standard_division(division_id):
    """Update an existing standard division."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    
    if not name:
        return jsonify({"error": "name jest wymagany"}), 400
    
    if update_standard_division(division_id, name, description):
        return jsonify({
            "ok": True,
            "message": f"Dywizja #{division_id} zaktualizowana"
        })
    else:
        return jsonify({"error": "Nie udało się zaktualizować dywizji"}), 400


@app.route("/admin/api/standard-divisions/<int:division_id>", methods=["DELETE"])
@admin_required
def admin_api_delete_standard_division(division_id):
    """Delete a standard division."""
    if delete_standard_division(division_id):
        return jsonify({
            "ok": True,
            "message": f"Dywizja #{division_id} usunięta"
        })
    else:
        return jsonify({"error": "Nie udało się usunąć dywizji (być może jest używana w mapowaniach)"}), 400


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
