"""Build Higher or Lower puzzles: hl-{sport}.json with 365 days x 5 questions.

Q1-2: headline career stat, famous players.  Q3-4: deeper career stat.  Q5: one specific season.
Career numbers come from the same {sport}.json player list Stat Line uses; season numbers come straight from the raw data.
"""
import os, sys, json, random, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SHOOTAROUND_OUT", os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import common, sports

DAYS = 365
def season_label(sport, y):
    return f"{y-1}–{str(y)[2:]}" if sport in ("nba", "nhl") else str(y)

def C(k, l, f, lo=None): return {"k": k, "l": l, "f": f, "min": lo}

# career stats (keys of the "s" object in {sport}.json players)
CAREER = {
  "nba": {"all": ([C("ppg","Career points per game","d1"), C("rpg","Career rebounds per game","d1"), C("apg","Career assists per game","d1"), C("g","Career games played","d0")],
                  [C("fg","Career FG%","p1"), C("x3","Career 3-point %","p1", .28), C("ft","Career free-throw %","p1"), C("spg","Career steals per game","d1"),
                   C("bpg","Career blocks per game","d1"), C("tov","Career turnovers per game","d1")])},
  "nhl": {"sk": ([C("g","Career goals","d0"), C("a","Career assists","d0"), C("p","Career points","d0"), C("gp","Career games played","d0")],
                 [C("pm","Career plus/minus","pm"), C("pim","Career penalty minutes","d0"), C("ppg","Career power-play goals","d0"),
                  C("gwg","Career game-winning goals","d0"), C("ppgame","Career points per game","d2")])},
  "mlb": {"hit": ([C("hr","Career home runs","d0"), C("h","Career hits","d0"), C("rbi","Career RBI","d0"), C("avg","Career batting average","p3")],
                  [C("sb","Career stolen bases","d0"), C("obp","Career on-base %","p3"), C("slg","Career slugging %","p3"), C("r","Career runs","d0"), C("bb","Career walks","d0")]),
          "pit": ([C("w","Career wins","d0"), C("so","Career strikeouts","d0"), C("sv","Career saves","d0", 1)],
                  [C("era","Career ERA","d2"), C("whip","Career WHIP","d2"), C("ip","Career innings pitched","d0"), C("l","Career losses","d0"), C("g","Career games pitched","d0")])},
  "nfl": {"qb": ([C("yds","Career passing yards","d0"), C("td","Career passing TDs","d0")],
                 [C("int_","Career interceptions thrown","d0"), C("cmp","Career completion %","p1"), C("ryds","Career rushing yards","d0")]),
          "rb": ([C("ryds","Career rushing yards","d0"), C("rtd","Career rushing TDs","d0")],
                 [C("ypc","Career yards per carry","d1"), C("rec","Career receptions","d0"), C("recyds","Career receiving yards","d0")]),
          "rec": ([C("rec","Career receptions","d0"), C("recyds","Career receiving yards","d0"), C("rectd","Career receiving TDs","d0")],
                  [C("ypr","Career yards per catch","d1"), C("g","Career games played","d0")]),
          "def": ([C("sk","Career sacks","d1"), C("ints","Career interceptions","d0")], [C("g","Career games played","d0"), C("st","Seasons as a starter","d0")])},
}
SEASON = {
  "nba": {"all": [C("ppg","Points per game","d1"), C("rpg","Rebounds per game","d1"), C("apg","Assists per game","d1"), C("fg","FG%","p1"), C("x3m","3-pointers made","d0")]},
  "nhl": {"sk": [C("g","Goals","d0"), C("a","Assists","d0"), C("p","Points","d0"), C("pm","Plus/minus","pm"), C("pim","Penalty minutes","d0")]},
  "mlb": {"hit": [C("hr","Home runs","d0"), C("avg","Batting average","p3"), C("rbi","RBI","d0"), C("sb","Stolen bases","d0"), C("h","Hits","d0")],
          "pit": [C("w","Wins","d0"), C("era","ERA","d2"), C("so","Strikeouts","d0")]},
  "nfl": {"qb": [C("yds","Passing yards","d0"), C("td","Passing TDs","d0"), C("int_","Interceptions thrown","d0")],
          "rb": [C("ryds","Rushing yards","d0"), C("rtd","Rushing TDs","d0")],
          "rec": [C("recyds","Receiving yards","d0"), C("rec","Receptions","d0"), C("rectd","Receiving TDs","d0")]},
}

