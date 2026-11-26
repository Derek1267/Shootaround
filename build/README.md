# Shootaround: developer notes

How the site is put together and how the puzzle files are made. Players don't need any of this.

## Run your own copy

The site is plain HTML, CSS and JavaScript with JSON data files. There's no server or build step needed to play.

**Try it locally.** Run a small web server from the repo's root folder; opening `index.html` directly won't load the puzzles.

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

**Host it on GitHub Pages:**
1. Fork this repo.
2. Go to **Settings → Pages** and set **Source** to your main branch, root folder.
3. In `index.html`, update the two settings near the top of the script, plus the `og:` links in the `<head>`, to your username and repo:
   ```js
   const GITHUB_REPO = "your-name/Shootaround";                  // where "Report a problem" opens issues
   const SITE_URL = "https://your-name.github.io/Shootaround/";  // link added to shared results
   ```
4. Make sure **Issues** are switched on (Settings → General → Features).

### Files

| File | What it is |
|---|---|
| `index.html` | The whole site: layout, styles and game logic |
| `nba.json`, `nfl.json`, `nhl.json`, `mlb.json`, `soccer.json` | 365 days of Journeyman, Links and Stat Line per sport, plus the player lists for guessing |
| `hl-nba.json`, `hl-nfl.json`, `hl-nhl.json`, `hl-mlb.json`, `hl-soccer.json` | 365 days of Higher or Lower per sport (5 questions a day) |
| `*-modern.json` | The same four kinds of file for the Modern era |
| `logo.svg` | The logo, also used as the browser tab icon |
| `og.png` | Preview image for shared links |
| `icon-180.png` | Home-screen icon when someone adds the site to their phone |
| `docs/` | The summary graphic used in the README |
| `build/` | Scripts that generate and check the puzzle files |

## The puzzle schedule is fixed

Day 1 is **22 November 2026**. Each day's puzzles are stored in the JSON files, so everyone gets the same puzzle. **Don't regenerate the files once people are playing:** that would change every day's puzzle and reset everyone's progress for the day. The build scripts refuse to overwrite existing files unless you pass `--force`. After day 365 the puzzles loop back to day 1.

## Rebuilding the data

```bash
pip install -r build/requirements.txt
cd build
bash get_data.sh                     # downloads raw data into ../raw-data (~300 MB)
python3 build.py --force             # NBA: Journeyman, Links, Stat Line (~10 min)
python3 build_sport.py nfl nhl mlb soccer --force
python3 hl_build.py nba nfl nhl mlb soccer --force   # Higher or Lower
python3 verify.py && python3 verify_sport.py nfl nhl mlb && python3 verify_hl.py
```

**Modern era files.** The same scripts build the Modern set (players whose career midpoint is 2010 or later) when `SHOOTAROUND_ERA=modern` is set. They write `nba-modern.json`, `hl-nba-modern.json` and so on, and never touch the All-time files:

```bash
export SHOOTAROUND_ERA=modern
python3 build.py --force && python3 build_sport.py nfl nhl mlb --force
python3 hl_build.py nba nfl nhl mlb --force
python3 verify.py && python3 verify_sport.py nfl nhl mlb soccer && python3 verify_hl.py
```

The checkers make sure that:
- every Links player really fits their group, and each grid has exactly one solution;
- no group repeats;
- Journeyman routes match the data;
- Higher or Lower values match the career and season numbers, with no ties.

## How the puzzles are made

Every puzzle is generated from real data rather than written by hand:
- Players are ranked by a fame score (All-Star or Pro Bowl picks, awards, career totals, Hall of Fame), weighted toward recent careers.
- Early-week puzzles use the best-known players, and later days dig deeper.
- Links grids are built from categories like teams, colleges, draft picks, awards, milestones, birthplaces, heights and names. A solver then checks that only one grouping works, and rejects grids where an unintended fifth group sneaks in.

## Known limits

- Soccer league numbers start in 2012–13, where the Transfermarkt dataset starts, so soccer has one puzzle set instead of Modern and All-time. Career paths come from transfer records and include loan spells; players whose transfer history has gaps are kept out of Journeyman.

- NFL covers drafted players since 1980, so undrafted players (for example Kurt Warner or Tony Romo) aren't included.
- NHL covers skaters only (no goalies) and has no award-based groups.
- Active players' numbers are a snapshot from the last data build and don't update during the season.
- Title counts credit a player when they finished that season on the championship team.
