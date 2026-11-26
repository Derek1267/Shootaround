"""Soccer loader for Shootaround, from the Transfermarkt dataset (github.com/dcaribou/transfermarkt-datasets).

Covers players who played in the Premier League, La Liga, Serie A, Bundesliga, Ligue 1 or MLS.
League numbers start in 2012-13 (that is where the dataset starts); career paths come from the
transfer history, which reaches back to youth teams for most players.
Returns players in the same shape as sports.load_nfl / load_nhl / load_mlb.
"""
import os, re, math, collections, datetime
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.environ.get("SHOOTAROUND_RAW", os.path.join(HERE, "..", "raw-data"))
D = os.path.join(RAW, "soccer")
TODAY = os.environ.get("SHOOTAROUND_TODAY", datetime.date.today().isoformat())

BIG = {"GB1": "Premier League", "ES1": "La Liga", "IT1": "Serie A", "L1": "Bundesliga", "FR1": "Ligue 1", "MLS1": "MLS"}
MIN_BIG_APPS = 40            # league games in the six leagues above to be in the player pool

YOUTH = re.compile(r"(Youth|Yth\.?|\bU-?\d{2}\b|\bU\d{2}\b|Sub-?\d{2}|Juniors?|\bJV\b|Academy|Akademie|Primavera|Reserves?|Castilla|"
                   r"Atlètic|Madrileño|Sevilla Atl|Bilbao Athletic|Basconia|Betis Deportivo|Deportivo Alavés B|Villarreal B|Valencia Mestalla|Mestalla|Jong |Amateure|\bII\b|\bB$| B$|\bC$|Juvenil|Jgd|Promesas|Next Gen|\bU1\d\b|\bU2\d\b|Juniores)", re.I)
SKIP = re.compile(r"^(Without Club|Unknown|Retired|Career break|Ban|Disqualification|Pause|Unattached|Own Youth|\?)$", re.I)

def _num(x):
    try:
        v = float(x); return v if v == v else None
    except (TypeError, ValueError):
        return None

def season_label(y):
    """2019 -> '2019–20' (Transfermarkt seasons are named by their first year)."""
    return f"{y}–{str(y + 1)[2:]}"

_CACHE = {}
def tables():
    if _CACHE: return _CACHE
    rd = lambda n, **k: pd.read_csv(os.path.join(D, f"{n}.csv.gz"), **k)
    comps = rd("competitions")
    leagues = set(comps[comps["type"] == "domestic_league"]["competition_id"])
    comp_country = dict(zip(comps["competition_id"], comps["country_name"]))
    games = rd("games", usecols=["game_id", "competition_id", "season"])
    app = rd("appearances", usecols=["game_id", "player_id", "player_club_id", "competition_id", "goals", "assists", "minutes_played", "yellow_cards", "red_cards"])
    app = app[app["competition_id"].isin(leagues)].merge(games[["game_id", "season"]], on="game_id", how="left")
    clubs = rd("clubs", usecols=["club_id", "name", "domestic_competition_id"])
    tr = rd("transfers")
    tr = tr[tr["transfer_date"] <= TODAY].sort_values(["player_id", "transfer_date"])
    # short club names (the ones fans use) from the transfer records; fall back to the official name
    short = collections.defaultdict(collections.Counter)
    for cid, n in zip(tr["from_club_id"], tr["from_club_name"]): short[cid][n] += 1
    for cid, n in zip(tr["to_club_id"], tr["to_club_name"]): short[cid][n] += 1
    name_of = {cid: tidy(c.most_common(1)[0][0]) for cid, c in short.items()}
    for cid, n in zip(clubs["club_id"], clubs["name"]): name_of.setdefault(cid, tidy(n))
    country_of = {cid: comp_country.get(dc, "") for cid, dc in zip(clubs["club_id"], clubs["domestic_competition_id"])}
    _CACHE.update(comps=comps, leagues=leagues, comp_country=comp_country, app=app, clubs=clubs, tr=tr,
                  players=rd("players"), name_of=name_of, country_of=country_of)
    return _CACHE

