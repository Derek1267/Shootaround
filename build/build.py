import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
ERA = _os.environ.get("SHOOTAROUND_ERA", "all")   # "modern": only players whose careers centre on 2010 or later (career midpoint >= 2010) -> nba-modern.json
MODERN_FROM = 2010
FILE = "nba.json" if ERA == "all" else f"nba-{ERA}.json"
"""Build nba.json for Shootaround: guess pool, 365 Journeyman days, 365 Stat Line days, 365 Knecht 4 days."""
import json, random, datetime
from common import load, per_game, nickname, city
from knecht import generate as gen_knecht
import sys as _sys0, sys
if _os.path.exists(_os.path.join(OUT, FILE)) and "--force" not in _sys0.argv and "--practice" not in _sys0.argv:
    _sys0.exit(f"{FILE} already exists. Published puzzles are frozen: rebuilding would change every player's puzzles.\n"
               "Only use --force before launch, or to start a brand-new schedule on purpose.")

P = load()
P_ALL = P                                         # names shared by two players anywhere in history stay out, in every era
if ERA == "modern":
    P = {k: v for k, v in P.items() if (v["from"] + v["to"]) / 2 >= MODERN_FROM}
EPOCH = datetime.date(2026, 11, 22)
DAYS = 365


def recency(to):
    """Favour players today's fans know: full weight for recent careers, less for older ones."""
    return 1.0 if to >= 2016 else .85 if to >= 2010 else .7 if to >= 2004 else .55 if to >= 1998 else .42 if to >= 1992 else .3

def fame(p):
    pg = per_game(p)
    return (p["allstar"]*4 + p["allnba"]*2 + pg["ppg"] + pg["g"]/100 + len(p["awards"])*4 + p["hof"]*6 + p["rings"]) * recency(p["to"])

POS = {"PG":"Point guard","SG":"Shooting guard","SF":"Small forward","PF":"Power forward","G":"Guard","F":"Forward","C":"Center"}
def pos_label(s):
    parts = [POS.get(x, x) for x in s.split("-") if x and x != "NA"]
    if not parts: return "—"
    out = parts[0]
    for x in parts[1:]: out += " / " + x.lower()
    return out
def season(y): return f"{y-1}–{str(y)[2:]}"
def span(p):
    return f"{season(p['from'])} to now" if p["to"] >= 2026 else f"{season(p['from'])} to {season(p['to'])}"
def draft_label(p):
    d = p["draft"]
    if not d:
        return "Undrafted" if p["from"] >= 1990 else "Not listed"
    return f"{d['year']} · Pick {d['pick']} ({nickname(d['team'])})"
def college_label(p):
    return " · ".join(p["colleges"]) if p["colleges"] else "No US college"

# Difficulty by weekday, like the NYT crossword: Mon easiest -> Sun hardest
WEEKDAY_LEVEL = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2}  # 0=easy,1=medium,2=hard
LEVEL_NAME = ["Easy", "Medium", "Hard"]
day_levels = [WEEKDAY_LEVEL[(EPOCH + datetime.timedelta(days=i)).weekday()] for i in range(DAYS)]

def schedule(pool, rng):
    """pool sorted by fame (most famous first). Split into easy/medium/hard by the
    number of days each level needs, then deal them out to matching weekdays."""
    need = [day_levels.count(l) for l in range(3)]
    buckets, i = [], 0
    for n in need:
        b = pool[i:i+n]; rng.shuffle(b); buckets.append(b); i += n
    return [buckets[l].pop() for l in day_levels]

rng = random.Random(20261122)

# ---------- guess pool (everyone guessable in Journeyman and Stat Line)
MIN_POOL_G = 150 if ERA == "modern" else 250   # the modern pool is smaller, so let shorter careers in
pool_players = [p for p in P.values() if p["from"] >= 1980 and per_game(p)["g"] >= MIN_POOL_G]
pool_players.sort(key=fame, reverse=True)
import collections
DUP = {n for n, k in collections.Counter(p["name"] for p in P_ALL.values() if p["from"] >= 1980).items() if k > 1}
pool_players = [p for p in pool_players if p["name"] not in DUP]
players_out = []
for p in pool_players:
    pg = per_game(p)
    players_out.append({
        "n": p["name"], "a": p["to"] >= 2026,
        "t": list(dict.fromkeys(nickname(s["full"]) for s in p["path"])),
        "s": {k: pg[k] for k in ["g","ppg","rpg","apg","fg","x3","ft","spg","bpg","tov"]},
    })

