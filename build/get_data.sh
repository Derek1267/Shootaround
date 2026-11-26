#!/usr/bin/env bash
# Downloads the raw data the build scripts use into ../raw-data (about 300 MB).
# Run from the build/ folder:  bash get_data.sh
set -euo pipefail
RAW="${SHOOTAROUND_RAW:-$(cd "$(dirname "$0")/.." && pwd)/raw-data}"
mkdir -p "$RAW" && cd "$RAW"

# NBA: Basketball-Reference datasets
[ -d bball-reference-datasets ] || git clone --depth 1 https://github.com/sumitrodatta/bball-reference-datasets.git

# NHL: skater stats and bios scraped from NHL.com
[ -d nhl_NHL ] || git clone --depth 1 https://github.com/natashk/NHL.git nhl_NHL

# MLB: Lahman Baseball Database (R package data, converted to CSV below)
[ -d Lahman ] || git clone --depth 1 https://github.com/cdalzell/Lahman.git
python3 - <<'PY'
import pyreadr
for t in ["People", "Batting", "Pitching", "Appearances", "AwardsPlayers", "AllstarFull", "Teams", "HallOfFame"]:
    df = list(pyreadr.read_r(f"Lahman/data/{t}.RData").values())[0]
    df.to_csv(f"mlb_{t}.csv", index=False)
    print("MLB", t, df.shape)
PY

# NFL: nflverse draft picks + season rosters 1980-2025
mkdir -p nfl
curl -sSL -o nfl/draft_picks.csv https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv
for y in $(seq 1980 2025); do
  [ -s "nfl/roster_$y.csv" ] || curl -sSL -o "nfl/roster_$y.csv" "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_$y.csv"
done
# Soccer: Transfermarkt tables from github.com/dcaribou/transfermarkt-datasets (CC0)
mkdir -p soccer
for t in players appearances games clubs competitions transfers; do
  [ -s "soccer/$t.csv.gz" ] || curl -sSL -o "soccer/$t.csv.gz" "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/$t.csv.gz"
done
echo "Raw data ready in $RAW"