def fmt(f, v):
    if v is None: return None
    if f == "d0": return f"{round(v):,}"
    if f == "d1": return f"{v:.1f}"
    if f == "d2": return f"{v:.2f}"
    if f == "p1": return f"{v*100:.1f}"
    if f == "p3": return f"{v:.3f}"
    if f == "pm": return f"{int(v):+d}"
    return str(v)

# ---------------------------------------------------------------- season tables: name -> [(label, team, role, stats)]
def nba_seasons(names):
    P = common.load()
    by = collections.defaultdict(list)
    for pid, p in P.items():
        if p["name"] in names and p["from"] >= 1980: by[p["name"]].append(pid)
    pid_of = {n: max(ids, key=lambda i: P[i]["g"]) for n, ids in by.items()}
    want = {v: k for k, v in pid_of.items()}
    tname = {(int(r["season"]), r["abbreviation"]): r["team"].replace("*", "") for r in common.rows("Team Abbrev.csv") if r["lg"] == "NBA"}
    rows = collections.defaultdict(dict)
    for r in common.rows("Player Totals.csv"):
        if r["lg"] != "NBA" or r["player_id"] not in want: continue
        s = int(r["season"])
        if r["team"] in common.MULTI or s not in rows[r["player_id"]]:
            rows[r["player_id"]][s] = r
    out = collections.defaultdict(list)
    num = common.num
    for pid, seasons in rows.items():
        for s, r in seasons.items():
            g = num(r["g"]) or 0
            if g < 40: continue
            fga = num(r["fga"]) or 0
            team = "2+ teams" if r["team"] in common.MULTI else common.nickname(tname.get((s, r["team"]), r["team"]))
            out[want[pid]].append((season_label("nba", s), team, "all", {
                "ppg": (num(r["pts"]) or 0) / g, "rpg": (num(r["trb"]) or 0) / g, "apg": (num(r["ast"]) or 0) / g,
                "fg": (num(r["fg"]) or 0) / fga if fga >= 300 else None, "x3m": num(r["x3p"])}))
    return out

def nhl_seasons(names):
    out = collections.defaultdict(list)
    best = {}
    rows = list(sports.rows(f"{sports.DATA}/nhl_NHL/data/skaters_by_season_summary.csv"))
    gp = collections.Counter()
    for r in rows: gp[(r["skaterFullName"], r["playerId"])] += sports.num(r["gamesPlayed"]) or 0
    for (n, pid), v in gp.items():
        if n in names and v > best.get(n, (None, -1))[1]: best[n] = (pid, v)
    want = {pid: n for n, (pid, _) in best.items()}
    for r in rows:
        if r["playerId"] not in want: continue
        g = sports.num(r["gamesPlayed"]) or 0
        if g < 40: continue
        y = int(r["seasonId"][4:])
        teams = r["teamAbbrevs"].split(",")
        team = "2+ teams" if len(teams) > 1 else sports.nhl_team(teams[0], y)[0]
        pm = r["plusMinus"]
        out[want[r["playerId"]]].append((season_label("nhl", y), team, "sk", {
            "g": sports.num(r["goals"]), "a": sports.num(r["assists"]), "p": sports.num(r["points"]),
            "pm": sports.num(pm) if pm not in ("", None) else None, "pim": sports.num(r["penaltyMinutes"])}))
    return out

