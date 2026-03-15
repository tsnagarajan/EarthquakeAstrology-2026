#!/usr/bin/env bash
# Download Swiss Ephemeris data files required for 1800-2100 planetary computation
# Run once from project root: bash data/ephe/download_ephe.sh
# Or make executable first: chmod +x data/ephe/download_ephe.sh
set -euo pipefail

EPHE_DIR="$(dirname "$0")"
# Files moved from AstroDienst FTP to GitHub (as of 2024)
# See: https://www.astro.com/ftp/swisseph/ for current download locations
BASE_URL="https://raw.githubusercontent.com/aloistr/swisseph/master/ephe"

# Required files for 1900-2026 planetary positions
FILES=(
    "sepl_18.se1"   # planets 1800-2400
    "semo_18.se1"   # moon 1800-2400
    "seas_18.se1"   # asteroids (Chiron) 1800-2400
    "sefstars.txt"  # fixed stars
)

for f in "${FILES[@]}"; do
    if [ -f "$EPHE_DIR/$f" ]; then
        echo "Already present: $f"
    else
        echo "Downloading $f ..."
        curl -fL -o "$EPHE_DIR/$f" "$BASE_URL/$f"
    fi
done

echo "Swiss Ephemeris files ready in $EPHE_DIR"
