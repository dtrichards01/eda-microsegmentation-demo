#!/usr/bin/env bash
# Regenerate Word docs from markdown sources (requires pandoc).
# Close open .docx files in Word before running — locked files block overwrite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="$ROOT/docs"

strip_pandoc_attrs() {
  sed 's/{width=[^}]*}//g'
}

generate_one() {
  local md="$1"
  local out="$2"
  local base
  base="$(basename "$out")"
  strip_pandoc_attrs < "$md" | pandoc -f markdown -t docx \
    --resource-path="$DOCS:$DOCS/diagrams" \
    -o "$out" || return 1
  echo "  OK $base ($(wc -c < "$out") bytes)"
}

echo "Generating Word docs from markdown ..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

strip_pandoc_attrs < "$DOCS/EDA-Microsegmentation.md" | pandoc -f markdown -t docx \
  --resource-path="$DOCS:$DOCS/diagrams" -o "$TMP/EDA-Microsegmentation.docx"
strip_pandoc_attrs < "$DOCS/EDA-Microsegmentation-Test-Report.md" | pandoc -f markdown -t docx \
  --resource-path="$DOCS:$DOCS/diagrams" -o "$TMP/EDA-Microsegmentation-Test-Report.docx"

for pair in \
  "EDA-Microsegmentation.docx" \
  "EDA-Microsegmentation-Test-Report.docx"; do
  if cp -f "$TMP/$pair" "$DOCS/$pair" 2>/dev/null; then
    echo "  OK $pair"
  else
    cp -f "$TMP/$pair" "$DOCS/${pair}.new"
    echo "  LOCKED — wrote ${pair}.new (close Word, then: mv docs/${pair}.new docs/$pair)"
  fi
done

echo "Done."