def mlb_seasons(names):
    D = sports.DATA
    P = sports.load_mlb()
    by = collections.defaultdict(list)
    for pid, p in P.items():
        if p["name"] in names and p["from"] >= 1975: by[p["name"]].append(pid)
    want = {max(ids, key=lambda i: P[i]["fame"]): n for n, ids in by.items()}
    tname = {(int(r["yearID"]), r["teamID"]): r["name"] for r in sports.rows(f"{D}/mlb_Teams.csv")}
    bat = collections.defaultdict(lambda: collections.defaultdict(collections.Counter)); pit = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    teams = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in sports.rows(f"{D}/mlb_Batting.csv"):
        if r["playerID"] in want:
            y = int(r["yearID"]); teams[r["playerID"]][y].append(r["teamID"])
            for k in ["AB", "H", "HR", "RBI", "SB"]: bat[r["playerID"]][y][k] += sports.num(r[k]) or 0
    for r in sports.rows(f"{D}/mlb_Pitching.csv"):
        if r["playerID"] in want:
            y = int(r["yearID"])
            if r["teamID"] not in teams[r["playerID"]][y]: teams[r["playerID"]][y].append(r["teamID"])
            for k in ["W", "SO", "ER", "IPouts", "SV", "G"]: pit[r["playerID"]][y][k] += sports.num(r[k]) or 0
    out = collections.defaultdict(list)
    for pid, n in want.items():
        role = P[pid]["role"]
        for y in sorted(teams[pid]):
            tl = list(dict.fromkeys(teams[pid][y]))
            team = "2+ teams" if len(tl) > 1 else sports.mlb_nick(tname.get((y, tl[0]), tl[0]))[0]
            if role == "hit":
                b = bat[pid][y]
                if b["AB"] < 350: continue
                out[n].append((season_label("mlb", y), team, "hit", {"hr": b["HR"], "avg": b["H"] / b["AB"], "rbi": b["RBI"], "sb": b["SB"], "h": b["H"]}))
            elif role == "pit":
                q = pit[pid][y]; ip = q["IPouts"] / 3
                if ip < 120: continue
                out[n].append((season_label("mlb", y), team, "pit", {"w": q["W"], "era": q["ER"] * 9 / ip, "so": q["SO"]}))
    return out

def nfl_seasons(names):
    P = sports.load_nfl()
    by = {p["name"]: gid for gid, p in P.items() if p["name"] in names}
    want = {gid: n for n, gid in by.items()}
    out = collections.defaultdict(list)
    for r in sports.rows(f"{sports.DATA}/nfl/player_stats_season.csv"):
        if r["player_id"] not in want or r.get("season_type", "REG") != "REG": continue
        n = want[r["player_id"]]; role = P[r["player_id"]]["role"]; y = int(r["season"])
        g = lambda k: sports.num(r.get(k)) or 0
        team = sports.nfl_team(r["recent_team"], y)[0]
        if role == "qb" and g("attempts") >= 250:
            out[n].append((season_label("nfl", y), team, "qb", {"yds": g("passing_yards"), "td": g("passing_tds"), "int_": g("interceptions")}))
        elif role == "rb" and g("carries") >= 150:
            out[n].append((season_label("nfl", y), team, "rb", {"ryds": g("rushing_yards"), "rtd": g("rushing_tds")}))
        elif role == "rec" and g("receptions") >= 40:
            out[n].append((season_label("nfl", y), team, "rec", {"recyds": g("receiving_yards"), "rec": g("receptions"), "rectd": g("receiving_tds")}))
    return out

SEASON_FN = {"nba": nba_seasons, "nhl": nhl_seasons, "mlb": mlb_seasons, "nfl": nfl_seasons}

