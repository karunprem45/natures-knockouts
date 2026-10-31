#!/usr/bin/env bash
# usage: ./scripts/commit.sh <driver-initials> "<commit message>"
set -euo pipefail
DRIVER="$1"; shift
MSG="$*"
TRAILERS=""
AUTHOR=""
while IFS='|' read -r key name email; do
  [ -z "$key" ] && continue
  if [ "$key" = "$DRIVER" ]; then
    AUTHOR="$name <$email>"
  else
    TRAILERS="${TRAILERS}
Co-authored-by: $name <$email>"
  fi
done < .mob
[ -z "$AUTHOR" ] && { echo "unknown driver: $DRIVER"; exit 1; }
git add -A
git commit --author="$AUTHOR" -m "$MSG
${TRAILERS}"
