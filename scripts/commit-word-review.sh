#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
bash scripts/generate-word-docs.sh
git add \
  README.md \
  docs/EDA-Microsegmentation.md \
  docs/EDA-Microsegmentation.docx \
  docs/EDA-Microsegmentation-Test-Report.md \
  docs/EDA-Microsegmentation-Test-Report.docx \
  docs/L3-IRB-RFC9135.md \
  scripts/extract-word-comments.py
git commit -m 'Apply Word review comments to MS documentation.'
git push origin main
git log -1 --oneline