def build_path(trs, dob_year, name_of, country_of):
    """Senior clubs in order from the transfer list. Loans that end with a return to the parent club
    become one stop marked as a loan. Returns (path, complete)."""
    stops, complete, first = [], True, True
    for r in trs:
        f_id, t_id = r["from_club_id"], r["to_club_id"]
        f, t = str(name_of.get(f_id, r["from_club_name"])), str(name_of.get(t_id, r["to_club_name"]))
        f_ok = not (YOUTH.search(f) or SKIP.match(f.strip())); t_ok = not (YOUTH.search(t) or SKIP.match(t.strip()))
        if first:
            # the history is complete if it starts in a youth team, or with a first move as a teenager
            if f_ok and not SKIP.match(f.strip()):
                yr = int(r["transfer_date"][:4])
                if dob_year and yr - dob_year > 20: complete = False
                stops.append({"id": f_id, "t": f, "date": r["transfer_date"], "fee": None})
            first = False
        if f_ok and stops and stops[-1]["id"] != f_id: complete = False      # a gap in the record
        if t_ok and (not stops or stops[-1]["id"] != t_id):
            stops.append({"id": t_id, "t": t, "date": r["transfer_date"], "fee": _num(r["transfer_fee"])})
    # loans: P -> L -> P, where the move into L cost nothing and the return comes within two years
    i, out = 0, []
    while i < len(stops):
        s = stops[i]
        if (out and i + 1 < len(stops) and stops[i + 1]["id"] == out[-1]["id"] and not s["fee"]
                and (int(stops[i + 1]["date"][:4]) - int(s["date"][:4])) <= 2):
            out.append({**s, "loan": True}); out.append({**stops[i + 1], "ret": True}); i += 2; continue
        out.append(s); i += 1
    path = []
    for s in out:
        if s.get("ret"): continue                                     # back at the parent club after a loan: not a new stop
        if path and path[-1]["id"] == s["id"]:
            path[-1]["loan"] = path[-1].get("loan") and s.get("loan"); continue
        path.append({"id": int(s["id"]), "t": s["t"], "c": country_of.get(s["id"], ""), "loan": bool(s.get("loan"))})
    return path, complete

RENAME = {"Miami": "Inter Miami", "Spurs": "Tottenham", "Bayern Munich": "Bayern", "Atlético": "Atlético Madrid", "Inter": "Inter Milan",
          "Sevilla FC": "Sevilla", "FC Empoli": "Empoli", "RSC Anderlecht": "Anderlecht", "Real Betis": "Betis", "B. Dortmund": "Dortmund",
          "Bor. Dortmund": "Dortmund", "Bay. Leverkusen": "Leverkusen", "Bayer 04 Leverkusen": "Leverkusen", "E. Frankfurt": "Eintracht Frankfurt",
          "Bor. M'gladbach": "Gladbach", "Nott'm Forest": "Nottingham Forest", "Sheff Utd": "Sheffield United", "Shakhtar D.": "Shakhtar Donetsk", "FC Schalke 04": "Schalke 04", "Hertha BSC": "Hertha Berlin",
          "Wolverhampton Wanderers": "Wolves", "Brighton & Hove Albion": "Brighton"}

def tidy(n):
    """Fan-friendly club names: drop FC/CF/SC tags and expand abbreviations."""
    n = str(n).strip()
    n = RENAME.get(n, n)
    n = re.sub(r"^(1\. ?FC |FC |AC |SC |SV |CF |RC |RCD |SD |UD |CD |AS |SS |US |OGC |RC )", "", n)
    n = re.sub(r" (FC|CF|SC|AC|SAD)$", "", n)
    for a, b in {"G. Bordeaux": "Bordeaux", "R. Strasbourg": "Strasbourg", "Dep. La Coruña": "Deportivo La Coruña", "Argentinos Jrs.": "Argentinos Juniors",
                 "Atl. Nacional": "Atlético Nacional", "Bor. Dortmund": "Dortmund", "Bay. Leverkusen": "Leverkusen", "E. Frankfurt": "Eintracht Frankfurt",
                 "Milan": "AC Milan"}.items():
        if n == a: n = b
    return RENAME.get(n, n)

POS = {"Goalkeeper": "gk", "Defender": "def", "Midfield": "mid", "Attack": "att"}

