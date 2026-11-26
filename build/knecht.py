"""Knecht 4 puzzle generator with a uniqueness solver."""
import random, collections
from common import per_game, nickname

STATIC = {"college", "draft", "height", "name", "team", "award"}  # facts that can't change for active players
WEIGHT = {"team": 0.0, "award": 1.0, "trophy": 1.2, "college": 1.5, "draft": 1.6, "height": 2.0,
          "milestone": 2.2, "loyal": 2.0, "name": 3.2}
HINT = {"team": "A franchise they all played for", "college": "Where they played before the NBA",
        "draft": "Draft night", "award": "End-of-season hardware", "trophy": "Trophy case",
        "milestone": "A big career number", "height": "Measure them", "loyal": "Never changed jerseys",
        "name": "Look at the names, not the players"}

def build_catalog(P):
    cats = []
    def add(cid, typ, label, members):
        cats.append({"id": cid, "type": typ, "label": label, "hint": HINT[typ], "m": set(members)})
    era = {pid: p for pid, p in P.items() if p["from"] >= 1980}
    retired = {pid for pid, p in era.items() if p["to"] <= 2025}

    teams = collections.defaultdict(set)
    for pid, p in era.items():
        for s in p["path"]:
            teams[nickname(s["full"])].add(pid)
    for t, m in teams.items():
        add("team:" + t, "team", f"Played for the {t}", m)

    cols = collections.defaultdict(set)
    for pid, p in era.items():
        for c in p["colleges"]:
            cols[c].add(pid)
    for c, m in cols.items():
        add("college:" + c, "college", f"Played college ball at {c}", m)

    add("draft:1", "draft", "No. 1 overall picks", [pid for pid, p in era.items() if p["draft"] and p["draft"]["pick"] == 1])
    add("draft:2", "draft", "No. 2 overall picks", [pid for pid, p in era.items() if p["draft"] and p["draft"]["pick"] == 2])
    add("draft:r2", "draft", "Second-round picks", [pid for pid, p in era.items() if p["draft"] and p["draft"]["year"] >= 1989 and p["draft"]["pick"] >= 31])
    add("draft:un", "draft", "Went undrafted", [pid for pid, p in era.items() if not p["draft"] and p["from"] >= 1990])

    names = {"mvp": "Won MVP", "dpoy": "Won Defensive Player of the Year", "roy": "Won Rookie of the Year",
             "smoy": "Won Sixth Man of the Year", "mip": "Won Most Improved Player"}
    for a, label in names.items():
        add("award:" + a, "award", label, [pid for pid, p in era.items() if any(x[0] == a for x in p["awards"])])
    add("trophy:as10", "trophy", "10 or more All-Star selections", [pid for pid, p in era.items() if p["allstar"] >= 10])
    add("trophy:rings3", "trophy", "Won 3 or more championships", [pid for pid in retired if era[pid]["rings"] >= 3])

    t = lambda pid, k: era[pid]["tot"].get(k, 0)
    for k, n, label in [("pts", 20000, "20,000+ career points"), ("trb", 10000, "10,000+ career rebounds"),
                        ("ast", 6000, "6,000+ career assists"), ("stl", 1500, "1,500+ career steals"),
                        ("blk", 1500, "1,500+ career blocks"), ("x3p", 2000, "2,000+ career three-pointers")]:
        add(f"milestone:{k}", "milestone", label, [pid for pid in era if t(pid, k) >= n])

    add("height:7", "height", "Listed at 7 feet or taller", [pid for pid, p in era.items() if p["ht"] and p["ht"] >= 84])
    add("height:6", "height", "Listed at 6 feet or shorter", [pid for pid, p in era.items() if p["ht"] and p["ht"] <= 72])
    add("loyal", "loyal", "10+ seasons, all with one team", [pid for pid in retired if len(era[pid]["path"]) == 1 and era[pid]["seasons"] >= 10])

    first = collections.defaultdict(set); last = collections.defaultdict(set)
    for pid, p in era.items():
        parts = p["name"].replace(" Jr.", "").replace(" III", "").replace(" II", "").split()
        if len(parts) >= 2:
            first[parts[0]].add(pid); last[parts[-1]].add(pid)
    for n, m in first.items():
        add("first:" + n, "name", f"First name {n}", m)
    for n, m in last.items():
        add("last:" + n, "name", f"Last name {n}", m)
    return cats

