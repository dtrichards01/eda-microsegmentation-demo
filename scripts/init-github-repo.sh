#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
git commit -m "Initial commit: EDA microsegmentation demo with scoped Variant D/E manifests and rollout docs."
gh repo create eda-microsegmentation-demo --public --description "Nokia EDA microsegmentation demo (variants A-E) for clab-3-tier-leaf-spine-dcgw" --source=. --remote=origin --push
echo "REPO_URL=https://github.com/dtrichards01/eda-microsegmentation-demo"
