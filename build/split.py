"""Split each puzzle set into a small core file plus 50-day chunks, so the site only downloads
today's block on first visit (the full files stay as the source of truth for the build tools).

  data/<set>.core.json   spec, players, practice rounds, day count
  data/<set>.d<k>.json   days k*50 .. k*50+49 of Journey, Quads, Digits and Flip

Run after any build:  python3 split.py
"""
import json, os, glob
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, ".."); OUT = os.path.join(ROOT, "data")
CHUNK = 50
os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*.json")): os.remove(f)
sets = [os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, "*.json")) if not os.path.basename(p).startswith("hl-")]
dump = lambda obj, name: json.dump(obj, open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
for s in sorted(sets):
    D = json.load(open(os.path.join(ROOT, f"{s}.json"), encoding="utf-8"))
    H = json.load(open(os.path.join(ROOT, f"hl-{s}.json"), encoding="utf-8"))
    n = len(D["journeyman"])
    assert len(D["statline"]) == n == len(D["knecht"]) == len(H["days"]), s
    core = {k: v for k, v in D.items() if k not in ("journeyman", "statline", "knecht")}
    core.update(n=n, chunk=CHUNK, hlPractice=H.get("practice"))
    dump(core, f"{s}.core.json")
    for k in range(0, n, CHUNK):
        dump({"start": k, "journeyman": D["journeyman"][k:k + CHUNK], "statline": D["statline"][k:k + CHUNK],
              "knecht": D["knecht"][k:k + CHUNK], "hl": H["days"][k:k + CHUNK]}, f"{s}.d{k // CHUNK}.json")
    print(f"{s}: core {os.path.getsize(os.path.join(OUT, s + '.core.json')) // 1024} KB, {-(-n // CHUNK)} chunks")
