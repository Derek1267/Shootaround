import os as _e
SUFFIX = "" if _e.environ.get("SHOOTAROUND_ERA", "all") == "all" else "-" + _e.environ["SHOOTAROUND_ERA"]
import json, collections, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "..")
import common, hl_build as H
errs = []
for sport in ["nba", "nfl", "nhl", "mlb"] + ([] if SUFFIX else ["soccer"]):   # soccer has one set (no Modern file)
    D = json.load(open(os.path.join(OUT, f"{sport}{SUFFIX}.json"))); HL = json.load(open(os.path.join(OUT, f"hl-{sport}{SUFFIX}.json")))
    S = {p["n"]: p for p in D["players"]}
    ncar = nsea = 0
    for d, day in enumerate(HL["days"]):
        if len(day) != 5: errs.append(f"{sport} {d}: {len(day)} questions")
        for q in day:
            if H.fmt(q["f"], q["a"]["v"]) == H.fmt(q["f"], q["b"]["v"]): errs.append(f"{sport} {d}: tie")
            if q["a"]["n"] == q["b"]["n"] and q["a"]["c"] == q["b"]["c"]: errs.append(f"{sport} {d}: same side")
            if q["a"]["c"] in ("Career", "Since 2012–13"):
                ncar += 1
                k = next(c["k"] for r in H.CAREER[sport].values() for lv in r for c in lv if c["l"] == q["s"])
                for side in "ab":
                    if abs(S[q[side]["n"]]["s"][k] - q[side]["v"]) > 1e-3: errs.append(f"{sport} {d}: career value mismatch {q[side]['n']} {k}")
                if (S[q["a"]["n"]].get("r") or "all") != (S[q["b"]["n"]].get("r") or "all"): errs.append(f"{sport} {d}: role mismatch")
            else:
                nsea += 1
    print(f"{sport}: career Qs {ncar}, season Qs {nsea}")
# NBA season PPG cross-check against the separate per-game file
pg = {}
for r in common.rows("Player Per Game.csv"):
    if r["lg"] == "NBA":
        key = (r["player"], int(r["season"]))
        if r["team"] in common.MULTI or key not in pg: pg[key] = r
HL = json.load(open(os.path.join(OUT, f"hl-nba{SUFFIX}.json"))); checked = bad = 0
for day in HL["days"]:
    q = day[4]
    if q["s"] != "Points per game": continue
    for side in "ab":
        y = int(q[side]["c"][:4]) + 1
        r = pg.get((q[side]["n"], y))
        if r:
            checked += 1
            if abs(float(r["pts_per_game"]) - q[side]["v"]) > 0.06: bad += 1; errs.append(f"nba season ppg {q[side]['n']} {y}: {r['pts_per_game']} vs {q[side]['v']}")
print(f"NBA season PPG cross-checked: {checked}, mismatches {bad}")
print("ERRORS:", len(errs), errs[:8])
for sport in ["nba", "mlb"]:
    print(f"\n{sport.upper()} day 1:")
    for i, q in enumerate(json.load(open(os.path.join(OUT, f"hl-{sport}{SUFFIX}.json")))["days"][0]):
        print(f"  Q{i+1} {q['s']}: {q['a']['n']} ({q['a']['c']}) = {H.fmt(q['f'], q['a']['v'])}  vs  {q['b']['n']} ({q['b']['c']}) = {H.fmt(q['f'], q['b']['v'])}")
