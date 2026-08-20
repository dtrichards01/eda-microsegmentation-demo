#!/usr/bin/env bash
# Push all commits to GitHub. Run from WSL when off corporate proxy (Zscaler blocks git-receive-pack).
set -euo pipefail
cd "$(dirname "$0")/.."
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Update MS variant descriptions and complete repo contents."
fi
gh auth setup-git
gh repo edit dtrichards01/eda-microsegmentation-demo \
  --description "Nokia EDA microsegmentation demo variants A-G for clab-3-tier-leaf-spine-dcgw"
git push -u origin main
echo "OK: https://github.com/dtrichards01/eda-microsegmentation-demo"