def load_soccer():
    T = tables()
    app, players, name_of, country_of = T["app"], T["players"], T["name_of"], T["country_of"]
    big = app[app["competition_id"].isin(BIG)]
    big_apps = big.groupby("player_id").size()
    keep = set(big_apps[big_apps >= MIN_BIG_APPS].index)
    a = app[app["player_id"].isin(keep)]
    tot = a.groupby("player_id").agg(g=("game_id", "size"), gl=("goals", "sum"), ast=("assists", "sum"), mins=("minutes_played", "sum"),
                                     yc=("yellow_cards", "sum"), rc=("red_cards", "sum"), s0=("season", "min"), s1=("season", "max"),
                                     ns=("season", "nunique"))
    leagues_of = a.groupby("player_id")["competition_id"].agg(lambda s: sorted(set(s)))
    seasons = a.groupby(["player_id", "season", "player_club_id"]).agg(g=("game_id", "size"), gl=("goals", "sum"), ast=("assists", "sum"),
                                                                    comp=("competition_id", "first")).reset_index()
    by_tr = {pid: g.to_dict("records") for pid, g in T["tr"][T["tr"]["player_id"].isin(keep)].groupby("player_id")}
    out = {}
    for r in players[players["player_id"].isin(keep)].to_dict("records"):
        pid = int(r["player_id"]); t = tot.loc[pid]
        dob = str(r["date_of_birth"])[:10] if isinstance(r["date_of_birth"], str) else ""
        dob_y = int(dob[:4]) if dob else None
        path, complete = build_path(by_tr.get(pid, []), dob_y, name_of, country_of)
        if not path: complete = False
        role = POS.get(r["position"])
        if not role: continue
        mv = _num(r["highest_market_value_in_eur"]) or 0
        c_, i_ = _num(r["international_caps"]), _num(r["international_goals"])
        caps, ig = (int(c_), int(i_ or 0)) if c_ is not None else (None, None)   # blank for some older players: unknown, not zero
        ht = _num(r["height_in_cm"]); ht = int(ht) if ht and ht > 140 else None
        s0, s1 = int(t["s0"]), int(t["s1"])
        p = {
            "id": pid, "name": r["name"].strip(), "from": s0, "to": s1, "seasons": int(t["ns"]), "path": path, "ambiguous": not complete,
            "pos": r["sub_position"] if isinstance(r["sub_position"], str) else r["position"], "role": role, "colleges": [], "draft": None,
            "ht": ht, "birth": {"country": r["country_of_birth"] if isinstance(r["country_of_birth"], str) else "",
                                "city": r["city_of_birth"].strip() if isinstance(r["city_of_birth"], str) else "", "region": ""},
            "nat": r["country_of_citizenship"] if isinstance(r["country_of_citizenship"], str) else "",
            "dob": dob, "hand": {"foot": r["foot"] if isinstance(r["foot"], str) else ""}, "honors": {"caps": caps, "ig": ig},
            "awards": [], "rings": 0, "hof": False, "mv": mv, "leagues": list(leagues_of.loc[pid]), "big_apps": int(big_apps.get(pid, 0)),
            "tot": {"g": int(t["g"]), "gl": int(t["gl"]), "ast": int(t["ast"]), "caps": caps or 0, "ig": ig or 0},
        }
        g = int(t["g"]) or 1
        p["stats"] = {"g": int(t["g"]), "gl": int(t["gl"]), "ast": int(t["ast"]), "min": int(t["mins"]), "yc": int(t["yc"]), "rc": int(t["rc"]),
                      "gpg": float(round(t["gl"] / max(t["mins"], 1) * 90, 2)), "caps": caps, "ig": ig, "mv": float(round(mv / 1e6, 1))}
        p["fame"] = math.sqrt(mv / 1e6) + p["big_apps"] / 60 + int(t["gl"]) / 30 + int(t["ast"]) / 40 + (caps or 0) / 25
        out[pid] = p
    return out

def soccer_seasons(names):
    """name -> [(season label, club, role, {gl, ast})] for league seasons with 15+ games, for Higher or Lower."""
    T = tables(); P = {p["id"]: p for p in load_soccer().values() if p["name"] in names}
    app = T["app"][T["app"]["player_id"].isin(P)]
    s = app.groupby(["player_id", "season", "player_club_id"]).agg(g=("game_id", "size"), gl=("goals", "sum"), ast=("assists", "sum")).reset_index()
    out = collections.defaultdict(list)
    for r in s[s["g"] >= 15].to_dict("records"):
        p = P[r["player_id"]]
        if p["role"] == "gk": continue
        out[p["name"]].append((season_label(int(r["season"])), T["name_of"].get(r["player_club_id"], ""), p["role"], {"gl": int(r["gl"]), "ast": int(r["ast"])}))
    return out
