#!/usr/bin/env bash
# Sync Cursor skills from Windows profile to WSL home (and reverse optional).
set -euo pipefail
WIN=/mnt/c/Users/darrenri/.cursor/skills
WSL=/home/clab/.cursor/skills
mkdir -p "$WSL"
for d in eda eda-mcp eda-dci eda-branch eda-alarm-watch; do
  if [ -d "$WIN/$d" ]; then
    mkdir -p "$WSL/$d"
    cp -a "$WIN/$d/." "$WSL/$d/"
    echo "  synced $d"
  fi
done
echo "Done: $WSL"
