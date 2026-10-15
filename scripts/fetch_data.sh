#!/usr/bin/env bash
# Fetch the assessment inputs at a pinned commit and verify checksums.
# The files are not committed (the source repo has no license).
set -euo pipefail
COMMIT=4b8c67246a659c26bd222079c5c7829d295acad9
BASE="https://raw.githubusercontent.com/future-research/candidate-assessment/${COMMIT}/data"
DEST="${1:-data}"
mkdir -p "$DEST"
while read -r sum name; do
  curl -fsSL "$BASE/$name" -o "$DEST/$name.tmp"
  echo "$sum  $DEST/$name.tmp" | sha256sum -c --quiet - || { rm -f "$DEST/$name.tmp"; echo "checksum mismatch: $name" >&2; exit 1; }
  mv "$DEST/$name.tmp" "$DEST/$name"
done <<'SUMS'
ffdcf6b3b51787d1f14b327ee9d31b9b1f8ee469eaa11068180f056ce5118798 exercises.json
c2e6373eaeb10c889d06e46b5ceb7a5f5a5df463d68198dc615d2ee9099675d2 member-context.json
SUMS
echo "data fetched at ${COMMIT:0:7}"