# ---------------------------------------------------------------- build
def build(sport, force=False):
    out_path = os.path.join(OUT, f"hl-{sport}.json")
    if os.path.exists(out_path) and not force:
        sys.exit(f"hl-{sport}.json already exists. Published puzzles are frozen; use --force only before launch.")
    D = json.load(open(os.path.join(OUT, f"{sport}.json"), encoding="utf-8"))
    pool = [p for p in D["players"] if p.get("s")]          # already sorted most-famous first
    rank = {p["n"]: i for i, p in enumerate(pool)}
    role_of = {p["n"]: (p.get("r") or "all") for p in pool}
    top = {"easy": pool[:200], "mid": pool[:400], "season": pool[:450]}
    def two(group):
        w = [1.0 / (1 + use_count[p["n"]]) ** 2 for p in group]
        a = rng.choices(group, weights=w)[0]
        b = rng.choices(group, weights=w)[0]
        return a, b
    seasons = SEASON_FN[sport]({p["n"] for p in top["season"]})
    rng = random.Random(f"hl-{sport}")
    days, used = [], set()
    use_count = collections.Counter()
    rank = rank

    def pick_career(level, stats_by_role):
        group = top["easy"] if level == 0 else top["mid"]
        for _ in range(4000):
            a, b = two(group)
            if a is b: continue
            ra = role_of[a["n"]]
            if role_of[b["n"]] != ra or ra not in stats_by_role: continue
            if use_count[a["n"]] > 14 or use_count[b["n"]] > 14: continue
            stat = rng.choice(stats_by_role[ra][level])
            va, vb = a["s"].get(stat["k"]), b["s"].get(stat["k"])
            if va is None or vb is None: continue
            if stat["min"] is not None and (va < stat["min"] or vb < stat["min"]): continue
            if fmt(stat["f"], va) == fmt(stat["f"], vb): continue
            key = ("c", stat["k"], frozenset((a["n"], b["n"])))
            if key in used: continue
            used.add(key)
            return {"s": stat["l"], "f": stat["f"], "a": {"n": a["n"], "c": "Career", "v": va}, "b": {"n": b["n"], "c": "Career", "v": vb}}
        raise RuntimeError("no career pair")

    season_players = [n for n in seasons if seasons[n]]
    def pick_season():
        for _ in range(6000):
            w = [1.0 / (1 + use_count[n]) ** 2 for n in season_players]
            na, nb = rng.choices(season_players, weights=w, k=2)
            if na == nb: continue
            sa, sb = rng.choice(seasons[na]), rng.choice(seasons[nb])
            if sa[2] != sb[2] or sa[2] not in SEASON[sport]: continue
            if use_count[na] > 14 or use_count[nb] > 14: continue
            stat = rng.choice(SEASON[sport][sa[2]])
            va, vb = sa[3].get(stat["k"]), sb[3].get(stat["k"])
            if va is None or vb is None or fmt(stat["f"], va) == fmt(stat["f"], vb): continue
            key = ("s", stat["k"], frozenset(((na, sa[0]), (nb, sb[0]))))
            if key in used: continue
            used.add(key)
            ctx = lambda s: f"{s[0]} season" + (f" · {s[1]}" if s[1] else "")
            return {"s": stat["l"], "f": stat["f"], "a": {"n": na, "c": ctx(sa), "v": va}, "b": {"n": nb, "c": ctx(sb), "v": vb}}
        raise RuntimeError("no season pair")

    stats_by_role = {r: v for r, v in CAREER[sport].items()}
    stats_by_role = {r: {0: v[0], 1: v[1]} for r, v in stats_by_role.items()}
    for d in range(DAYS):
        qs = [pick_career(0, stats_by_role), pick_career(0, stats_by_role), pick_career(1, stats_by_role), pick_career(1, stats_by_role), pick_season()]
        for q in qs:
            use_count[q["a"]["n"]] += 1; use_count[q["b"]["n"]] += 1
            for side in ("a", "b"):
                v = q[side]["v"]; q[side]["v"] = round(v, 4) if isinstance(v, float) else v
        days.append(qs)
    json.dump({"sport": sport, "epoch": D["epoch"], "days": days}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{sport}: {len(days)} days, {len(days)*5} questions, players with seasons {len(season_players)}, distinct players {len(use_count)}, max uses {max(use_count.values())}")

if __name__ == "__main__":
    force = "--force" in sys.argv
    for s in [a for a in sys.argv[1:] if not a.startswith("--")]:
        build(s, force)
