#!/usr/bin/env bash
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
NS=clab-3-tier-leaf-spine-dcgw

echo "==> Edge interfaces (Dot1q + labels + full spec)"
kubectl apply -f "$DIR/edge-interfaces-dot1q.yaml"

echo "==> VirtualNetworks (seven dedicated vnet-ms-* services)"
kubectl apply -f "$DIR/virtualnetworks.yaml"

echo "==> Policies"
kubectl apply -f "$DIR/association-policies.yaml"
python3 "$DIR/gen-microsegmentation-policies.py"
kubectl apply -f "$DIR/microsegmentation-policies.yaml"

echo "Done. Clients: python3 ../scripts/configure-client-ms-eth1.py --variant A --apply"
