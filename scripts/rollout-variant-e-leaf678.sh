#!/usr/bin/env bash
set -euo pipefail
NS=clab-3-tier-leaf-spine-dcgw
DEMO=/mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo
OUT=$DEMO/docs/tmp/variant-e-leaf678-$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"

echo "=== pre-check ===" | tee "$OUT/SUMMARY.md"
kubectl get virtualnetwork vnet-ms-static -n "$NS" 2>&1 | tee -a "$OUT/SUMMARY.md" || true

echo "=== apply labels + variant E ===" | tee -a "$OUT/SUMMARY.md"
kubectl apply -f "$DEMO/variants/labels-vnet-ms-static.yaml" | tee -a "$OUT/SUMMARY.md"
kubectl apply -f "$DEMO/variants/_variant-e-leaf678-apply.yaml" | tee -a "$OUT/SUMMARY.md"
sleep 15

echo "=== scope ===" | tee -a "$OUT/SUMMARY.md"
kubectl get virtualnetwork vnet-ms-static -n "$NS" -o jsonpath='nodes={.status.nodes} numNodes={.status.numNodes} state={.status.operationalState}{"\n"}' | tee -a "$OUT/SUMMARY.md"

configure_client() {
  local c=$1 ip=$2
  docker exec "$c" bash -c "
    ip link set eth1 up
    ip link del eth1.90 2>/dev/null || true
    ip link add link eth1 name eth1.90 type vlan id 90 2>/dev/null || true
    ip link set eth1.90 up
    ip addr flush dev eth1.90
    ip addr add $ip dev eth1.90
    ip route replace default via 172.16.90.254 dev eth1.90
  "
}

echo "=== configure clients ===" | tee -a "$OUT/SUMMARY.md"
configure_client client6 172.16.90.6/24 && echo OK client6 | tee -a "$OUT/SUMMARY.md"
configure_client client7 172.16.90.7/24 && echo OK client7 | tee -a "$OUT/SUMMARY.md"
configure_client client8 172.16.90.8/24 && echo OK client8 | tee -a "$OUT/SUMMARY.md"

run_ping() {
  local from=$1 dst=$2 label=$3
  echo "--- $label ($from -> $dst)" | tee -a "$OUT/SUMMARY.md"
  docker exec "$from" ping -I eth1.90 -c 3 -W 2 "$dst" 2>&1 | tee -a "$OUT/SUMMARY.md" || true
}

echo "=== ping matrix ===" | tee -a "$OUT/SUMMARY.md"
run_ping client8 172.16.90.6 "red->blue ALLOW"
run_ping client8 172.16.90.7 "red->green DENY"
run_ping client6 172.16.90.7 "blue->green ALLOW"
run_ping client6 172.16.90.8 "blue->red ALLOW"
run_ping client7 172.16.90.6 "green->blue ALLOW"
run_ping client7 172.16.90.8 "green->red DENY"
run_ping client6 172.16.90.254 "blue->gateway ALLOW"
run_ping client8 172.16.91.1 "red->static-prefix DENY"

cp "$DEMO/variants/_variant-e-leaf678-apply.yaml" "$OUT/variant-e-leaf678-apply.yaml"
echo "Artifacts: $OUT" | tee -a "$OUT/SUMMARY.md"
