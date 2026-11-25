import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
"""Shared loader: turns the Basketball-Reference CSVs into one clean player table."""
import csv, collections, os

D = _os.path.join(RAW, "bball-reference-datasets", "Data")
MULTI = {"TOT", "2TM", "3TM", "4TM", "5TM"}

# NBA champions by season end-year (1980-2025). Used only for retired players' ring counts.
CHAMPS = {1980:"LAL",1981:"BOS",1982:"LAL",1983:"PHI",1984:"BOS",1985:"LAL",1986:"BOS",1987:"LAL",1988:"LAL",
          1989:"DET",1990:"DET",1991:"CHI",1992:"CHI",1993:"CHI",1994:"HOU",1995:"HOU",1996:"CHI",1997:"CHI",
          1998:"CHI",1999:"SAS",2000:"LAL",2001:"LAL",2002:"LAL",2003:"SAS",2004:"DET",2005:"SAS",2006:"MIA",
          2007:"SAS",2008:"BOS",2009:"LAL",2010:"LAL",2011:"DAL",2012:"MIA",2013:"MIA",2014:"SAS",2015:"GSW",
          2016:"CLE",2017:"GSW",2018:"GSW",2019:"TOR",2020:"LAL",2021:"MIL",2022:"GSW",2023:"DEN",2024:"BOS",2025:"OKC",2026:"NYK"}

def rows(name):
    with open(os.path.join(D, name), newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def nickname(full):
    if full.endswith("Trail Blazers"): return "Trail Blazers"
    return full.split()[-1]

def city(full):
    nick = nickname(full)
    return full[: -len(nick)].strip()

def load():
    # team full names per (season, abbreviation)
    tname = {}
    for r in rows("Team Abbrev.csv"):
        if r["lg"] == "NBA":
            tname[(int(r["season"]), r["abbreviation"])] = r["team"].replace("*", "")

    info = {r["player_id"]: r for r in rows("Player Career Info.csv")}

    # season-by-season team rows (NBA only)
    seasons = collections.defaultdict(lambda: collections.defaultdict(list))
    totals = collections.defaultdict(dict)  # pid -> season -> row (TOT row if traded)
    for r in rows("Player Totals.csv"):
        if r["lg"] != "NBA": continue
        pid, s = r["player_id"], int(r["season"])
        if r["team"] in MULTI:
            totals[pid][s] = r
        else:
            seasons[pid][s].append(r["team"])
            totals[pid].setdefault(s, r)

    draft = {}
    for r in rows("Draft Pick History.csv"):
        if r["lg"] == "NBA" and r["player_id"] and r["player_id"] not in draft:
            draft[r["player_id"]] = r

    allstar = collections.Counter()
    for r in rows("All-Star Selections.csv"):
        if r["lg"] == "NBA": allstar[r["player_id"]] += 1

    awards = collections.defaultdict(list)
    for r in rows("Player Award Shares.csv"):
        if r["winner"] == "TRUE" and r["award"].startswith("nba"):
            awards[r["player_id"]].append((r["award"].replace("nba ", ""), int(r["season"])))

    allnba = collections.Counter()
    alldef = collections.Counter()
    for r in rows("End of Season Teams.csv"):
        if r["lg"] != "NBA": continue
        if r["type"] == "All-NBA": allnba[r["player_id"]] += 1
        if r["type"] == "All-Defense": alldef[r["player_id"]] += 1

    players = {}
    for pid, by_season in seasons.items():
        if pid not in info: continue
        ci = info[pid]
        yrs = sorted(by_season)
        # ---- order teams inside traded seasons using the seasons before and after
        path, ambiguous = [], False
        prev_last = None
        for i, s in enumerate(yrs):
            teams = list(dict.fromkeys(by_season[s]))
            if len(teams) > 1:
                nxt = list(dict.fromkeys(by_season[yrs[i + 1]])) if i + 1 < len(yrs) else None
                first = prev_last if prev_last in teams else None
                last = None
                if nxt and len(nxt) == 1 and nxt[0] in teams and nxt[0] != first:
                    last = nxt[0]
                rest = [t for t in teams if t not in (first, last)]
                if len(rest) > 1 or (first is None and last is None):
                    ambiguous = True
                if first is None and len(rest) == 1 and last is not None and len(teams) == 2:
                    first = rest[0]; rest = []
                elif last is None and len(rest) == 1 and first is not None and len(teams) == 2:
                    last = rest[0]; rest = []
                teams = [t for t in [first] + rest + [last] if t]
            for t in teams:
                full = tname.get((s, t), t)
                if path and path[-1]["abbr"] == t:
                    path[-1]["to"] = s
                else:
                    path.append({"abbr": t, "full": full, "from": s, "to": s})
            prev_last = teams[-1]

        # ---- career totals (one row per season; TOT row when traded)
        tot = collections.Counter()
        has = collections.Counter()
        for s, r in totals[pid].items():
            for k in ["g","mp","fg","fga","x3p","x3pa","ft","fta","trb","ast","stl","blk","tov","pts"]:
                v = num(r.get(k))
                if v is not None:
                    tot[k] += v; has[k] += 1
        g = tot["g"] or 1

        rings = 0
        for s in yrs:
            if s in CHAMPS and by_season[s] and CHAMPS[s] in by_season[s]:
                # credit only if the champion was the player's final team that season
                ordered = [p["abbr"] for p in path if p["from"] <= s <= p["to"]]
                if ordered and ordered[-1] == CHAMPS[s]:
                    rings += 1

        d = draft.get(pid)
        ht = num(ci["ht_in_in"])
        players[pid] = {
            "id": pid, "name": ci["player"], "pos": ci["pos"], "ht": int(ht) if ht else None,
            "colleges": [c.strip() for c in ci["colleges"].split(",")] if ci["colleges"] not in ("", "NA") else [],
            "hof": ci["hof"] == "TRUE", "from": yrs[0], "to": yrs[-1], "seasons": len(yrs),
            "path": path, "ambiguous": ambiguous,
            "draft": {"year": int(d["season"]), "pick": int(d["overall_pick"]), "team": tname.get((int(d["season"]), d["tm"]), d["tm"])} if d and d["overall_pick"] not in ("", "NA") else None,
            "allstar": allstar[pid], "allnba": allnba[pid], "alldef": alldef[pid],
            "awards": awards[pid], "rings": rings,
            "tot": dict(tot), "has": dict(has), "g": int(tot["g"]),
        }
    return players

def per_game(p):
    t, g = p["tot"], p["tot"].get("g", 0) or 1
    pct = lambda a, b: round(t.get(a, 0) / t[b], 3) if t.get(b) else None
    return {
        "g": int(t.get("g", 0)), "ppg": round(t.get("pts", 0) / g, 1), "rpg": round(t.get("trb", 0) / g, 1),
        "apg": round(t.get("ast", 0) / g, 1), "spg": round(t.get("stl", 0) / g, 1), "bpg": round(t.get("blk", 0) / g, 1),
        "tov": round(t.get("tov", 0) / g, 1), "fg": pct("fg", "fga"), "x3": pct("x3p", "x3pa"), "ft": pct("ft", "fta"),
        "x3m": int(t.get("x3p", 0)),
    }
