"""Add more days to a published schedule without changing any existing day.

New Journeyman and Stat Line answers are the most famous players not used anywhere yet (daily or practice),
given the same easy (Mon-Wed) / medium (Thu-Sat) / hard (Sun) rhythm as the first year.
"""
import datetime, random, collections

EPOCH = datetime.date(2026, 11, 22)
WEEKDAY_LEVEL = {0: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2}

def levels(start, n):
    return [WEEKDAY_LEVEL[(EPOCH + datetime.timedelta(days=start + i)).weekday()] for i in range(n)]

def used_names(D):
    u = {e["n"] for e in D["journeyman"]} | {e["n"] for e in D["statline"]}
    pr = D.get("practice", {})
    for k in ("journeyman", "statline"):
        if k in pr: u.add(pr[k]["n"])
    return u

def schedule(players, lv, rng):
    """players sorted most famous first -> one per day, easier days get the more famous ones."""
    counts = collections.Counter(lv)
    buckets, i = {}, 0
    for L in (0, 1, 2):
        buckets[L] = players[i:i + counts[L]]; i += counts[L]
        rng.shuffle(buckets[L])
    return [buckets[L].pop() for L in lv]

def pick(cands, used, n, role_counts=None):
    out = []
    if role_counts:
        for role, k in role_counts.items():
            got = [p for p in cands if p["name"] not in used and p["role"] == role][:k]
            if len(got) < k: raise RuntimeError(f"only {len(got)} unused {role} players for {k} days")
            out += got
        out.sort(key=lambda p: p["fame"], reverse=True)
    else:
        out = [p for p in cands if p["name"] not in used][:n]
        if len(out) < n: raise RuntimeError(f"only {len(out)} unused players for {n} days")
    return out

def role_split(D, n):
    """Keep Stat Line's mix of roles (e.g. QB/RB/WR) in the new days."""
    c = collections.Counter(e.get("r") for e in D["statline"])
    if None in c: return None
    tot = sum(c.values()); out = {r: int(n * k / tot) for r, k in c.items()}
    for r, _ in c.most_common():
        if sum(out.values()) >= n: break
        out[r] += 1
    return out
