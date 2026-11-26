import os as _os
HERE = _os.path.dirname(_os.path.abspath(__file__))
RAW = _os.environ.get("SHOOTAROUND_RAW", _os.path.join(HERE, "..", "raw-data"))
OUT = _os.path.join(HERE, "..")
# Era: "all" (default) writes {sport}.json; "modern" keeps only players whose career midpoint is MODERN_FROM or later and writes {sport}-modern.json
ERA = _os.environ.get("SHOOTAROUND_ERA", "all")
MODERN_FROM = 2010
SUFFIX = "" if ERA == "all" else "-" + ERA
"""Build {sport}.json (NFL, NHL, MLB): guess pool, 365 Journeyman, 365 Stat Line, 365 Knecht 4."""
import json, random, datetime, collections, sys
import sports, knecht, soccer

EPOCH = datetime.date(2026, 11, 22)
DAYS = 365
WEEKDAY_LEVEL = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2}
def recency(to):
    """Favour players today's fans know: full weight for recent careers, less for older ones."""
    return 1.0 if to >= 2016 else .85 if to >= 2010 else .7 if to >= 2004 else .55 if to >= 1998 else .42 if to >= 1992 else .3

day_levels = [WEEKDAY_LEVEL[(EPOCH + datetime.timedelta(days=i)).weekday()] for i in range(DAYS)]

def C(k, l, f, tol): return {"k": k, "l": l, "f": f, "tol": tol}
def ft_in(i): return f"{i // 12}'{i % 12}\""