# ---------- Stat Line answers (retired, 300+ games)
sl_pool = [p for p in pool_players if per_game(p)["g"] >= 300 and p["from"] >= 1980]
sl_days = schedule(sl_pool[:DAYS], rng)
sl_out = [{
    "n": p["name"], "lvl": day_levels[i],
    "h": {"years": span(p), "pos": pos_label(p["pos"]),
          "as": str(p["allstar"]), "rings": str(p["rings"]), "draft": draft_label(p), "college": college_label(p)}
} for i, p in enumerate(sl_days)]

# ---------- Journeyman answers (retired, 3+ stints, unambiguous trade order)
jm_pool = [p for p in (pool_players if ERA == "modern" else sl_pool) if len(p["path"]) >= 3 and not p["ambiguous"]]
jm_days = schedule(jm_pool[:DAYS], rng)
jm_out = [{
    "n": p["name"], "lvl": day_levels[i],
    "path": [{"t": nickname(s["full"]), "c": city(s["full"]), "y": season(s["from"]) if s["from"] == s["to"] else f"{season(s['from'])} to {season(s['to'])}"} for s in p["path"]],
    "h": {"seasons": span(p), "pos": pos_label(p["pos"]),
          "draft": draft_label(p), "college": college_label(p),
          "honors": f'{p["allstar"]} All-Star · {p["rings"]} title{"" if p["rings"] == 1 else "s"}'}
} for i, p in enumerate(jm_days)]

# ---------- Practice round (see build_sport.practice): python3 build.py --practice
if "--practice" in sys.argv:
    path = _os.path.join(OUT, FILE)
    Dj = json.load(open(path, encoding="utf-8"))
    n_easy, n_med = day_levels.count(0), day_levels.count(1)
    used = {e["n"] for e in Dj["journeyman"]} | {e["n"] for e in Dj["statline"]}
    jm_entry = lambda p, lvl: {"n": p["name"], "lvl": lvl,
        "path": [{"t": nickname(s["full"]), "c": city(s["full"]), "y": season(s["from"]) if s["from"] == s["to"] else f"{season(s['from'])} to {season(s['to'])}"} for s in p["path"]],
        "h": {"seasons": span(p), "pos": pos_label(p["pos"]), "draft": draft_label(p), "college": college_label(p),
              "honors": f'{p["allstar"]} All-Star · {p["rings"]} title{"" if p["rings"] == 1 else "s"}'}}
    sl_entry = lambda p, lvl: {"n": p["name"], "lvl": lvl, "h": {"years": span(p), "pos": pos_label(p["pos"]),
        "as": str(p["allstar"]), "rings": str(p["rings"]), "draft": draft_label(p), "college": college_label(p)}}
    prac = {}
    for kind, ranked, entry in (("journeyman", jm_pool, jm_entry), ("statline", sl_pool, sl_entry)):
        listing = Dj[kind]; pos = {e["n"]: i for i, e in enumerate(listing)}
        band = [p for p in ranked[n_easy:n_easy + n_med] if pos.get(p["name"], -1) >= 60]
        pick = band[len(band) // 2]; idx = pos[pick["name"]]
        repl = next(p for p in ranked if p["name"] not in used)
        listing[idx] = entry(repl, listing[idx]["lvl"]); used.add(repl["name"])
        prac[kind] = entry(pick, 1)
        print(f"  {kind}: practice {pick['name']} (was day {idx + 1}); day {idx + 1} is now {repl['name']}")
    daily_groups = {frozenset(g["p"]) for z in Dj["knecht"] for g in z["groups"]}
    for seed in range(9000, 9100):
        k4p, _ = gen_knecht(P, fame, [1], 1, sizes=(240, 400, 580), seed=seed)
        if not any(frozenset(g["p"]) in daily_groups for g in k4p[0]["groups"]): break
    prac["knecht"] = k4p[0]; print("  links:", [g["label"] for g in k4p[0]["groups"]])
    Dj["practice"] = prac
    json.dump(Dj, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    sys.exit(0)

# ---------- Knecht 4
k4_out, k4_report = gen_knecht(P, fame, day_levels, DAYS, sizes=(240, 400, 580))

data = {
    "sport": "nba", "era": ERA, "built": datetime.date.today().isoformat(), "epoch": EPOCH.isoformat(),
    "levels": LEVEL_NAME, "players": players_out, "journeyman": jm_out, "statline": sl_out, "knecht": k4_out,
}
import sys as _sys
if _os.path.exists(_os.path.join(OUT, FILE)) and "--force" not in _sys.argv:
    _sys.exit(f"{FILE} already exists. Published puzzles are frozen: rebuilding would change every player's puzzles.\n"
              "Only use --force before launch, or to start a brand-new schedule on purpose.")
with open(_os.path.join(OUT, FILE), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print("players", len(players_out), "jm", len(jm_out), "sl", len(sl_out), "k4", len(k4_out))
print(k4_report)
