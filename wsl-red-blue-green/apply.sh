#!/usr/bin/env bash
set -euo pipefail
NS=clab-3-tier-leaf-spine-dcgw
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Applying interface labels (red/blue/green on vnet-1) ==="
kubectl apply -f "$DIR/interface-labels.yaml"

echo "=== Green GroupTag ==="
kubectl apply -f "$DIR/grouptag-green.yaml"

echo "=== Association policy ==="
kubectl apply -f "$DIR/association-policy.yaml"

echo "=== Remove legacy drop policies ==="
kubectl -n "$NS" delete microsegmentationpolicy red-to-blue blue-to-red --ignore-not-found

echo "=== Microsegmentation policy red-blue-green ==="
kubectl apply -f "$DIR/microsegmentation-policy.yaml"

echo "=== Label vnet-1 for policy binding ==="
kubectl -n "$NS" label virtualnetwork vnet-1 eda.nokia.com/gbp=red-blue-green --overwrite

echo "=== Status ==="
kubectl -n "$NS" get grouptag,associationpolicy,microsegmentationpolicy
kubectl -n "$NS" get virtualnetwork vnet-1 -o jsonpath='{.metadata.labels}{"\n"}'