# ---------------------------------------------------------------- sport configs
CFG = {
  "nfl": {
    "league": "NFL", "load": sports.load_nfl, "era_from": 1980, "retired_to": 2024, "active_to": 2025,
    "season": lambda y: str(y), "cup": "Super Bowl", "cups": "Super Bowls", "sl_quota": {"qb": 50, "rb": 90, "rec": 115, "def": 110},
    "roles": {
      "qb": {"label": "Quarterback", "hero": [C("yds","Pass yards","d0",0), C("td","Pass TD","d0",0), C("int_","INT","d0",0)],
             "row": [C("cmp","Cmp%","p1",0), C("att","Attempts","d0",0), C("ryds","Rush yds","d0",0), C("rtd","Rush TD","d0",0), C("g","Games","d0",0), C("st","Seasons as starter","d0",0)],
             "cols": [C("yds","Yds","d0",5000), C("td","TD","d0",40), C("int_","INT","d0",30), C("cmp","Cmp%","p1",.02), C("att","Att","d0",800),
                      C("ryds","Rush","d0",500), C("g","G","d0",30), C("st","Starts","d0",2)]},
      "rb": {"label": "Running back", "hero": [C("ryds","Rush yards","d0",0), C("rtd","Rush TD","d0",0), C("ypc","Yds/carry","d1",0)],
             "row": [C("ratt","Carries","d0",0), C("rec","Catches","d0",0), C("recyds","Rec yds","d0",0), C("rectd","Rec TD","d0",0), C("g","Games","d0",0), C("st","Seasons as starter","d0",0)],
             "cols": [C("ryds","Rush","d0",1500), C("rtd","TD","d0",15), C("ratt","Att","d0",300), C("ypc","YPC","d1",.3), C("rec","Rec","d0",75),
                      C("recyds","RecYd","d0",600), C("g","G","d0",30), C("st","Starts","d0",2)]},
      "rec": {"label": "Receiver / tight end", "hero": [C("rec","Catches","d0",0), C("recyds","Rec yards","d0",0), C("rectd","Rec TD","d0",0)],
             "row": [C("ypr","Yds/catch","d1",0), C("ryds","Rush yds","d0",0), C("g","Games","d0",0), C("st","Seasons as starter","d0",0)],
             "cols": [C("rec","Rec","d0",100), C("recyds","Yds","d0",1500), C("rectd","TD","d0",15), C("ypr","Y/R","d1",1.0),
                      C("g","G","d0",30), C("st","Starts","d0",2)]},
      "def": {"label": "Defender", "hero": [C("sk","Sacks","d1",0), C("ints","Interceptions","d0",0), C("g","Games","d0",0)],
             "row": [C("st","Seasons as starter","d0",0)],
             "cols": [C("sk","Sacks","d1",15), C("ints","INT","d0",8), C("g","G","d0",30), C("st","Starts","d0",2)]},
    },
    "colors": {"Bills":"#00338D","Dolphins":"#008E97","Patriots":"#002244","Jets":"#125740","Steelers":"#FFB612","Bengals":"#FB4F14","Browns":"#311D00",
      "Ravens":"#241773","Jaguars":"#006778","Colts":"#002C5F","Texans":"#03202F","Titans":"#4B92DB","Oilers":"#00A0E1","Chiefs":"#E31837","Broncos":"#FB4F14",
      "Chargers":"#0080C6","Raiders":"#A5ACAF","Seahawks":"#69BE28","Cowboys":"#003594","Giants":"#0B2265","Eagles":"#004C54","Washington":"#5A1414",
      "Commanders":"#5A1414","Bears":"#0B162A","Lions":"#0076B6","Packers":"#203731","Vikings":"#4F2683","Falcons":"#A71930","Panthers":"#0085CA",
      "Saints":"#D3BC8D","Buccaneers":"#D50A0A","49ers":"#AA0000","Rams":"#003594","Cardinals":"#97233F"},
  },
  "nhl": {
    "league": "NHL", "load": sports.load_nhl, "era_from": 1980, "retired_to": 2025, "active_to": 2026,
    "season": lambda y: f"{y-1}–{str(y)[2:]}", "cup": "Stanley Cup", "cups": "Stanley Cups",
    "roles": {"sk": {"label": "Skater", "hero": [C("g","Goals","d0",0), C("a","Assists","d0",0), C("p","Points","d0",0)],
              "row": [C("gp","Games","d0",0), C("pm","+/-","pm",0), C("pim","PIM","d0",0), C("ppg","PP goals","d0",0), C("shg","SH goals","d0",0), C("gwg","GW goals","d0",0), C("ppgame","Pts/game","d2",0)],
              "cols": [C("g","G","d0",50), C("a","A","d0",75), C("p","P","d0",100), C("pm","+/-","pm",40), C("pim","PIM","d0",200),
                       C("ppg","PPG","d0",25), C("gwg","GWG","d0",10), C("gp","GP","d0",150)]}},
    "colors": {"Ducks":"#F47A38","Mighty Ducks":"#00685E","Coyotes":"#8C2633","Thrashers":"#5C88DA","Flames":"#C8102E","Bruins":"#FFB81C","Sabres":"#003087",
      "Hurricanes":"#CE1126","Blackhawks":"#CF0A2C","Rockies":"#002F87","Avalanche":"#6F263D","Blue Jackets":"#002654","Stars":"#006847","North Stars":"#007A33",
      "Red Wings":"#CE1126","Oilers":"#FF4C00","Panthers":"#C8102E","Whalers":"#00843D","Kings":"#111111","Wild":"#154734","Canadiens":"#AF1E2D",
      "Predators":"#FFB81C","Devils":"#CE1126","Islanders":"#00539B","Rangers":"#0038A8","Senators":"#C2912C","Flyers":"#F74902","Penguins":"#FCB514",
      "Nordiques":"#1E4FA0","Sharks":"#006D75","Kraken":"#99D9D9","Blues":"#002F87","Lightning":"#002868","Maple Leafs":"#00205B","Canucks":"#00205B",
      "Golden Knights":"#B4975A","Capitals":"#C8102E","Jets":"#041E42","Mammoth":"#71AFE5","Hockey Club":"#71AFE5","Scouts":"#002F87","Barons":"#C8102E","Golden Seals":"#006B54"},
  },
  "mlb": {
    "league": "MLB", "load": sports.load_mlb, "era_from": 1975, "retired_to": 2024, "active_to": 2025,
    "season": lambda y: str(y), "cup": "World Series", "cups": "World Series titles",
    "roles": {
      "hit": {"label": "Hitter", "hero": [C("avg","Batting avg","p3",0), C("hr","Home runs","d0",0), C("rbi","RBI","d0",0)],
              "row": [C("h","Hits","d0",0), C("r","Runs","d0",0), C("sb","Steals","d0",0), C("bb","Walks","d0",0), C("obp","OBP","p3",0), C("slg","SLG","p3",0), C("g","Games","d0",0)],
              "cols": [C("avg","AVG","p3",.010), C("hr","HR","d0",40), C("rbi","RBI","d0",150), C("h","H","d0",250), C("sb","SB","d0",50),
                       C("obp","OBP","p3",.012), C("slg","SLG","p3",.025), C("g","G","d0",200)]},
      "pit": {"label": "Pitcher", "hero": [C("w","Wins","d0",0), C("era","ERA","d2",0), C("so","Strikeouts","d0",0)],
              "row": [C("l","Losses","d0",0), C("sv","Saves","d0",0), C("ip","Innings","d0",0), C("whip","WHIP","d2",0), C("g","Games","d0",0), C("gs","Starts","d0",0), C("cg","Complete games","d0",0)],
              "cols": [C("w","W","d0",25), C("l","L","d0",25), C("era","ERA","d2",.25), C("so","SO","d0",350), C("sv","SV","d0",50),
                       C("ip","IP","d0",400), C("whip","WHIP","d2",.08), C("g","G","d0",120)]},
    },
    "colors": {"Orioles":"#DF4601","Red Sox":"#BD3039","Yankees":"#0C2340","Rays":"#092C5C","Devil Rays":"#00A3AD","Blue Jays":"#134A8E","White Sox":"#27251F",
      "Guardians":"#E31937","Indians":"#E31937","Tigers":"#0C2340","Royals":"#004687","Twins":"#002B5C","Astros":"#EB6E1F","Angels":"#BA0021","Athletics":"#003831",
      "Mariners":"#005C5C","Rangers":"#003278","Braves":"#CE1141","Marlins":"#00A3E0","Mets":"#FF5910","Phillies":"#E81828","Nationals":"#AB0003","Expos":"#003087",
      "Cubs":"#0E3386","Reds":"#C6011F","Brewers":"#12284B","Pirates":"#FDB827","Cardinals":"#C41E3A","Diamondbacks":"#A71930","Rockies":"#33006F",
      "Dodgers":"#005A9C","Padres":"#2F241D","Giants":"#FD5A1E"},
  },
}

