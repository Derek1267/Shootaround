import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
import json, sys, collections
import build_sport as B, knecht
for sport in sys.argv[1:]:
    cfg = B.CFG[sport]; P = cfg["load"]()
    for p in P.values(): p["fame"] = p["fame"] * B.recency(p["to"])
    D = json.load(open(_os.path.join(OUT, f"{sport}.json"), encoding="utf-8"))
    byname = collections.defaultdict(list)
    for pid, p in P.items(): byname[p["name"]].append(pid)
    era = [p for p in P.values() if p["from"] >= cfg["era_from"] and p["stats"] is not None and p["role"]]
    era.sort(key=lambda p: p["fame"], reverse=True)
    dup = {n for n, k in collections.Counter(p["name"] for p in P.values() if p["from"] >= cfg["era_from"] - 10).items() if k > 1}
    era = [p for p in era if p["name"] not in dup]
    era_ids = {p["id"] for p in era[:1600]}
    retired_ids = {p["id"] for p in era if p["to"] <= cfg["retired_to"]} & era_ids
    cats = {c["label"]: c for c in B.catalog(sport, cfg, P, era_ids, retired_ids)}
    pid = lambda n: [i for i in byname[n] if i in era_ids][0]
    errs, seen = [], set()
    for d, pz in enumerate(D["knecht"]):
        ids, chosen = [], []
        for g in pz["groups"]:
            c = cats[g["label"]]; chosen.append(c)
            for n in g["p"]:
                i = pid(n); ids.append(i)
                if i not in c["m"]: errs.append(f"k4 {d}: {n} not in {g['label']}")
            k = frozenset(g["p"]); 
            if k in seen: errs.append(f"k4 {d}: repeated group")
            seen.add(k)
        if len(set(ids)) != 16: errs.append(f"k4 {d}: dup players")
        if knecht.count_solutions(ids, chosen) != 1: errs.append(f"k4 {d}: not unique")
    names = {p["n"] for p in D["players"]}
    for d, j in enumerate(D["journeyman"]):
        p = P[max(byname[j["n"]], key=lambda i: P[i]["fame"])]
        if [s["t"] for s in j["path"]] != [s["t"] for s in p["path"]]: errs.append(f"jm {d}: path {j['n']}")
        if j["n"] not in names: errs.append(f"jm {d}: {j['n']} not guessable")
    for d, s in enumerate(D["statline"]):
        if s["n"] not in names: errs.append(f"sl {d}: {s['n']} not guessable")
    print(f"===== {sport.upper()}: errors {len(errs)}", errs[:10])
    print("  SL roles", collections.Counter(s["r"] for s in D["statline"]), "| groups", len(seen))
    for d in (0, 1, 2):
        pz = D["knecht"][d]; print(f"  Knecht day {d+1} ({D['levels'][pz['lvl']]}):")
        for g in pz["groups"]: print(f"    [{g['tier']}] {g['label']}: {', '.join(g['p'])}")
    print("  JM week:", [(j["n"], D["levels"][j["lvl"]][0]) for j in D["journeyman"][:7]])
    print("  JM sample path:", D["journeyman"][1]["n"], [s["t"] for s in D["journeyman"][1]["path"]], D["journeyman"][1]["h"])
    print("  SL week:", [(s["n"], s["r"], D["levels"][s["lvl"]][0]) for s in D["statline"][:7]])
