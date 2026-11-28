"""Stamp a new build number into index.html and version.json.
Run this before every push so installed home-screen apps notice the update and reload themselves."""
import json, re, time, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
v = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
page = root / "index.html"
s, n = re.subn(r'const BUILD = "[^"]*";', f'const BUILD = "{v}";', page.read_text())
assert n == 1, "BUILD line not found in index.html"
page.write_text(s)
(root / "version.json").write_text(json.dumps({"v": v}) + "\n")
print("build", v)