SOCCER_ROLE = lambda lab: {"label": lab, "hero": [C("gl","League goals","d0",0), C("ast","Assists","d0",0), C("g","League games","d0",0)],
    "row": [C("min","Minutes","d0",0), C("gpg","Goals per 90","d2",0), C("yc","Yellow cards","d0",0), C("rc","Red cards","d0",0), C("caps","Caps","d0",0), C("ig","Int'l goals","d0",0)],
    "cols": [C("gl","G","d0",25), C("ast","A","d0",20), C("g","GP","d0",60), C("min","Min","d0",5000), C("gpg","G/90","d2",.1),
             C("yc","YC","d0",12), C("caps","Caps","d0",15)]}
CFG["soccer"] = {
    "league": "Soccer", "load": soccer.load_soccer, "era_from": 2012, "retired_to": 2024, "active_to": 2025,
    "season": soccer.season_label, "cup": "", "cups": "", "sl_quota": {"att": 160, "mid": 120, "def": 85},
    "roles": {"att": SOCCER_ROLE("Forward"), "mid": SOCCER_ROLE("Midfielder"), "def": SOCCER_ROLE("Defender")},
    "colors": {"Arsenal": "#EF0107", "Chelsea": "#034694", "Liverpool": "#C8102E", "Man City": "#6CABDD", "Man Utd": "#DA291C", "Tottenham": "#132257",
      "Everton": "#003399", "Newcastle": "#241F20", "Aston Villa": "#670E36", "West Ham": "#7A263A", "Leicester": "#003090", "Real Madrid": "#FEBE10",
      "Barcelona": "#A50044", "Atlético Madrid": "#CB3524", "Sevilla": "#D81920", "Valencia": "#EE3524", "Villarreal": "#FFE667", "Betis": "#00954C",
      "Juventus": "#1A1A1A", "AC Milan": "#FB090B", "Inter Milan": "#0068A8", "Napoli": "#12A0D7", "Roma": "#8E1F2F", "Lazio": "#87D8F7",
      "Fiorentina": "#482E92", "Atalanta": "#1E71B8", "Bayern": "#DC052D", "Dortmund": "#FDE100", "Leverkusen": "#E32221", "RB Leipzig": "#DD0741",
      "Schalke 04": "#004D9D", "Wolfsburg": "#65B32E", "PSG": "#004170", "Marseille": "#2FAEE0", "Lyon": "#DA0812", "Monaco": "#E7161A",
      "Lille": "#E01E13", "Inter Miami": "#F7B5CD", "LA Galaxy": "#00245D", "LAFC": "#C39E6D", "Al-Nassr": "#FCD116", "Al-Hilal": "#005BAC",
      "Ajax": "#D2122E", "Porto": "#00428C", "Benfica": "#E83030", "Celtic": "#018749", "Galatasaray": "#A90432"},
}

MIN_G = {"nfl": 48, "nhl": 300, "mlb": 400, "soccer": 80}

def schedule(pool, rng):
    need = [day_levels.count(l) for l in range(3)]
    buckets, i = [], 0
    for n in need:
        b = pool[i:i+n]; rng.shuffle(b); buckets.append(b); i += n
    return [buckets[l].pop() for l in day_levels]

def season_span(cfg, p):
    if p["to"] >= cfg["active_to"]: return f"{cfg['season'](p['from'])} to now"
    return f"{cfg['season'](p['from'])} to {cfg['season'](p['to'])}"
def draft_label(p, sport):
    d = p["draft"]
    if not d: return "Undrafted" if sport != "mlb" else "—"
    t = f" ({d['team']})" if d.get("team") else ""
    return f"{d['year']} · Round {d['round']}, pick {d['pick']}{t}"
def birthplace(p):
    b = p["birth"]; parts = [b.get("city"), b.get("region")] if b.get("country") in ("the USA", "Canada") else [b.get("city"), b.get("country")]
    return ", ".join(x for x in parts if x) or "—"

