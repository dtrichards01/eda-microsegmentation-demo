#!/bin/bash
# VLAN-aware client eth1 setup for EDA microsegmentation Dot1q demos.
# Bind into clab linux nodes (see clab/clab-ms-client-exec.snippet).
#
# Usage:
#   client-config-ms-vlan.sh <vlan-id> <ip/prefix> <gateway> [static-route]
#
# Example (variant A / vnet-ms-vlan):
#   bash /client-config-ms-vlan.sh 101 172.16.101.1/24 172.16.101.254 172.16.0.0/16

set -euo pipefail

VID="${1:?vlan id}"
IP="${2:?ip/prefix}"
GW="${3:?gateway}"
EXTRA_ROUTE="${4:-}"

PARENT=eth1
VIF="${PARENT}.${VID}"

echo "MS VLAN client config: vlan=${VID} ip=${IP} gw=${GW}"

ip link set "$PARENT" up 2>/dev/null || true

# Remove other MS demo VLAN subifs
for v in 101 102 103 104 106 107 108; do
  ip link del "${PARENT}.${v}" 2>/dev/null || true
done

ip link add link "$PARENT" name "$VIF" type vlan id "$VID" 2>/dev/null || true
ip link set "$VIF" up
ip addr flush dev "$VIF" 2>/dev/null || true
ip addr add "$IP" dev "$VIF"

while ip route show default 2>/dev/null | grep -q '^default'; do
  ip route del default 2>/dev/null || break
done

if [ -n "$GW" ]; then
  ip route add default via "$GW" dev "$VIF"
fi

if [ -n "$EXTRA_ROUTE" ]; then
  ip route add "$EXTRA_ROUTE" via "$GW" dev "$VIF" 2>/dev/null || true
fi

echo "iface: $VIF"
ip -o addr show dev "$VIF"
ip route show default | head -1
