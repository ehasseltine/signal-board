#!/usr/bin/env bash
# Pre-build script: syncs daily JSON from data/daily/ to public/data/daily/
# This prevents the recurring bug where Astro builds serve stale content
# because public/data/daily/ was not updated before the build.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DATA_DIR="$ROOT/data/daily"
PUBLIC_DIR="$ROOT/public/data/daily"

# Ensure latest.json exists
if [ ! -f "$DATA_DIR/latest.json" ]; then
  echo "ERROR: $DATA_DIR/latest.json does not exist."
  echo "The pipeline has not generated any data yet. Run the pipeline first."
  exit 1
fi

# Extract date from latest.json
DATE=$(python3 -c "import json; print(json.load(open('$DATA_DIR/latest.json'))['date'])" 2>/dev/null || echo "unknown")

if [ "$DATE" = "unknown" ]; then
  echo "ERROR: Could not read date from latest.json. File may be corrupted."
  exit 1
fi

# Ensure public directory exists
mkdir -p "$PUBLIC_DIR"

# Copy latest.json and the dated file
cp "$DATA_DIR/latest.json" "$PUBLIC_DIR/latest.json"
echo "Synced latest.json (date: $DATE) to public/data/daily/"

if [ -f "$DATA_DIR/$DATE.json" ]; then
  cp "$DATA_DIR/$DATE.json" "$PUBLIC_DIR/$DATE.json"
  echo "Synced $DATE.json to public/data/daily/"
fi

# Also sync any other dated files that exist in data/ but not in public/
for f in "$DATA_DIR"/20*.json; do
  [ -f "$f" ] || continue
  basename=$(basename "$f")
  if [ ! -f "$PUBLIC_DIR/$basename" ]; then
    cp "$f" "$PUBLIC_DIR/$basename"
    echo "Synced $basename to public/data/daily/"
  fi
done

echo "Pre-build sync complete."