def hints(sport, cfg, p):
    if sport == "soccer":
        born = datetime.date.fromisoformat(p["dob"]).strftime("%B %-d, %Y") if p["dob"] else "—"   # date only: nationality is its own clue
        foot = (p["hand"].get("foot") or "").capitalize()
        caps = p["honors"]["caps"]
        return {"born": born, "pos": p["pos"], "nat": p["nat"] or "—",
                "foot": " · ".join(x for x in [f"{foot} foot" if foot else "", f"{p['ht'] / 100:.2f} m" if p["ht"] else ""] if x) or "—",
                "caps": "Not recorded" if caps is None else f"{caps} cap{'s' if caps != 1 else ''} · {p['honors']['ig']} goal{'s' if p['honors']['ig'] != 1 else ''}",
                "leagues": " · ".join(soccer.BIG[l] for l in soccer.BIG if l in p["leagues"]) or "—"}
    h = {"seasons": season_span(cfg, p), "pos": p["pos"], "draft": draft_label(p, sport), "cups": f"{p['rings']}"}
    if sport == "nfl":
        h["honors"] = f"{p['honors']['probowl']} Pro Bowl{'s' if p['honors']['probowl'] != 1 else ''} · {p['honors']['allpro']} All-Pro"
        h["origin"] = " · ".join(p["colleges"]) or "—"
    elif sport == "nhl":
        h["honors"] = f"{p['rings']} Stanley Cup{'s' if p['rings'] != 1 else ''}"
        h["origin"] = birthplace(p)
    else:
        h["honors"] = f"{p['honors']['allstar']} All-Star · {p['rings']} title{'s' if p['rings'] != 1 else ''}"
        h["origin"] = birthplace(p)
        h["hand"] = f"Bats {p['hand'].get('bats') or '?'} · Throws {p['hand'].get('throws') or '?'}"
    return h

HINT_SPECS = {
    "soccer": {"jm": [("born","Born"),("pos","Position"),("nat","Nationality"),("foot","Foot · Height"),("caps","International caps"),("initials","Initials")],
               "sl": [("born","Born"),("pos","Position"),("nat","Nationality"),("leagues","Big leagues played in"),("caps","International caps")]},
    "nfl": {"jm": [("seasons","Seasons"),("pos","Position"),("draft","Draft"),("origin","College"),("initials","Initials")],
            "sl": [("seasons","Career"),("pos","Position"),("honors","Pro Bowls · All-Pro"),("draft","Draft"),("origin","College")]},
    "nhl": {"jm": [("seasons","Seasons"),("pos","Position"),("draft","Draft"),("origin","Birthplace"),("initials","Initials")],
            "sl": [("seasons","Career"),("pos","Position"),("honors","Stanley Cups"),("draft","Draft"),("origin","Birthplace")]},
    "mlb": {"jm": [("seasons","Seasons"),("pos","Position"),("hand","Bats · Throws"),("origin","Birthplace"),("initials","Initials")],
            "sl": [("seasons","Career"),("pos","Position"),("honors","All-Star picks · Titles"),("hand","Bats · Throws"),("origin","Birthplace")]},
}

# ---------------------------------------------------------------- Knecht 4 categories
HINT = {"team": "A franchise they all played for", "college": "Where they played before the pros", "draft": "Draft day",
        "award": "End-of-season hardware", "trophy": "Trophy case", "milestone": "A big career number", "height": "Measure them",
        "loyal": "Never changed jerseys", "name": "Look at the names, not the players", "birth": "Where they were born",
        "pos": "What they did on the field", "hand": "Which side", "league": "Where they played", "nation": "Their passport"}
WEIGHT = {"team": 0.0, "pos": 0.4, "birth": 0.9, "award": 1.0, "trophy": 1.2, "college": 1.5, "draft": 1.6, "height": 2.0,
          "milestone": 2.2, "loyal": 2.0, "hand": 2.4, "name": 3.2, "league": 1.0, "nation": 0.9}
TYPE_W = {"team": 3.0, "college": 2.0, "birth": 2.0, "award": 1.4, "name": 1.3, "draft": 1.1, "milestone": 1.2,
          "trophy": 0.9, "height": 0.7, "loyal": 0.5, "pos": 0.8, "hand": 0.6, "league": 1.5, "nation": 1.8}
STATIC = {"college", "draft", "height", "name", "birth", "pos", "hand", "team", "award", "nation", "league"}

