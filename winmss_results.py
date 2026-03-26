#!/usr/bin/env python3
"""
WinMSS CAB Results Extractor
Wyciąga dane zawodników, wyniki i klasy ze spakowanego pliku WinMSS .cab

Użycie:
    python3 winmss_results.py [plik.cab]
    python3 winmss_results.py                    # szuka WinMSS.cab w bieżącym katalogu
    python3 winmss_results.py --csv wyniki.csv   # eksport do CSV
    python3 winmss_results.py --overall          # tylko zestawienie ogólne
    python3 winmss_results.py --stages           # z wynikami per-stage
"""

from __future__ import annotations
import re
import sys
import os
import csv
import subprocess
import tempfile
import shutil
import argparse
from collections import defaultdict
from typing import Optional

# ---------------------------------------------------------------------------
# Mapowanie ID dywizji (TypeDivisionId z WinMSS) na nazwy
# Dla zawodów strzeleckich IPSC shotgun (FirearmId=3)
# Dostosuj do zawodów jeśli nazwy się nie zgadzają.
# ---------------------------------------------------------------------------
DIVISION_NAMES = {
    "1":  "Open",
    "2":  "Standard",
    "3":  "Standard S2",
    "4":  "Modified",
    "5":  "Production",
    "6":  "Production Optics",
    "7":  "Prod. Optics Carry",
    "8":  "Classic",
    "9":  "Revolver",
    "10": "Open",            # Shotgun Open
    "11": "Standard",       # Shotgun Standard  ← najliczniejsza
    "12": "Standard Manual",# Shotgun Standard Manual
    "13": "Modified",       # Shotgun Modified
}

# Mapowanie kategorii (TypeNonTeamCategoryId)
CATEGORY_NAMES = {
    "0": "",
    "1": "Lady",
    "2": "Junior",
    "3": "Senior",
    "4": "Super Senior",
    "5": "Super Junior",
}

# ---------------------------------------------------------------------------
# Pomocnicze funkcje parsowania
# ---------------------------------------------------------------------------