def count_solutions(players, cats, limit=2):
    """players: list of 16 pids; cats: 4 category dicts. Count ways to split into 4 groups of 4, one per category."""
    options = [[i for i, c in enumerate(cats) if p in c["m"]] for p in players]
    if any(not o for o in options): return 0
    order = sorted(range(16), key=lambda i: len(options[i]))
    cap = [4, 4, 4, 4]; found = 0
    def rec(k):
        nonlocal found
        if found >= limit: return
        if k == 16: found += 1; return
        for c in options[order[k]]:
            if cap[c]:
                cap[c] -= 1; rec(k + 1); cap[c] += 1
    rec(0)
    return found

def generate(P, fame, day_levels, days, cats=None, era=None, active_to=2026, static=None, weight=None, type_w=None, seed=4444, sizes=(320, 520, 760)):
    """NBA defaults; other sports pass their own catalog (cats), eligible player ids (era) and settings."""
    rng = random.Random(seed)
    STATIC_ = static or STATIC
    WEIGHT_ = weight or WEIGHT
    if cats is None:
        cats = build_catalog(P)
    if era is None:
        dup = {n for n, k in collections.Counter(p["name"] for p in P.values() if p["from"] >= 1980).items() if k > 1}
        era = [pid for pid, p in P.items() if p["from"] >= 1980 and per_game(p)["g"] >= 200 and p["name"] not in dup]
    era = sorted(era, key=lambda pid: fame(P[pid]), reverse=True)
    rank = {pid: i for i, pid in enumerate(era)}
    universe = [set(era[:sizes[0]]), set(era[:sizes[1]]), set(era[:sizes[2]])]
    active = {pid for pid in era if P[pid]["to"] >= active_to}

    pcats = collections.defaultdict(list)                 # player -> indexes of the links they fit
    for ci, c in enumerate(cats):
        for pid in c["m"]: pcats[pid].append(ci)
    use_p = collections.Counter(); use_c = collections.Counter(); last_c = {}
    seen_groups = set()
    out, tries_total, herr_total = [], 0, 0

    cap = [10]
    def eligible(c, U):
        pool = c["m"] & U
        if c["type"] not in STATIC_:
            pool -= active
        return [pid for pid in pool if use_p[pid] < cap[0]]

    TYPE_W = type_w or {"team": 3.0, "college": 2.0, "award": 1.6, "name": 1.3, "draft": 1.1, "milestone": 1.1,
              "trophy": 0.8, "height": 0.7, "loyal": 0.5}
    for d in range(days):
        lvl = day_levels[d]; U = universe[lvl]
        def make_usable(cool):
            u = collections.defaultdict(list)
            for c in cats:
                if d - last_c.get(c["id"], -99) >= cool and len(eligible(c, U)) >= 6:
                    u[c["type"]].append(c)
            return u
        cap[0] = 10
        usable = make_usable(10)
        tries_day = 0; why = collections.Counter()
        while True:
            tries_total += 1; tries_day += 1
            relax = tries_day > 1500
            if tries_day == 5000:   # escalate 1: shorter cooldown
                cap[0] = 12; usable = make_usable(3)
            if tries_day == 12000:  # escalate 2: borrow the next level's bigger player pool
                U = universe[min(lvl + 1, 2)] if U is not universe[2] else set(era); usable = make_usable(3)
            if tries_day == 25000:
                print("stuck day", d, dict(why), flush=True)
                cap[0] = 99; usable = make_usable(0)
            pick, types = [], collections.Counter()
            tlist = [t for t in TYPE_W if usable[t]]
            if len(tlist) < 3:   # this level's player pool is used up: borrow from the next level
                if len(U) < len(universe[2]): U = universe[min(lvl + 1, 2)]
                else: U = set(era); cap[0] = max(cap[0] + 2, 14)
                usable = make_usable(0); continue
            for _ in range(12):
                t = rng.choices(tlist, weights=[TYPE_W[x] for x in tlist])[0]
                if types[t] >= (2 if t == "team" else 1): continue
                opts = [c for c in usable[t] if c not in pick]
                if not opts: continue
                low = min(use_c[c["id"]] for c in opts)
                c = rng.choice([c for c in opts if use_c[c["id"]] <= low + 1])
                pick.append(c); types[t] += 1
                if len(pick) == 4: break
            if len(pick) < 4 or len(types) < (2 if tries_day > 5000 else 3): why["pick"] += 1; continue
            chosen, ok = [], True
            taken = set(); other = collections.Counter(); pick_ids = {id(c) for c in pick}
            for c in pick:
                # only players who fit this link and none of the other three, so every link fits exactly its own four
                el = [pid for pid in eligible(c, U) if pid not in taken and not any(pid in c2["m"] for c2 in pick if c2 is not c)]
                w = {pid: 1.0 / (1 + use_p[pid] * 1.5) * (1.0 / (1 + rank[pid] / 150)) for pid in el}
                grp = []
                while len(grp) < 4 and el:
                    pid = rng.choices(el, weights=[w[x] for x in el])[0]
                    el.remove(pid)
                    # skip anyone who would give some other link a fourth player on the board
                    if any(other[ci] >= 3 for ci in pcats.get(pid, ()) if id(cats[ci]) not in pick_ids): continue
                    grp.append(pid)
                    for ci in pcats.get(pid, ()): other[ci] += 1
                if len(grp) < 4: ok = False; break
                chosen.append(sorted(grp)); taken |= set(grp)
            if not ok: why["members"] += 1; continue
            flat = [pid for g in chosen for pid in g]
            if any(frozenset(g) in seen_groups for g in chosen): continue
            if count_solutions(flat, pick) != 1: why["unique"] += 1; continue
            # no accidental fifth group: no other category may hold 5+ of the 16
            fs = set(flat)
            # strict: every group's link fits exactly its four players and nobody else on the board (no decoys),
            # and no other link covers four or more of the sixteen (no look-alike fifth group)
            if any(len(c["m"] & fs) != 4 for c in pick): why["strict"] += 1; continue
            if any(len(c["m"] & fs) >= 4 for c in cats if c not in pick): why["fifth"] += 1; continue
            herrings = 0
            break
        herr_total += herrings
        if d % 20 == 0 or tries_day > 2000: print("day", d, "lvl", lvl, "tries", tries_day, flush=True)
        order = sorted(range(4), key=lambda i: WEIGHT_.get(pick[i]["type"], 1.5) + rng.random() * 0.8)
        groups = []
        for tier, i in enumerate(order):
            c = pick[i]
            groups.append({"tier": tier, "type": c["type"], "label": c["label"], "hint": c["hint"],
                           "p": sorted((P[pid]["name"] for pid in chosen[i]), key=lambda n: n.split()[-1])})
            use_c[c["id"]] += 1; last_c[c["id"]] = d
            seen_groups.add(frozenset(chosen[i]))
            for pid in chosen[i]: use_p[pid] += 1
        out.append({"lvl": lvl, "groups": groups})
    report = (f"k4: {len(out)} puzzles, {len(out)*4} groups, attempts {tries_total}, avg decoys {herr_total/len(out):.2f}, "
              f"distinct categories used {len(use_c)}, distinct players {len(use_p)}, max player uses {max(use_p.values())}")
    return out, report