def catalog(sport, cfg, P, era_ids, retired):
    cats = []
    def add(cid, typ, label, members):
        m = set(members) & era_ids
        if len(m) >= 6: cats.append({"id": cid, "type": typ, "label": label, "hint": HINT[typ], "m": m})
    E = {pid: P[pid] for pid in era_ids}
    if sport == "soccer":
        teams = collections.defaultdict(set); nat = collections.defaultdict(set); lg = collections.defaultdict(set)
        first = collections.defaultdict(set); last = collections.defaultdict(set)
        for pid, p in E.items():
            for s_ in p["path"]: teams[s_["t"]].add(pid)
            if p["nat"]: nat[p["nat"]].add(pid)
            for l in p["leagues"]: lg[l].add(pid)
            parts = p["name"].split()
            if len(parts) >= 2: first[parts[0]].add(pid); last[parts[-1]].add(pid)
        for t, m in teams.items(): add("team:" + t, "team", f"Played for {t}", m)
        for c, m in nat.items(): add("nat:" + c, "nation", f"Nationality: {c}", m)
        T = soccer.tables(); comp_name = {"GB1": "the Premier League", "ES1": "La Liga", "IT1": "Serie A", "L1": "the Bundesliga", "FR1": "Ligue 1",
            "MLS1": "MLS", "SA1": "the Saudi Pro League", "NL1": "the Eredivisie", "PO1": "Liga Portugal", "TR1": "the Turkish Süper Lig",
            "SC1": "the Scottish Premiership", "BE1": "the Belgian Pro League", "RU1": "the Russian Premier League", "GR1": "the Greek Super League"}
        for l, m in lg.items():
            if l in comp_name: add("lg:" + l, "league", f"Played in {comp_name[l]}", m)
        for n, m in first.items(): add("first:" + n, "name", f"First name {n}", m)
        for n, m in last.items(): add("last:" + n, "name", f"Last name {n}", m)
        posg = {"Goalkeepers": ("Goalkeeper",), "Centre-backs": ("Centre-Back",), "Full-backs": ("Left-Back", "Right-Back"),
                "Defensive midfielders": ("Defensive Midfield",), "Wingers": ("Left Winger", "Right Winger"), "Centre-forwards": ("Centre-Forward",)}
        for lab, ps in posg.items(): add("pos:" + lab, "pos", lab, [pid for pid, p in E.items() if p["pos"] in ps])
        add("foot:l", "hand", "Left-footed", [pid for pid, p in E.items() if p["hand"].get("foot") == "left"])
        add("ht:tall", "height", "Listed at 1.93 m or taller", [pid for pid, p in E.items() if p["ht"] and p["ht"] >= 193])
        add("ht:short", "height", "Listed at 1.70 m or shorter", [pid for pid, p in E.items() if p["ht"] and p["ht"] <= 170])
        add("caps:100", "trophy", "100+ international caps", [pid for pid, p in E.items() if (p["honors"]["caps"] or 0) >= 100])
        add("ms:gl100", "milestone", "100+ league goals since 2012–13", [pid for pid, p in E.items() if p["tot"]["gl"] >= 100])
        add("ms:ast60", "milestone", "60+ league assists since 2012–13", [pid for pid, p in E.items() if p["tot"]["ast"] >= 60])
        # soccer pools are dominated by a few leagues and countries; very big groups would make every grid
        # have an accidental fifth group, so leave them out
        return [c for c in cats if len(c["m"]) <= 0.12 * len(era_ids)]
    teams = collections.defaultdict(set)
    for pid, p in E.items():
        for s in p["path"]: teams[s["t"]].add(pid)
    for t, m in teams.items():
        add("team:" + t, "team", f"Played for {'the ' if t not in ('Washington',) else ''}{t}", m)
    first = collections.defaultdict(set); last = collections.defaultdict(set)
    for pid, p in E.items():
        parts = p["name"].replace(" Jr.", "").replace(" Sr.", "").replace(" III", "").replace(" II", "").split()
        if len(parts) >= 2: first[parts[0]].add(pid); last[parts[-1]].add(pid)
    for n, m in first.items(): add("first:" + n, "name", f"First name {n}", m)
    for n, m in last.items(): add("last:" + n, "name", f"Last name {n}", m)
    add("loyal", "loyal", "10+ seasons, all with one team", [pid for pid in retired if len(E[pid]["path"]) == 1 and E[pid]["seasons"] >= 10])
    add("rings2", "trophy", f"Won 2 or more {cfg['cups']}", [pid for pid in retired if E[pid]["rings"] >= 2])
    T = lambda p, *ks: sum((p["stats"] or {}).get(k) or 0 for k in ks)
    if sport == "nfl":
        cols = collections.defaultdict(set)
        for pid, p in E.items():
            for c in p["colleges"]: cols[c].add(pid)
        for c, m in cols.items(): add("college:" + c, "college", f"Played college ball at {c}", m)
        add("draft:1", "draft", "No. 1 overall picks", [pid for pid, p in E.items() if p["draft"]["pick"] == 1])
        add("draft:2", "draft", "No. 2 overall picks", [pid for pid, p in E.items() if p["draft"]["pick"] == 2])
        add("draft:late", "draft", "Drafted in round 5 or later", [pid for pid, p in E.items() if p["draft"]["round"] >= 5])
        add("pos:qb", "pos", "Quarterbacks", [pid for pid, p in E.items() if p["pos"] == "Quarterback"])
        add("pos:te", "pos", "Tight ends", [pid for pid, p in E.items() if p["pos"] == "Tight end"])
        add("trophy:pb10", "trophy", "10 or more Pro Bowls", [pid for pid, p in E.items() if p["honors"]["probowl"] >= 10])
        add("trophy:ap5", "trophy", "5 or more first-team All-Pro picks", [pid for pid, p in E.items() if p["honors"]["allpro"] >= 5])
        t = lambda p, k: p["tot"].get(k, 0)
        for k, n, lab in [("pass_yards", 40000, "40,000+ career passing yards"), ("rush_yards", 10000, "10,000+ career rushing yards"),
                          ("rec_yards", 10000, "10,000+ career receiving yards"), ("def_sacks", 100, "100+ career sacks"), ("def_ints", 45, "45+ career interceptions")]:
            add("ms:" + k, "milestone", lab, [pid for pid, p in E.items() if t(p, k) >= n])
        add("ht:tall", "height", "Listed at 6'6\" or taller", [pid for pid, p in E.items() if p["ht"] and p["ht"] >= 78])
        add("ht:short", "height", "Listed at 5'9\" or shorter", [pid for pid, p in E.items() if p["ht"] and p["ht"] <= 69])
    elif sport == "nhl":
        cty = collections.defaultdict(set); reg = collections.defaultdict(set)
        for pid, p in E.items():
            if p["birth"]["country"] != "Canada": cty[p["birth"]["country"]].add(pid)
            if p["birth"]["region"] and p["birth"]["country"] == "Canada": reg[p["birth"]["region"]].add(pid)
        for c, m in cty.items():
            if c and len(c) > 3: add("birth:" + c, "birth", f"Born in {c}", m)
        for r_, m in reg.items(): add("region:" + r_, "birth", f"Born in {r_}", m)
        add("draft:1", "draft", "No. 1 overall picks", [pid for pid, p in E.items() if p["draft"] and p["draft"]["pick"] == 1])
        add("draft:un", "draft", "Went undrafted", [pid for pid, p in E.items() if not p["draft"] and p["from"] >= 1986])
        add("draft:late", "draft", "Drafted in round 5 or later", [pid for pid, p in E.items() if p["draft"] and p["draft"]["round"] >= 5])
        add("pos:d", "pos", "Defensemen", [pid for pid, p in E.items() if p["pos"] == "Defenseman"])
        for k, n, lab in [("g", 500, "500+ career goals"), ("p", 1000, "1,000+ career points"), ("gp", 1500, "1,500+ games played"),
                          ("pim", 2500, "2,500+ penalty minutes"), ("a", 800, "800+ career assists")]:
            add("ms:" + k, "milestone", lab, [pid for pid, p in E.items() if T(p, k) >= n])
        add("ht:tall", "height", "Listed at 6'5\" or taller", [pid for pid, p in E.items() if p["ht"] and p["ht"] >= 77])
        add("ht:short", "height", "Listed at 5'9\" or shorter", [pid for pid, p in E.items() if p["ht"] and p["ht"] <= 69])
    else:
        cty = collections.defaultdict(set)
        for pid, p in E.items():
            if p["birth"]["country"] and p["birth"]["country"] != "the USA": cty[p["birth"]["country"]].add(pid)
        for c, m in cty.items(): add("birth:" + c, "birth", f"Born in {c}", m)
        st = collections.defaultdict(set)
        for pid, p in E.items():
            if p["birth"]["country"] == "the USA" and p["birth"]["region"]: st[p["birth"]["region"]].add(pid)
        US = {"CA": "California", "TX": "Texas", "FL": "Florida", "NY": "New York", "PA": "Pennsylvania", "OH": "Ohio", "IL": "Illinois", "GA": "Georgia", "NC": "North Carolina", "LA": "Louisiana", "MI": "Michigan", "AL": "Alabama"}
        for code, full in US.items(): add("state:" + code, "birth", f"Born in {full}", st[code])
        names = {"mvp": "Won MVP", "cy": "Won the Cy Young", "roy": "Won Rookie of the Year", "wsmvp": "Won World Series MVP"}
        for a, lab in names.items():
            add("award:" + a, "award", lab, [pid for pid, p in E.items() if any(x[0] == a for x in p["awards"])])
        add("award:gg5", "award", "5 or more Gold Gloves", [pid for pid, p in E.items() if sum(1 for x in p["awards"] if x[0] == "gg") >= 5])
        add("trophy:as10", "trophy", "10 or more All-Star selections", [pid for pid, p in E.items() if p["honors"]["allstar"] >= 10])
        b = lambda p, k: p["tot"]["bat"].get(k, 0); q = lambda p, k: p["tot"]["pit"].get(k, 0)
        for key, fn, n, lab in [("hr", b, 400, "400+ career home runs"), ("h", b, 2500, "2,500+ career hits"), ("sb", b, 400, "400+ career stolen bases"),
                                ("w", q, 200, "200+ career wins"), ("so", q, 2500, "2,500+ career strikeouts (pitching)"), ("sv", q, 300, "300+ career saves")]:
            KEY = {"hr": "HR", "h": "H", "sb": "SB", "w": "W", "so": "SO", "sv": "SV"}[key]
            add("ms:" + key, "milestone", lab, [pid for pid, p in E.items() if fn(p, KEY) >= n])
        add("hand:sw", "hand", "Switch hitters", [pid for pid, p in E.items() if p["hand"].get("bats") == "B"])
        add("hand:lhp", "hand", "Left-handed pitchers", [pid for pid, p in E.items() if p["role"] == "pit" and p["hand"].get("throws") == "L"])
        add("pos:c", "pos", "Catchers", [pid for pid, p in E.items() if p["pos"] == "Catcher"])
        add("pos:ss", "pos", "Shortstops", [pid for pid, p in E.items() if p["pos"] == "Shortstop"])
        add("ht:tall", "height", "Listed at 6'7\" or taller", [pid for pid, p in E.items() if p["ht"] and p["ht"] >= 79])
        add("ht:short", "height", "Listed at 5'8\" or shorter", [pid for pid, p in E.items() if p["ht"] and p["ht"] <= 68])
    return cats