def parse_winmss_xml(path: str) -> list[dict]:
    """
    Parsuje plik XML w formacie rowset (ADO/WinMSS) i zwraca listę słowników.
    Pliki używają przestrzeni nazw z:row więc standardowy XML parser daje błędy.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    rows = []
    for m in re.finditer(r"<z:row\s+([^/]+?)/>", content, re.DOTALL):
        attr_str = m.group(1)
        attrs = dict(re.findall(r"(\w+)='([^']*)'", attr_str))
        rows.append(attrs)
    return rows


def extract_cab(cab_path: str, out_dir: str) -> None:
    """Rozpakowuje plik .cab przy użyciu cabextract lub expand (Windows)."""
    cabextract = shutil.which("cabextract")
    if cabextract:
        result = subprocess.run(
            [cabextract, "-d", out_dir, cab_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"cabextract błąd:\n{result.stderr}")
        return

    # macOS/Windows: próba z expand
    expand = shutil.which("expand")
    if expand:
        result = subprocess.run(
            [expand, cab_path, "-F:*", out_dir],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return

    raise RuntimeError(
        "Nie znaleziono narzędzia do rozpakowywania .cab.\n"
        "Zainstaluj cabextract: brew install cabextract"
    )


# ---------------------------------------------------------------------------
# Wczytywanie danych
# ---------------------------------------------------------------------------

def load_data(cab_path: str) -> dict:
    """Wczytuje dane z pliku .cab i zwraca słownik tabel."""
    tmpdir = tempfile.mkdtemp(prefix="winmss_")
    try:
        extract_cab(cab_path, tmpdir)

        # Mapowanie nazw plików (case-insensitive) → ścieżki
        file_map = {f.upper(): os.path.join(tmpdir, f) for f in os.listdir(tmpdir)}

        def load(name):
            path = file_map.get(name.upper())
            if not path or not os.path.exists(path):
                return []
            return parse_winmss_xml(path)

        data = {
            "match":    load("THEMATCH.XML"),
            "members":  load("MEMBER.XML"),
            "enrolled": load("ENROLLED.XML"),
            "stages":   load("STAGE.XML"),
            "scores":   load("SCORE.XML"),
            "clubs":    load("CLUB.XML"),
            "squads":   load("SQUAD.XML"),
        }
        return data
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Obliczenia wyników
# ---------------------------------------------------------------------------

def build_results(data: dict) -> tuple[dict, list, list]:
    """
    Łączy wszystkie dane i buduje pełne zestawienie wyników.

    Zwraca: (match_info, stages_list, competitors_list)
    """
    match_info = data["match"][0] if data["match"] else {}

    # Indeksowanie zawodników (members)
    members = {r["MemberId"]: r for r in data["members"]}

    # Indeksowanie etapów (stages)
    stages = sorted(data["stages"], key=lambda s: int(s.get("StageId", 0)))

    # Indeksowanie danych rejestracji: MemberId → enrolled record
    enrolled_by_member = {r["MemberId"]: r for r in data["enrolled"]}

    # Indeksowanie wyników: (MemberId, StageId) → score record
    score_idx: dict[tuple, dict] = {}
    for s in data["scores"]:
        key = (s.get("MemberId", ""), s.get("StageId", ""))
        score_idx[key] = s

    # Zbierz wyniki per zawodnik
    competitors = []
    for enr in data["enrolled"]:
        member_id = enr.get("MemberId", "")
        member    = members.get(member_id, {})
        div_id    = enr.get("DivId", "?")
        cat_id    = enr.get("CatId", "0")
        is_disq   = enr.get("IsDisq", "False").lower() == "true"

        division = DIVISION_NAMES.get(div_id, f"Div{div_id}")
        category = CATEGORY_NAMES.get(cat_id, f"Cat{cat_id}")

        # Wyniki per etap
        stage_scores = []
        total_points = 0
        total_time   = 0.0
        all_stages_complete = True

        for stg in stages:
            stage_id = stg.get("StageId", "")
            sc = score_idx.get((member_id, stage_id))
            if sc is None:
                stage_scores.append(None)
                all_stages_complete = False
                continue

            a   = int(sc.get("ScoreA",   0))
            b   = int(sc.get("ScoreB",   0))
            c   = int(sc.get("ScoreC",   0))
            d_  = int(sc.get("ScoreD",   0))
            m   = int(sc.get("Misses",   0))
            pe  = int(sc.get("ProcError",0))
            pen = int(sc.get("Penalties",0))
            t   = float(sc.get("ShootTime", 0) or 0)
            pts = int(sc.get("FinalScore", 0) or 0)
            hf  = pts / t if t > 0 else 0.0
            stg_disq = sc.get("IsDisq", "False").lower() == "true"

            stage_scores.append({
                "stage_id": stage_id,
                "A": a, "B": b, "C": c, "D": d_, "M": m, "PE": pe,
                "Pen": pen,
                "time": t,
                "hf": hf,
                "pts": pts,
                "disq": stg_disq,
            })
            if not stg_disq:
                total_points += pts
                total_time   += t

        # Łączny hit-factor
        overall_hf = total_points / total_time if total_time > 0 else 0.0

        competitors.append({
            "member_id": member_id,
            "comp_id":   int(enr.get("CompId", 0)),
            "lastname":  member.get("Lastname", ""),
            "firstname": member.get("Firstname", ""),
            "female":    member.get("Female", "false").lower() == "true",
            "region":    member.get("RegionId", ""),
            "div_id":    div_id,
            "division":  division,
            "cat_id":    cat_id,
            "category":  category,
            "squad":     enr.get("SquadId", ""),
            "is_disq":   is_disq,
            "stage_scores": stage_scores,
            "total_points": total_points,
            "total_time":   total_time,
            "overall_hf":  overall_hf,
        })

    # --- Przelicz punkty IPSC: dwa rodzaje ---
    # 1. Per-division: pkt = (HF / best HF w DYWIZJI) × max pkt
    # 2. Overall (globalne): pkt = (HF / best HF GLOBALNIE) × max pkt
    n_stages = len(stages)
    
    # Najlepszy HF globalnie na każdym torze
    best_hf_per_stage_global = [0.0] * n_stages
    for c in competitors:
        for i in range(n_stages):
            if i < len(c["stage_scores"]):
                sc = c["stage_scores"][i]
                if sc and not sc["disq"] and not c["is_disq"] and sc["hf"] > best_hf_per_stage_global[i]:
                    best_hf_per_stage_global[i] = sc["hf"]
    
    # Najlepszy HF per-dywizję na każdym torze
    best_hf_per_stage_div = defaultdict(lambda: [0.0] * n_stages)
    for div in set(c["division"] for c in competitors):
        div_competitors = [c for c in competitors if c["division"] == div]
        for i in range(n_stages):
            for c in div_competitors:
                if i < len(c["stage_scores"]):
                    sc = c["stage_scores"][i]
                    if sc and not sc["disq"] and not c["is_disq"] and sc["hf"] > best_hf_per_stage_div[div][i]:
                        best_hf_per_stage_div[div][i] = sc["hf"]
    
    # Wylicz obie wersje punktów dla każdego zawodnika
    for c in competitors:
        total_pts_overall = 0.0
        total_pts_in_division = 0.0
        div = c["division"]
        for i in range(n_stages):
            if i < len(c["stage_scores"]):
                sc = c["stage_scores"][i]
                if sc and not sc["disq"]:
                    max_pts = int(stages[i].get("MaxPoints", 0))
                    
                    # Punkty Overall (globalne)
                    best_global_hf = best_hf_per_stage_global[i]
                    if best_global_hf > 0:
                        stage_pts_overall = (sc["hf"] / best_global_hf) * max_pts
                    else:
                        stage_pts_overall = 0.0
                    total_pts_overall += stage_pts_overall
                    
                    # Punkty w dywizji
                    best_div_hf = best_hf_per_stage_div[div][i]
                    if best_div_hf > 0:
                        stage_pts_in_div = (sc["hf"] / best_div_hf) * max_pts
                    else:
                        stage_pts_in_div = 0.0
                    total_pts_in_division += stage_pts_in_div
                    
                    # Zdominuj: dla wyświetlenia zwracamy per-division (poprawne dla IPSC)
                    sc["pts"] = round(stage_pts_in_div, 4)
        
        c["total_points"] = round(total_pts_overall, 4)  # Globalne - używane do rankingu
        c["total_points_overall"] = round(total_pts_overall, 4)  # Globalne dla Overall tab
        c["total_points_in_division"] = round(total_pts_in_division, 4)  # Per-division dla Dywizje tab

    return match_info, stages, competitors


def rank_competitors(competitors: list, key: str = "overall") -> list:
    """
    Sortuje zawodników i przypisuje miejsca.
    Dyskwalifikowani zawsze na końcu.
    """
    active  = [c for c in competitors if not c["is_disq"]]
    disq    = [c for c in competitors if c["is_disq"]]

    active.sort(key=lambda c: c["total_points"], reverse=True)
    disq.sort(  key=lambda c: c["lastname"])

    result = []
    prev_pts, prev_rank = None, 0
    for i, c in enumerate(active, 1):
        if c["total_points"] == prev_pts:
            rank = prev_rank
        else:
            rank = i
            prev_rank = i
        prev_pts = c["total_points"]
        result.append({**c, "rank": rank})

    for c in disq:
        result.append({**c, "rank": "DSQ"})

    return result


def add_percent_of_best(ranked: list) -> list:
    """Dodaje kolumnę % do lidera."""
    active = [c for c in ranked if not c["is_disq"]]
    if not active:
        return ranked
    best_pts = max(c["total_points"] for c in active)
    result = []
    for c in ranked:
        if best_pts > 0 and not c["is_disq"]:
            pct = c["total_points"] / best_pts * 100
        else:
            pct = 0.0
        result.append({**c, "pct": pct})
    return result


# ---------------------------------------------------------------------------
# Formatowanie tabel
# ---------------------------------------------------------------------------

def fmt_name(comp: dict) -> str:
    return f"{comp['lastname']} {comp['firstname']}"


def fmt_hf(hf: float) -> str:
    return f"{hf:.4f}" if hf else "-"


def fmt_time(t: float) -> str:
    return f"{t:.2f}s" if t else "-"


def fmt_rank(r) -> str:
    return str(r)


def print_table(headers: list, rows: list, col_widths: Optional[list] = None) -> None:
    if not rows:
        print("  (brak danych)")
        return

    if col_widths is None:
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
                      for i, h in enumerate(headers)]

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in col_widths) + " |"

    print(sep)
    print(fmt.format(*[str(h) for h in headers]))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    print(sep)


# ---------------------------------------------------------------------------
# Widoki tabel
# ---------------------------------------------------------------------------

def overall_table(ranked: list, stages: list, show_stages: bool = False) -> None:
    """Drukuje tabelę zestawienia ogólnego."""
    n_stages = len(stages)

    if show_stages:
        stage_headers = []
        for stg in stages:
            sn = stg.get("StageName", f"S{stg['StageId']}")
            stage_headers += [f"{sn}\nPkt", f"{sn}\nHF"]
        headers = ["#", "Nr", "Nazwisko Imię", "Dywizja", "Kat.",
                   *[h.replace("\n", " ") for h in stage_headers],
                   "Pkt łącz.", "Czas łącz.", "HF Overall", "% lidera"]
    else:
        headers = ["#", "Nr", "Nazwisko Imię", "Dywizja", "Kat.",
                   "Pkt łącz.", "Czas łącz.", "HF Overall", "% lidera"]

    rows = []
    for c in ranked:
        if show_stages:
            stage_cells = []
            for i, stg in enumerate(stages):
                sc = c["stage_scores"][i] if i < len(c["stage_scores"]) else None
                if sc is None:
                    stage_cells += ["-", "-"]
                elif sc["disq"]:
                    stage_cells += ["DSQ", "DSQ"]
                else:
                    stage_cells += [sc["pts"], f"{sc['hf']:.4f}"]
        else:
            stage_cells = []

        pct_str = f"{c.get('pct', 0):.2f}%" if not c["is_disq"] else "DSQ"

        row = [
            fmt_rank(c["rank"]),
            c["comp_id"],
            fmt_name(c),
            c["division"],
            c["category"] or "-",
            *stage_cells,
            c["total_points"] if not c["is_disq"] else "DSQ",
            fmt_time(c["total_time"]),
            fmt_hf(c["overall_hf"]),
            pct_str,
        ]
        rows.append(row)

    print_table(headers, rows)


def division_tables(ranked: list, stages: list, show_stages: bool = False) -> None:
    """Drukuje tabele wyników per dywizja."""
    # Grupowanie po dywizji
    by_div: dict[str, list] = defaultdict(list)
    for c in ranked:
        by_div[c["division"]].append(c)

    for div_name in sorted(by_div):
        competitors = by_div[div_name]
        # Przelicz miejsca w dywizji
        active = [c for c in competitors if not c["is_disq"]]
        disq   = [c for c in competitors if c["is_disq"]]
        active.sort(key=lambda c: c["overall_hf"], reverse=True)

        # Znajdź najlepszy HF w dywizji
        best_div_hf = active[0]["overall_hf"] if active else 0

        print(f"\n{'='*60}")
        print(f"  Dywizja: {div_name}  ({len(competitors)} zawodników)")
        print(f"{'='*60}")

        headers = ["# Dyw.", "# Og.", "Nazwisko Imię", "Kat.",
                   "Pkt łącz.", "Czas łącz.", "HF Overall", "% w dyw."]

        rows = []
        for div_rank, c in enumerate(active, 1):
            pct_div = c["overall_hf"] / best_div_hf * 100 if best_div_hf > 0 else 0
            rows.append([
                div_rank,
                c["rank"],
                fmt_name(c),
                c["category"] or "-",
                c["total_points"],
                fmt_time(c["total_time"]),
                fmt_hf(c["overall_hf"]),
                f"{pct_div:.2f}%",
            ])
        for c in disq:
            rows.append(["DSQ", "DSQ", fmt_name(c), c["category"] or "-",
                         "DSQ", "-", "-", "-"])

        print_table(headers, rows)


def stage_details_table(ranked: list, stages: list) -> None:
    """Drukuje szczegóły dla każdego etapu (najlepsze HF w etapie = 100%)."""
    for i, stg in enumerate(stages):
        stage_id   = stg.get("StageId", str(i + 1))
        stage_name = stg.get("StageName", f"Stage {stage_id}")
        max_pts    = stg.get("MaxPoints", "?")

        # Zbierz dane dla tego etapu
        stage_data = []
        for c in ranked:
            if i < len(c["stage_scores"]) and c["stage_scores"][i] is not None:
                sc = c["stage_scores"][i]
                stage_data.append((c, sc))

        # Znajdź najlepszy HF dla etapu (do %)
        valid_hfs = [sc["hf"] for _, sc in stage_data if not sc["disq"] and sc["hf"] > 0]
        best_stage_hf = max(valid_hfs) if valid_hfs else 0

        print(f"\n{'='*70}")
        print(f"  Tor {stage_id}: {stage_name}   (maks. pkt: {max_pts})")
        print(f"{'='*70}")

        headers = ["# Og.", "Nazwisko Imię", "Dyw.", "Kat.",
                   "A", "B", "C", "D", "M", "PE",
                   "Pkt", "Czas", "HF", "% toru"]

        rows = []
        for c, sc in sorted(stage_data, key=lambda x: x[1]["hf"], reverse=True):
            if sc["disq"]:
                rows.append([c["rank"], fmt_name(c), c["division"], c["category"] or "-",
                              *(["-"] * 6), "DSQ", "-", "-", "-"])
            else:
                pct = sc["hf"] / best_stage_hf * 100 if best_stage_hf > 0 else 0
                rows.append([
                    c["rank"],
                    fmt_name(c),
                    c["division"],
                    c["category"] or "-",
                    sc["A"], sc["B"], sc["C"], sc["D"], sc["M"], sc["PE"],
                    sc["pts"],
                    fmt_time(sc["time"]),
                    fmt_hf(sc["hf"]),
                    f"{pct:.2f}%",
                ])

        print_table(headers, rows)


# ---------------------------------------------------------------------------
# Eksport CSV
# ---------------------------------------------------------------------------

def export_csv(ranked: list, stages: list, out_path: str) -> None:
    """Eksportuje wyniki do pliku CSV."""
    stage_names = [stg.get("StageName", f"S{stg['StageId']}") for stg in stages]

    fieldnames = [
        "Miejsce", "Nr_zawodnika", "Nazwisko", "Imie", "Dywizja", "Kategoria",
        "Plec", "Region", "Eskwadra",
    ]
    for sn in stage_names:
        fieldnames += [f"{sn}_Pkt", f"{sn}_Czas", f"{sn}_HF",
                       f"{sn}_A", f"{sn}_B", f"{sn}_C", f"{sn}_D",
                       f"{sn}_M", f"{sn}_PE"]
    fieldnames += ["Pkt_lacznie", "Czas_lacznie", "HF_overall", "Procent_lidera"]

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for c in ranked:
            row: dict = {
                "Miejsce":       fmt_rank(c["rank"]),
                "Nr_zawodnika":  c["comp_id"],
                "Nazwisko":      c["lastname"],
                "Imie":          c["firstname"],
                "Dywizja":       c["division"],
                "Kategoria":     c["category"],
                "Plec":          "K" if c["female"] else "M",
                "Region":        c["region"],
                "Eskwadra":      c["squad"],
                "Pkt_lacznie":   c["total_points"] if not c["is_disq"] else "DSQ",
                "Czas_lacznie":  f"{c['total_time']:.2f}" if c["total_time"] else "0",
                "HF_overall":    f"{c['overall_hf']:.4f}" if not c["is_disq"] else "DSQ",
                "Procent_lidera": f"{c.get('pct', 0):.2f}" if not c["is_disq"] else "DSQ",
            }

            for i, stg in enumerate(stages):
                sn = stage_names[i]
                sc = c["stage_scores"][i] if i < len(c["stage_scores"]) else None
                if sc is None:
                    row[f"{sn}_Pkt"]  = ""
                    row[f"{sn}_Czas"] = ""
                    row[f"{sn}_HF"]   = ""
                    for k in ("A", "B", "C", "D", "M", "PE"):
                        row[f"{sn}_{k}"] = ""
                elif sc["disq"]:
                    row[f"{sn}_Pkt"]  = "DSQ"
                    row[f"{sn}_Czas"] = ""
                    row[f"{sn}_HF"]   = "DSQ"
                    for k in ("A", "B", "C", "D", "M", "PE"):
                        row[f"{sn}_{k}"] = ""
                else:
                    row[f"{sn}_Pkt"]  = sc["pts"]
                    row[f"{sn}_Czas"] = f"{sc['time']:.2f}"
                    row[f"{sn}_HF"]   = f"{sc['hf']:.4f}"
                    row[f"{sn}_A"]    = sc["A"]
                    row[f"{sn}_B"]    = sc["B"]
                    row[f"{sn}_C"]    = sc["C"]
                    row[f"{sn}_D"]    = sc["D"]
                    row[f"{sn}_M"]    = sc["M"]
                    row[f"{sn}_PE"]   = sc["PE"]

            writer.writerow(row)

    print(f"\nEksport do CSV: {out_path}")


# ---------------------------------------------------------------------------
# Główny program
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Wyciąga wyniki z pliku WinMSS .cab"
    )
    parser.add_argument(
        "cabfile", nargs="?", default="WinMSS.cab",
        help="Ścieżka do pliku .cab (domyślnie: WinMSS.cab)"
    )
    parser.add_argument(
        "--csv", metavar="PLIK.csv",
        help="Eksportuj wyniki do pliku CSV"
    )
    parser.add_argument(
        "--stages", action="store_true",
        help="Pokaż szczegółowe wyniki per tor"
    )
    parser.add_argument(
        "--overall", action="store_true",
        help="Pokaż tylko zestawienie ogólne (bez podziału na dywizje)"
    )
    parser.add_argument(
        "--stage-detail", action="store_true",
        help="Pokaż ranking per tor (A/B/C/D/M/PE)"
    )
    args = parser.parse_args()

    cab_path = args.cabfile
    if not os.path.exists(cab_path):
        print(f"Błąd: nie znaleziono pliku '{cab_path}'", file=sys.stderr)
        sys.exit(1)

    print(f"Wczytywanie: {cab_path} ...")
    data = load_data(cab_path)

    match_info, stages, competitors = build_results(data)
    ranked = rank_competitors(competitors)
    ranked = add_percent_of_best(ranked)

    # --- Nagłówek zawodów ---
    print()
    print("=" * 70)
    match_name = match_info.get("MatchName", "(brak nazwy)")
    match_date = match_info.get("MatchDt", "")[:10]
    match_lvl  = int(match_info.get("MatchLevel", 0)) + 1
    n_stages   = len(stages)
    n_comps    = len(competitors)
    print(f"  {match_name}")
    print(f"  Data: {match_date}   Poziom: L{match_lvl}   "
          f"Torów: {n_stages}   Zawodników: {n_comps}")
    print("=" * 70)

    # --- Zestawienie ogólne ---
    print("\n>>> ZESTAWIENIE OGÓLNE\n")
    overall_table(ranked, stages, show_stages=args.stages)

    # --- Tabele per dywizja ---
    if not args.overall:
        print("\n>>> ZESTAWIENIA PER DYWIZJA")
        division_tables(ranked, stages, show_stages=args.stages)

    # --- Szczegóły torów ---
    if args.stage_detail:
        print("\n>>> SZCZEGÓŁY TORÓW")
        stage_details_table(ranked, stages)

    # --- Eksport CSV ---
    if args.csv:
        export_csv(ranked, stages, args.csv)

    print("\nGotowe.")


if __name__ == "__main__":
    main()
