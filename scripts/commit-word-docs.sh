#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
git add .gitignore \
  docs/EDA-Microsegmentation.docx \
  docs/EDA-Microsegmentation-Test-Report.docx \
  docs/EDA-Microsegmentation.md \
  docs/EDA-Microsegmentation-Test-Report.md \
  scripts/generate-word-docs.sh
git rm -f 'docs/~$A-Microsegmentation.docx' 2>/dev/null || true
git commit -m 'Regenerate Word docs from Aug 2026 markdown; add pandoc generation script.'
git push origin main
git log -1 --oneline
