import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
"""Independent check of nba.json against the raw data."""
import os as _e
SUFFIX = "" if _e.environ.get("SHOOTAROUND_ERA", "all") == "all" else "-" + _e.environ["SHOOTAROUND_ERA"]
import json, collections
from common import load, per_game
from knecht import build_catalog, count_solutions

P = load()
if SUFFIX == "-modern":                       # mirror build.py: the modern catalog is built from modern players only
    P = {k: v for k, v in P.items() if (v["from"] + v["to"]) / 2 >= 2010}
cats = {c["label"]: c for c in build_catalog(P)}
D = json.load(open(_os.path.join(OUT, f"nba{SUFFIX}.json"), encoding="utf-8"))
byname = collections.defaultdict(list)
for pid, p in P.items():
    if p["from"] >= 1980: byname[p["name"]].append(pid)
def pid_of(n, label=None):
    ids = byname[n]
    if label and len(ids) > 1:
        ids = [i for i in ids if i in cats[label]["m"]] or ids
    return max(ids, key=lambda i: per_game(P[i])["g"])

errs = []
labels = collections.Counter(); seen_groups = set(); dup_groups = 0; levels = collections.Counter()
for d, puz in enumerate(D["knecht"] + ([D["practice"]["knecht"]] if "practice" in D else [])):   # practice puzzle checked too
    names = [n for g in puz["groups"] for n in g["p"]]
    if len(set(names)) != 16: errs.append(f"k4 day {d}: duplicate names")
    levels[puz["lvl"]] += 1
    pids, chosen = [], []
    for g in puz["groups"]:
        c = cats[g["label"]]; chosen.append(c); labels[g["label"]] += 1
        for n in g["p"]:
            pid = pid_of(n, g["label"]); pids.append(pid)
            if pid not in c["m"]: errs.append(f"k4 day {d}: {n} is not in '{g['label']}'")
        key = frozenset(g["p"])
        if key in seen_groups: dup_groups += 1
        seen_groups.add(key)
    if sorted(g["tier"] for g in puz["groups"]) != [0, 1, 2, 3]: errs.append(f"k4 day {d}: tiers")
    if count_solutions(pids, chosen) != 1: errs.append(f"k4 day {d}: not unique")
    fs = set(pids)
    if any(len(c["m"] & fs) != 4 for c in chosen): errs.append(f"k4 day {d}: a link fits more than its four")
    if any(len(c["m"] & fs) >= 4 for c in cats.values() if c not in chosen): errs.append(f"k4 day {d}: another link fits four")

for d, j in enumerate(D["journeyman"] + ([D["practice"]["journeyman"]] if "practice" in D else [])):   # practice puzzle checked too
    p = P[pid_of(j["n"])]
    if [s["t"] for s in j["path"]] != [s["full"].split()[-1] if not s["full"].endswith("Trail Blazers") else "Trail Blazers" for s in p["path"]]:
        errs.append(f"jm day {d}: path mismatch for {j['n']}")
names = {p["n"] for p in D["players"]}
for d, s in enumerate(D["statline"] + ([D["practice"]["statline"]] if "practice" in D else [])):   # practice puzzle checked too
    if s["n"] not in names: errs.append(f"sl day {d}: {s['n']} missing from player pool")

print("errors:", len(errs)); print("\n".join(errs[:20]))
print("k4 puzzles", len(D["knecht"]), "groups", 4 * len(D["knecht"]), "distinct groups", len(seen_groups), "repeat groups", dup_groups)
print("levels", dict(levels), "distinct labels", len(labels))
print("most used labels", labels.most_common(8))
print("types", collections.Counter(g["type"] for p in D["knecht"] for g in p["groups"]))
for d in (0, 1, 6):
    print(f"\n--- Knecht day {d + 1} ({D['levels'][D['knecht'][d]['lvl']]})")
    for g in D["knecht"][d]["groups"]:
        print(f"  [{g['tier']}] {g['label']}: {', '.join(g['p'])}")
print("\nJourneyman first week:", [(j["n"], D["levels"][j["lvl"]]) for j in D["journeyman"][:7]])
print("Stat Line first week:", [(s["n"], D["levels"][s["lvl"]]) for s in D["statline"][:7]])
