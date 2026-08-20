#!/usr/bin/env bash
set -euo pipefail
cd /home/clab/Projects/eda-mcp-client
git add docs/LLM_CONFIGURATION.md
git commit -m 'Document related lab projects and Qwen skill cross-links in LLM_CONFIGURATION.'
git push origin main
git log -1 --oneline
