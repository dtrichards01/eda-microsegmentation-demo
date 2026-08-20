#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
git add \
  README.md \
  docs/EDA-Microsegmentation.md \
  docs/EDA-Microsegmentation.docx \
  docs/EDA-Microsegmentation-Test-Report.md \
  docs/EDA-Microsegmentation-Test-Report.docx \
  docs/VARIANT-SCOPE-LOCK.md \
  variants/README.md
git commit -m "$(cat <<'EOF'
Restructure MS doc §2 with EDA intro and per-variant sections.

Replace Variant-A-only architecture overview with EDA microsegmentation
intro (§2.1–2.2), lab topology (§2.3), and variants A–G (§2.4–2.10).
Generalise §3–§6, split §4 endpoints by variant, dedupe §12, fix §13/§14
numbering, and fix UTF-8 encoding. Sync README, variant catalog, Word docs.
EOF
)"
git push origin main
git log -1 --oneline
