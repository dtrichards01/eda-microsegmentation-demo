#!/usr/bin/env bash
# Deploy all MS variant VirtualNetworks + policies to WSL EDA cluster.
set -eu
NS=clab-3-tier-leaf-spine-dcgw
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> GroupTags (gateway, remote)"
kubectl apply -f "$DIR/grouptags-extra.yaml"

echo "==> VirtualNetworks (seven dedicated vnet-ms-* services)"
kubectl apply -f "$DIR/virtualnetworks.yaml"

echo "==> Association policies"
kubectl apply -f "$DIR/association-policies.yaml"

echo "==> MicroSegmentation policies"
python3 "$DIR/gen-microsegmentation-policies.py"
kubectl apply -f "$DIR/microsegmentation-policies.yaml"

echo ""
echo "Done. Apply edge Dot1q: bash apply-dot1q.sh — see README.md"
kubectl get virtualnetwork -n "$NS" -o custom-columns=NAME:.metadata.name,VARIANT:.metadata.labels.eda\\.nokia\\.com/ms-variant 2>/dev/null | grep -E 'vnet-ms|NAME' | head -10
