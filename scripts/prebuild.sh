#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# PREBUILD DATA SYNC
# ─────────────────────────────────────────────────────────────────────────────
#
# DATA FLOW (single source of truth):
#
#   Pipeline (GitHub Actions)
#     → writes to: data/daily/{date}.json + data/daily/latest.json   [CANONICAL]
#     → prebuild.sh copies to: public/data/daily/                    [build input]
#     → Astro reads from: public/data/daily/ at build time
#     → Astro outputs to: docs/                                      [deployed]
#
# WHY THIS EXISTS:
#   Astro reads data from public/ during the build. If public/data/daily/ is
#   stale, the build will render yesterday's content even if data/daily/ has
#   today's data. This script ensures the build always uses the latest pipeline
#   output.
#
# PATCHING RULE:
#   If you need to patch JSON data (fix a field, add a key), ALWAYS patch the
#   canonical file in data/daily/ FIRST, then run `npm run build`. The prebuild
#   step will copy your patched file into public/data/daily/ automatically.
#   Never patch public/data/daily/ or docs/data/daily/ directly — those files
#   will be overwritten.
#
# ─────────────────────────────────────────────────────────────────────────────

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

# Safety check: warn if public/ files are newer than data/ files
# (indicates someone patched the wrong location)
if [ -f "$PUBLIC_DIR/latest.json" ]; then
  if [ "$PUBLIC_DIR/latest.json" -nt "$DATA_DIR/latest.json" ]; then
    echo "⚠ WARNING: public/data/daily/latest.json was newer than data/daily/latest.json"
    echo "  This suggests a manual patch was applied to the wrong location."
    echo "  The canonical source (data/daily/) has been copied over it."
  fi
fi

echo "Pre-build sync complete."
