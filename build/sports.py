import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
"""Adapters: turn each league's raw data into one player format shared by the puzzle builders.

Player dict:
  id, name, from, to (season end-years), seasons, path [{t, c, from, to}], ambiguous,
  pos, role, colleges [], draft {year, pick, round, team} | None, ht (inches), wt,
  birth {country, region}, hand {...}, honors {allstar, allpro, ...}, awards [(code, year)],
  rings, hof, tot {...} career totals, stats {...} Stat Line numbers, fame
"""
import csv, collections, os

DATA = RAW

def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)

def num(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None

def add_stint(path, t, c, season):
    if path and path[-1]["t"] == t and path[-1]["c"] == c:
        path[-1]["to"] = season
    else:
        path.append({"t": t, "c": c, "from": season, "to": season})

# =====================================================================
# NFL  (nflverse: draft picks 1980+ with career totals, season rosters)
# =====================================================================
NFL_TEAMS = {
    "BUF": ("Bills", "Buffalo"), "MIA": ("Dolphins", "Miami"), "NE": ("Patriots", "New England"), "NYJ": ("Jets", "New York"),
    "PIT": ("Steelers", "Pittsburgh"), "CIN": ("Bengals", "Cincinnati"), "CLE": ("Browns", "Cleveland"), "CLV": ("Browns", "Cleveland"),
    "JAX": ("Jaguars", "Jacksonville"), "IND": ("Colts", "Indianapolis"), "KC": ("Chiefs", "Kansas City"), "DEN": ("Broncos", "Denver"),
    "SD": ("Chargers", "San Diego"), "LAC": ("Chargers", "Los Angeles"), "SEA": ("Seahawks", "Seattle"), "DAL": ("Cowboys", "Dallas"),
    "NYG": ("Giants", "New York"), "PHI": ("Eagles", "Philadelphia"), "CHI": ("Bears", "Chicago"), "DET": ("Lions", "Detroit"),
    "GB": ("Packers", "Green Bay"), "MIN": ("Vikings", "Minnesota"), "ATL": ("Falcons", "Atlanta"), "CAR": ("Panthers", "Carolina"),
    "NO": ("Saints", "New Orleans"), "TB": ("Buccaneers", "Tampa Bay"), "SF": ("49ers", "San Francisco"),
    "RAI": ("Raiders", "Los Angeles"), "LV": ("Raiders", "Las Vegas"), "RAM": ("Rams", "Los Angeles"), "SL": ("Rams", "St. Louis"),
    "PHO": ("Cardinals", "Phoenix"), "HST": ("Texans", "Houston"), "BLT": ("Ravens", "Baltimore"), "ARZ": ("Cardinals", "Arizona"),
}
PFR = {"GNB": "GB", "KAN": "KC", "LAR": "LA", "LVR": "LV", "NOR": "NO", "NWE": "NE", "SDG": "SD", "SFO": "SF", "TAM": "TB"}
def nfl_team(abbr, y):
    abbr = PFR.get(abbr, abbr)
    if abbr == "WAS": return ("Commanders", "Washington") if y >= 2022 else ("Washington", "")
    if abbr == "OAK": return ("Raiders", "Oakland")
    if abbr == "LA": return ("Rams", "Los Angeles")
    if abbr == "STL": return ("Cardinals", "St. Louis") if y <= 1987 else ("Rams", "St. Louis")
    if abbr == "ARI": return ("Cardinals", "Arizona") if y >= 1994 else ("Cardinals", "Phoenix")
    if abbr == "HOU": return ("Oilers", "Houston") if y <= 1996 else ("Texans", "Houston")
    if abbr == "TEN": return ("Oilers", "Tennessee") if y <= 1998 else ("Titans", "Tennessee")
    if abbr == "BAL": return ("Colts", "Baltimore") if y <= 1983 else ("Ravens", "Baltimore")
    return NFL_TEAMS.get(abbr, (abbr, ""))

# Super Bowl winners by season (season year, not game year)
NFL_CHAMPS = {1980:"Raiders",1981:"49ers",1982:"Washington",1983:"Raiders",1984:"49ers",1985:"Bears",1986:"Giants",1987:"Washington",
    1988:"49ers",1989:"49ers",1990:"Giants",1991:"Washington",1992:"Cowboys",1993:"Cowboys",1994:"49ers",1995:"Cowboys",1996:"Packers",
    1997:"Broncos",1998:"Broncos",1999:"Rams",2000:"Ravens",2001:"Patriots",2002:"Buccaneers",2003:"Patriots",2004:"Patriots",2005:"Steelers",
    2006:"Colts",2007:"Giants",2008:"Steelers",2009:"Saints",2010:"Packers",2011:"Giants",2012:"Ravens",2013:"Seahawks",2014:"Patriots",
    2015:"Broncos",2016:"Patriots",2017:"Eagles",2018:"Patriots",2019:"Chiefs",2020:"Buccaneers",2021:"Rams",2022:"Chiefs",2023:"Chiefs",2024:"Eagles",2025:"Seahawks"}

NFL_POS = {"QB": "Quarterback", "RB": "Running back", "FB": "Fullback", "WR": "Wide receiver", "TE": "Tight end", "DE": "Defensive end",
    "DT": "Defensive tackle", "NT": "Nose tackle", "LB": "Linebacker", "OLB": "Linebacker", "ILB": "Linebacker", "MLB": "Linebacker",
    "CB": "Cornerback", "S": "Safety", "SS": "Safety", "FS": "Safety", "DB": "Defensive back", "DL": "Defensive line", "K": "Kicker", "P": "Punter"}
NFL_ROLE = {"QB": "qb", "RB": "rb", "FB": "rb", "WR": "rec", "TE": "rec"}
NFL_DEF = {"DE","DT","NT","LB","OLB","ILB","MLB","CB","S","SS","FS","DB","DL"}

def load_nfl():
    D = f"{DATA}/nfl"
    picks = {}
    for r in rows(f"{D}/draft_picks.csv"):
        g = r["gsis_id"]
        if not g or g == "NA": continue
        picks[g] = r
    # rosters -> paths (rows inside a season ordered by the last week with that team)
    seasons = collections.defaultdict(dict)
    bio = {}
    for y in range(1980, 2026):
        for r in rows(f"{D}/roster_{y}.csv"):
            g = r["gsis_id"]
            if g not in picks: continue
            wk = num(r.get("week"))
            if wk is None: wk = -1
            seasons[g].setdefault(y, {})
            seasons[g][y][r["team"]] = max(wk, seasons[g][y].get(r["team"], 0))
            bio[g] = r
    out = {}
    for g, pk in picks.items():
        if g not in seasons: continue
        yrs = sorted(seasons[g])
        path = []
        amb = any(len(v) > 1 and min(v.values()) < 0 for v in seasons[g].values())
        for y in yrs:
            for abbr, _ in sorted(seasons[g][y].items(), key=lambda kv: kv[1]):
                t, c = nfl_team(abbr, y)
                add_stint(path, t, c, y)
        to = int(num(pk["to"]) or yrs[-1])
        pos = pk["position"]
        role = NFL_ROLE.get(pos, "def" if pos in NFL_DEF else None)
        gm = int(num(pk["games"]) or 0)
        tot = {k: num(pk[k]) or 0 for k in ["pass_completions","pass_attempts","pass_yards","pass_tds","pass_ints","rush_atts","rush_yards",
               "rush_tds","receptions","rec_yards","rec_tds","def_solo_tackles","def_ints","def_sacks","seasons_started","car_av"]}
        tot["games"] = gm
        rings = sum(1 for y in yrs if y in NFL_CHAMPS and [p["t"] for p in path if p["from"] <= y <= p["to"]][-1:] == [NFL_CHAMPS[y]])
        b = bio.get(g, {})
        ht, wt = num(b.get("height")), num(b.get("weight"))
        p = {
            "id": g, "name": pk["pfr_player_name"], "from": yrs[0], "to": max(to, yrs[-1]), "seasons": len(yrs),
            "path": path, "ambiguous": amb, "pos": NFL_POS.get(pos, pos), "role": role,
            "colleges": [pk["college"]] if pk["college"] and pk["college"] != "NA" else [],
            "draft": {"year": int(pk["season"]), "pick": int(pk["pick"]), "round": int(pk["round"]), "team": nfl_team(pk["team"], int(pk["season"]))[0]},
            "ht": int(ht) if ht else None, "wt": int(wt) if wt else None, "birth": {}, "hand": {},
            "honors": {"probowl": int(num(pk["probowls"]) or 0), "allpro": int(num(pk["allpro"]) or 0)},
            "awards": [], "rings": rings, "hof": pk["hof"] == "TRUE", "tot": tot,
        }
        p["stats"] = nfl_stats(p)
        p["fame"] = (p["honors"]["probowl"] * 4 + p["honors"]["allpro"] * 5 + tot["car_av"] / 8 + p["hof"] * 8 + rings * 1.5
                     + (3 if p["draft"]["round"] == 1 else 0) + (2 if p["draft"]["pick"] <= 5 else 0) + gm / 60)
        out[g] = p
    return out

def nfl_stats(p):
    t = p["tot"]; s = {"g": int(t["games"]), "st": int(t["seasons_started"])}
    r = p["role"]
    if r == "qb":
        s.update(yds=int(t["pass_yards"]), td=int(t["pass_tds"]), int_=int(t["pass_ints"]), att=int(t["pass_attempts"]),
                 cmp=round(t["pass_completions"] / t["pass_attempts"], 3) if t["pass_attempts"] else None,
                 ryds=int(t["rush_yards"]), rtd=int(t["rush_tds"]))
    elif r == "rb":
        s.update(ryds=int(t["rush_yards"]), rtd=int(t["rush_tds"]), ratt=int(t["rush_atts"]),
                 ypc=round(t["rush_yards"] / t["rush_atts"], 1) if t["rush_atts"] else None,
                 rec=int(t["receptions"]), recyds=int(t["rec_yards"]), rectd=int(t["rec_tds"]))
    elif r == "rec":
        s.update(rec=int(t["receptions"]), recyds=int(t["rec_yards"]), rectd=int(t["rec_tds"]),
                 ypr=round(t["rec_yards"] / t["receptions"], 1) if t["receptions"] else None, ryds=int(t["rush_yards"]))
    elif r == "def":
        s.update(sk=t["def_sacks"], ints=int(t["def_ints"]))
    return s

# =====================================================================
# NHL  (NHL stats API scrape: skaters by season + bios)
# =====================================================================
NHL_TEAMS = {"ANA": ("Ducks", "Anaheim"), "ARI": ("Coyotes", "Arizona"), "PHX": ("Coyotes", "Phoenix"), "ATL": ("Thrashers", "Atlanta"),
    "AFM": ("Flames", "Atlanta"), "BOS": ("Bruins", "Boston"), "BUF": ("Sabres", "Buffalo"), "CGY": ("Flames", "Calgary"),
    "CAR": ("Hurricanes", "Carolina"), "CHI": ("Blackhawks", "Chicago"), "CLE": ("Barons", "Cleveland"), "CLR": ("Rockies", "Colorado"),
    "COL": ("Avalanche", "Colorado"), "CBJ": ("Blue Jackets", "Columbus"), "DAL": ("Stars", "Dallas"), "DET": ("Red Wings", "Detroit"),
    "EDM": ("Oilers", "Edmonton"), "FLA": ("Panthers", "Florida"), "HFD": ("Whalers", "Hartford"), "KCS": ("Scouts", "Kansas City"),
    "LAK": ("Kings", "Los Angeles"), "MIN": ("Wild", "Minnesota"), "MNS": ("North Stars", "Minnesota"), "MTL": ("Canadiens", "Montréal"),
    "NSH": ("Predators", "Nashville"), "NJD": ("Devils", "New Jersey"), "NYI": ("Islanders", "New York"), "NYR": ("Rangers", "New York"),
    "OTT": ("Senators", "Ottawa"), "PHI": ("Flyers", "Philadelphia"), "PIT": ("Penguins", "Pittsburgh"), "QUE": ("Nordiques", "Québec"),
    "SJS": ("Sharks", "San Jose"), "SEA": ("Kraken", "Seattle"), "STL": ("Blues", "St. Louis"), "TBL": ("Lightning", "Tampa Bay"),
    "TOR": ("Maple Leafs", "Toronto"), "VAN": ("Canucks", "Vancouver"), "VGK": ("Golden Knights", "Vegas"), "WSH": ("Capitals", "Washington"),
    "WIN": ("Jets", "Winnipeg"), "WPG": ("Jets", "Winnipeg"), "CGS": ("Golden Seals", "California")}
def nhl_team(abbr, y):
    if abbr == "ANA" and y <= 2006: return ("Mighty Ducks", "Anaheim")
    if abbr == "UTA": return ("Hockey Club", "Utah") if y == 2025 else ("Mammoth", "Utah")
    return NHL_TEAMS.get(abbr, (abbr, ""))
# Stanley Cup winners by season end-year
NHL_CHAMPS = {1980:"NYI",1981:"NYI",1982:"NYI",1983:"NYI",1984:"EDM",1985:"EDM",1986:"MTL",1987:"EDM",1988:"EDM",1989:"CGY",1990:"EDM",
    1991:"PIT",1992:"PIT",1993:"MTL",1994:"NYR",1995:"NJD",1996:"COL",1997:"DET",1998:"DET",1999:"DAL",2000:"NJD",2001:"COL",2002:"DET",
    2003:"NJD",2004:"TBL",2006:"CAR",2007:"ANA",2008:"DET",2009:"PIT",2010:"CHI",2011:"BOS",2012:"LAK",2013:"CHI",2014:"LAK",2015:"CHI",
    2016:"PIT",2017:"PIT",2018:"WSH",2019:"STL",2020:"TBL",2021:"TBL",2022:"COL",2023:"VGK",2024:"FLA",2025:"FLA",2026:"CAR"}
NHL_COUNTRY = {"CAN": "Canada", "USA": "the USA", "SWE": "Sweden", "FIN": "Finland", "RUS": "Russia", "CZE": "Czechia", "SVK": "Slovakia",
    "DEU": "Germany", "CHE": "Switzerland", "DNK": "Denmark", "NOR": "Norway", "LVA": "Latvia", "AUT": "Austria", "UKR": "Ukraine",
    "BLR": "Belarus", "KAZ": "Kazakhstan", "FRA": "France", "SVN": "Slovenia", "GBR": "the UK", "POL": "Poland"}
NHL_REGION = {"ON": "Ontario", "QC": "Québec", "AB": "Alberta", "BC": "British Columbia", "SK": "Saskatchewan", "MB": "Manitoba",
    "NS": "Nova Scotia", "NB": "New Brunswick", "NL": "Newfoundland and Labrador", "PE": "Prince Edward Island", "MN": "Minnesota",
    "MA": "Massachusetts", "MI": "Michigan", "NY": "New York", "IL": "Illinois", "CA": "California", "PA": "Pennsylvania", "WI": "Wisconsin"}
NHL_POS = {"C": "Center", "L": "Left wing", "R": "Right wing", "D": "Defenseman"}

def load_nhl():
    D = f"{DATA}/nhl_NHL/data"
    bios = {r["playerId"]: r for r in rows(f"{D}/skaters_bios.csv")}
    seasons = collections.defaultdict(list)
    for r in rows(f"{D}/skaters_by_season_summary.csv"):
        seasons[r["playerId"]].append(r)
    out = {}
    for pid, rs in seasons.items():
        rs.sort(key=lambda r: r["seasonId"])
        if pid not in bios: continue
        b = bios[pid]
        path, tot, yrs = [], collections.Counter(), []
        has_pm = True
        for r in rs:
            y = int(r["seasonId"][4:])  # season end-year
            yrs.append(y)
            for abbr in r["teamAbbrevs"].split(","):
                t, c = nhl_team(abbr, y)
                add_stint(path, t, c, y)
                path[-1]["abbr"] = abbr
            for k in ["gamesPlayed", "goals", "assists", "points", "penaltyMinutes", "ppGoals", "shGoals", "gameWinningGoals", "shots"]:
                tot[k] += num(r[k]) or 0
            if r["plusMinus"] in ("", None): has_pm = False
            tot["plusMinus"] += num(r["plusMinus"]) or 0
        yrs = sorted(set(yrs))
        rings = 0
        for y in yrs:
            if y in NHL_CHAMPS:
                stints = [p for p in path if p["from"] <= y <= p["to"]]
                if stints and stints[-1].get("abbr") == NHL_CHAMPS[y]: rings += 1
        dy, dp, dr = num(b["draftYear"]), num(b["draftOverall"]), num(b["draftRound"])
        gp = tot["gamesPlayed"] or 1
        p = {
            "id": pid, "name": b["skaterFullName"], "from": yrs[0], "to": yrs[-1], "seasons": len(yrs), "path": path, "ambiguous": False,
            "pos": NHL_POS.get(b["positionCode"], b["positionCode"]), "role": "sk", "colleges": [],
            "draft": {"year": int(dy), "pick": int(dp), "round": int(dr), "team": ""} if dy and dp else None,
            "ht": int(num(b["height"])) if num(b["height"]) else None, "wt": int(num(b["weight"])) if num(b["weight"]) else None,
            "birth": {"country": NHL_COUNTRY.get(b["birthCountryCode"], b["birthCountryCode"]), "region": NHL_REGION.get(b["birthStateProvinceCode"], ""),
                      "city": b["birthCity"]},
            "hand": {"shoots": b["shootsCatches"]}, "honors": {}, "awards": [], "rings": rings, "hof": b["isInHallOfFameYn"] == "Y",
            "tot": dict(tot),
        }
        p["stats"] = {"gp": int(tot["gamesPlayed"]), "g": int(tot["goals"]), "a": int(tot["assists"]), "p": int(tot["points"]),
                      "pm": int(tot["plusMinus"]) if has_pm else None, "pim": int(tot["penaltyMinutes"]), "ppg": int(tot["ppGoals"]),
                      "shg": int(tot["shGoals"]), "gwg": int(tot["gameWinningGoals"]), "ppgame": round(tot["points"] / gp, 2)}
        p["fame"] = tot["points"] / 60 + tot["goals"] / 60 + tot["gamesPlayed"] / 150 + p["hof"] * 8 + rings * 1.5 + (3 if p["draft"] and p["draft"]["pick"] <= 3 else 0)
        out[pid] = p
    return out

# =====================================================================
# MLB  (Lahman database 1871-2025)
# =====================================================================
MLB_TWO = ("Red Sox", "White Sox", "Blue Jays", "Devil Rays")
def mlb_nick(full):
    full = full.replace(" of Anaheim", "")
    for n in MLB_TWO:
        if full.endswith(n): return n, full[: -len(n)].strip()
    if full == "Athletics": return "Athletics", "Sacramento"
    parts = full.split()
    return parts[-1], " ".join(parts[:-1])
MLB_COUNTRY = {"D.R.": "the Dominican Republic", "Venezuela": "Venezuela", "P.R.": "Puerto Rico", "Cuba": "Cuba", "Japan": "Japan",
    "Mexico": "Mexico", "CAN": "Canada", "Panama": "Panama", "Colombia": "Colombia", "Curacao": "Curaçao", "Nicaragua": "Nicaragua",
    "Australia": "Australia", "South Korea": "South Korea", "Netherlands": "the Netherlands", "Taiwan": "Taiwan", "USA": "the USA",
    "Aruba": "Aruba", "Germany": "Germany", "Bahamas": "the Bahamas", "Brazil": "Brazil"}
MLB_AWARDS = {"Most Valuable Player": "mvp", "Cy Young Award": "cy", "Rookie of the Year": "roy", "World Series MVP": "wsmvp",
    "Gold Glove": "gg", "Silver Slugger": "ss"}

def load_mlb():
    D = DATA
    tname = {(int(r["yearID"]), r["teamID"]): r["name"] for r in rows(f"{D}/mlb_Teams.csv")}
    champs = {int(r["yearID"]): r["teamID"] for r in rows(f"{D}/mlb_Teams.csv") if r["WSWin"] == "Y"}
    people = {r["playerID"]: r for r in rows(f"{D}/mlb_People.csv")}
    stints = collections.defaultdict(dict)   # pid -> (year, stint) -> team
    bat = collections.defaultdict(collections.Counter); pit = collections.defaultdict(collections.Counter)
    for r in rows(f"{D}/mlb_Batting.csv"):
        y = int(r["yearID"]); stints[r["playerID"]][(y, int(r["stint"]))] = r["teamID"]
        for k in ["G","AB","R","H","X2B","X3B","HR","RBI","SB","BB","HBP","SF","SO"]:
            bat[r["playerID"]][k] += num(r[k]) or 0
    for r in rows(f"{D}/mlb_Pitching.csv"):
        y = int(r["yearID"]); stints[r["playerID"]].setdefault((y, int(r["stint"])), r["teamID"])
        for k in ["W","L","G","GS","CG","SHO","SV","IPouts","H","ER","BB","SO"]:
            pit[r["playerID"]][k] += num(r[k]) or 0
    allstar = collections.Counter(r["playerID"] for r in rows(f"{D}/mlb_AllstarFull.csv"))
    awards = collections.defaultdict(list)
    for r in rows(f"{D}/mlb_AwardsPlayers.csv"):
        if r["awardID"] in MLB_AWARDS: awards[r["playerID"]].append((MLB_AWARDS[r["awardID"]], int(r["yearID"])))
    hof = {r["playerID"] for r in rows(f"{D}/mlb_HallOfFame.csv") if r["inducted"] == "Y" and r["category"] == "Player"}
    POSN = {"G_c": "Catcher", "G_1b": "First base", "G_2b": "Second base", "G_3b": "Third base", "G_ss": "Shortstop",
            "G_lf": "Outfield", "G_cf": "Outfield", "G_rf": "Outfield", "G_dh": "Designated hitter"}
    posg = collections.defaultdict(collections.Counter)
    for r in rows(f"{D}/mlb_Appearances.csv"):
        for k, lab in POSN.items():
            posg[r["playerID"]][lab] += num(r.get(k)) or 0
    out = {}
    for pid, st in stints.items():
        if pid not in people: continue
        pe = people[pid]
        keys = sorted(st)
        path = []
        for (y, s) in keys:
            t, c = mlb_nick(tname.get((y, st[(y, s)]), st[(y, s)]))
            add_stint(path, t, c, y)
            path[-1]["abbr"] = st[(y, s)]
        yrs = sorted({y for y, _ in keys})
        rings = 0
        for y in yrs:
            if y in champs:
                last = [st[k] for k in keys if k[0] == y][-1]
                if last == champs[y]: rings += 1
        b, pt = bat[pid], pit[pid]
        ip = pt["IPouts"] / 3
        role = "pit" if ip >= 300 and (b["AB"] < 2 * ip) else ("hit" if b["AB"] >= 300 else None)
        name = f'{pe["nameFirst"]} {pe["nameLast"]}'.strip()
        ht = num(pe["height"])
        p = {
            "id": pid, "name": name, "from": yrs[0], "to": yrs[-1], "seasons": len(yrs), "path": path, "ambiguous": False,
            "pos": ("Pitcher" if role == "pit" else (posg[pid].most_common(1)[0][0] if posg[pid] else "Position player")), "role": role, "colleges": [], "draft": None,
            "ht": int(ht) if ht else None, "wt": int(num(pe["weight"]) or 0) or None,
            "birth": {"country": MLB_COUNTRY.get(pe["birthCountry"], pe["birthCountry"]), "region": pe["birthState"], "city": pe["birthCity"]},
            "hand": {"bats": pe["bats"], "throws": pe["throws"]}, "honors": {"allstar": allstar[pid]}, "awards": awards[pid],
            "rings": rings, "hof": pid in hof, "tot": {"bat": dict(b), "pit": dict(pt)},
        }
        if role == "hit":
            ab, h = b["AB"] or 1, b["H"]
            tb = h + b["X2B"] + 2 * b["X3B"] + 3 * b["HR"]
            obp_d = b["AB"] + b["BB"] + b["HBP"] + b["SF"]
            p["stats"] = {"g": int(b["G"]), "avg": round(h / ab, 3), "hr": int(b["HR"]), "rbi": int(b["RBI"]), "h": int(h), "r": int(b["R"]),
                          "sb": int(b["SB"]), "bb": int(b["BB"]), "obp": round((h + b["BB"] + b["HBP"]) / obp_d, 3) if obp_d else None,
                          "slg": round(tb / ab, 3)}
        elif role == "pit":
            p["stats"] = {"w": int(pt["W"]), "l": int(pt["L"]), "era": round(pt["ER"] * 9 / ip, 2) if ip else None, "so": int(pt["SO"]),
                          "sv": int(pt["SV"]), "ip": int(round(ip)), "whip": round((pt["BB"] + pt["H"]) / ip, 2) if ip else None,
                          "g": int(pt["G"]), "gs": int(pt["GS"]), "cg": int(pt["CG"])}
        else:
            p["stats"] = None
        aw = collections.Counter(a for a, _ in awards[pid])
        p["fame"] = (allstar[pid] * 4 + (aw["mvp"] + aw["cy"]) * 6 + aw["roy"] * 3 + aw["gg"] * .7 + aw["ss"] * .7 + p["hof"] * 8 + rings * 1.2
                     + b["H"] / 250 + b["HR"] / 50 + pt["W"] / 15 + pt["SO"] / 250 + pt["SV"] / 40 + len(yrs) / 5)
        out[pid] = p
    return out
