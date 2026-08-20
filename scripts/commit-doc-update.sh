#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
git add docs/EDA-Microsegmentation.md docs/EDA-Microsegmentation-Test-Report.md
git commit -m "Update MS doc and test report with Aug 2026 Variant D/E validation results."
git push origin main
git log -1 --oneline
