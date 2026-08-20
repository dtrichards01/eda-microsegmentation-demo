#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
git add scripts/sync-cursor-skills.sh scripts/commit-doc-restructure.sh scripts/commit-doc-update.sh scripts/commit-word-docs.sh scripts/commit-word-review.sh scripts/commit-mcp-llm-doc.sh 2>/dev/null || true
git add scripts/sync-cursor-skills.sh
for f in scripts/commit-*.sh; do [ -f "$f" ] && git add "$f"; done
git commit -m 'Add doc maintenance and skill sync helper scripts.'
git push origin main
git log -1 --oneline