# ---------------------------------------------------------------- build
def build(sport):
    if _os.path.exists(_os.path.join(OUT, f"{sport}{SUFFIX}.json")) and "--force" not in sys.argv:
        sys.exit(f"{sport}{SUFFIX}.json already exists. Published puzzles are frozen: rebuilding would change every player's puzzles.\n"
                 "Only use --force before launch, or to start a brand-new schedule on purpose.")
    cfg = CFG[sport]
    rng = random.Random(f"{sport}-2026")
    P = cfg["load"]()
    dup = {n for n, k in collections.Counter(p["name"] for p in P.values() if p["from"] >= cfg["era_from"] - 10).items() if k > 1}
    for p in P.values(): p["fame"] = p.get("fame0", p["fame"]); p["fame0"] = p["fame"]; p["fame"] = p["fame0"] * recency(p["to"])
    if ERA == "modern":
        P = {k: v for k, v in P.items() if (v["from"] + v["to"]) / 2 >= MODERN_FROM}
    era = [p for p in P.values() if p["from"] >= cfg["era_from"] and p["name"] not in dup and p["stats"] is not None and p["role"]]
    era.sort(key=lambda p: p["fame"], reverse=True)
    retired = [p for p in era if p["to"] <= cfg["retired_to"]]

    answers = [p for p in era if (p["stats"].get("gp" if sport == "nhl" else "g") or 0) >= MIN_G[sport]]
    jm_pool = [p for p in answers if len(p["path"]) >= 3 and not p["ambiguous"]]
    pool = era[:2200]
    ids = {p["id"] for p in pool}
    pool += [p for p in answers[:1200] + jm_pool[:DAYS] if p["id"] not in ids and not ids.add(p["id"])]
    players_out = [{"n": p["name"], "r": p["role"], "t": list(dict.fromkeys(s["t"] for s in p["path"])), "s": p["stats"]} for p in pool]

    if cfg.get("sl_quota"):
        sl_pick = []
        for role, n in cfg["sl_quota"].items():
            sl_pick += [p for p in answers if p["role"] == role][:n]
        sl_pick.sort(key=lambda p: p["fame"], reverse=True)
    else:
        sl_pick = answers[:DAYS]
    sl_days = schedule(sl_pick, rng)
    sl_out = [{"n": p["name"], "r": p["role"], "lvl": day_levels[i], "h": hints(sport, cfg, p)} for i, p in enumerate(sl_days)]

    jm_days = schedule(jm_pool[:DAYS], rng)
    jm_out = [{"n": p["name"], "lvl": day_levels[i], "path": [{"t": s["t"], "c": s["c"], **({"l": 1} if s.get("loan") else {})} for s in p["path"]], "h": hints(sport, cfg, p)}
              for i, p in enumerate(jm_days)]

    era_ids = {p["id"] for p in era[:1600]}
    retired_ids = {p["id"] for p in retired} & era_ids
    cats = catalog(sport, cfg, P, era_ids, retired_ids)
    k4_out, rep = knecht.generate(P, lambda p: p["fame"], day_levels, DAYS, cats=cats, era=list(era_ids), active_to=cfg["active_to"], sizes=(240, 400, 580),
                                  static=STATIC, weight=WEIGHT, type_w=TYPE_W, seed={"nfl": 11, "nhl": 22, "mlb": 33, "soccer": 44}[sport])
    spec = {
        "roles": cfg["roles"],
        "jm_hints": [{"key": k, "label": l, **({"wide": True} if k == "initials" else {})} for k, l in HINT_SPECS[sport]["jm"]],
        "sl_hints": [{"key": k, "label": l, **({"wide": True} if i == 4 else {})} for i, (k, l) in enumerate(HINT_SPECS[sport]["sl"])],
    }
    data = {"sport": sport, "era": ERA, "league": cfg["league"], "built": datetime.date.today().isoformat(), "epoch": EPOCH.isoformat(),
            "levels": ["Easy", "Medium", "Hard"], "colors": cfg["colors"], "spec": spec,
            "players": players_out, "journeyman": jm_out, "statline": sl_out, "knecht": k4_out}
    out = _os.path.join(OUT, f"{sport}{SUFFIX}.json")
    if _os.path.exists(out) and "--force" not in sys.argv:
        sys.exit(f"{sport}{SUFFIX}.json already exists. Published puzzles are frozen: rebuilding would change every player's puzzles.\n"
                 "Only use --force before launch, or to start a brand-new schedule on purpose.")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(sport, "players", len(players_out), "jm pool", len(jm_pool), "sl pool", len(retired), "| jm", len(jm_out), "sl", len(sl_out), "k4", len(k4_out))
    print(" ", rep, "| categories", len(cats), collections.Counter(c["type"] for c in cats))
    return data

def practice(sport):
    """One extra puzzle per game, used only for the Practice round. It is a medium-level pick that is not any day's
    answer: we take a medium player from late in the year for practice and give that day the best unused player.
    Also refreshes soccer's Born clue. Only the puzzle files' 'practice' block and those few entries change."""
    path = _os.path.join(OUT, f"{sport}{SUFFIX}.json")
    D = json.load(open(path, encoding="utf-8"))
    cfg = CFG[sport]
    P = cfg["load"]()
    dup = {n for n, k in collections.Counter(p["name"] for p in P.values() if p["from"] >= cfg["era_from"] - 10).items() if k > 1}
    for p in P.values(): p["fame"] = p.get("fame0", p["fame"]); p["fame0"] = p["fame"]; p["fame"] = p["fame0"] * recency(p["to"])
    if ERA == "modern":
        P = {k: v for k, v in P.items() if (v["from"] + v["to"]) / 2 >= MODERN_FROM}
    era = [p for p in P.values() if p["from"] >= cfg["era_from"] and p["name"] not in dup and p["stats"] is not None and p["role"]]
    era.sort(key=lambda p: p["fame"], reverse=True)
    answers = [p for p in era if (p["stats"].get("gp" if sport == "nhl" else "g") or 0) >= MIN_G[sport]]
    jm_pool = [p for p in answers if len(p["path"]) >= 3 and not p["ambiguous"]]
    by_name = {p["name"]: p for p in era}
    jm_entry = lambda p, lvl: {"n": p["name"], "lvl": lvl, "path": [{"t": s_["t"], "c": s_["c"], **({"l": 1} if s_.get("loan") else {})} for s_ in p["path"]], "h": hints(sport, cfg, p)}
    sl_entry = lambda p, lvl: {"n": p["name"], "r": p["role"], "lvl": lvl, "h": hints(sport, cfg, p)}
    n_easy, n_med = day_levels.count(0), day_levels.count(1)
    used = {e["n"] for e in D["journeyman"]} | {e["n"] for e in D["statline"]} | {e["n"] for e in D.get("practice", {}).get("journeyman", [])[:0]}
    out = {}
    def swap(kind, ranked, entry, same_role, repl_src=None):
        nonlocal used
        listing = D[kind]
        pos = {e["n"]: i for i, e in enumerate(listing)}
        band = [p for p in ranked[n_easy:n_easy + n_med] if pos.get(p["name"], -1) >= 60]
        ranked = repl_src or ranked
        pick = band[len(band) // 2]
        idx = pos[pick["name"]]
        repl = next(p for p in ranked if p["name"] not in used and (not same_role or p["role"] == pick["role"]))
        listing[idx] = entry(repl, listing[idx]["lvl"]); used |= {repl["name"]}
        out[kind] = entry(pick, 1)
        print(f"  {kind}: practice {pick['name']} (was day {idx + 1}); day {idx + 1} is now {repl['name']}")
    swap("journeyman", jm_pool[:DAYS] + jm_pool[DAYS:], jm_entry, False)
    if cfg.get("sl_quota"):                                 # same list the daily Stat Line was scheduled from
        sl_pick = []
        for role, n in cfg["sl_quota"].items(): sl_pick += [p for p in answers if p["role"] == role][:n]
        sl_pick.sort(key=lambda p: p["fame"], reverse=True)
        sl_rank = sorted([p for p in answers if p["role"] in cfg["sl_quota"]], key=lambda p: p["fame"], reverse=True)
    else:
        sl_pick = sl_rank = answers
    swap("statline", sl_pick, sl_entry, bool(cfg.get("sl_quota")), sl_rank)
    # Links: one medium grid from a different seed; none of its groups may match a daily group
    era_ids = {p["id"] for p in era[:1600]}
    retired_ids = {p["id"] for p in era if p["to"] <= cfg["retired_to"]} & era_ids
    cats = catalog(sport, cfg, P, era_ids, retired_ids)
    daily_groups = {frozenset(g["p"]) for z in D["knecht"] for g in z["groups"]}
    for seed in range(9000, 9100):
        k4, _ = knecht.generate(P, lambda p: p["fame"], [1], 1, cats=cats, era=list(era_ids), active_to=cfg["active_to"], sizes=(240, 400, 580),
                                static=STATIC, weight=WEIGHT, type_w=TYPE_W, seed=seed)
        if not any(frozenset(g["p"]) in daily_groups for g in k4[0]["groups"]): break
    out["knecht"] = k4[0]
    print("  links:", [g["label"] for g in k4[0]["groups"]])
    if sport == "soccer":                                   # refresh the Born clue everywhere
        for e in D["journeyman"] + D["statline"]:
            if e["n"] in by_name: e["h"]["born"] = hints(sport, cfg, by_name[e["n"]])["born"]
    D["practice"] = out
    with open(path, "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__" and "--practice" in sys.argv:
    for sp in [a for a in sys.argv[1:] if not a.startswith("--")]:
        print(sp); practice(sp)
    sys.exit(0)

if __name__ == "__main__":
    for s in [a for a in sys.argv[1:] if not a.startswith("--")]:
        build(s)
