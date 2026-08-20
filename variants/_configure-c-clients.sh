#!/bin/bash
set -e
configure() {
  local c=$1 vid=$2 ip=$3 gw=$4
  docker exec "$c" bash -s "$vid" "$ip" "$gw" <<'INNER'
vid=$1; ip=$2; gw=$3
ip link set eth1 up 2>/dev/null || true
VIF=eth1.$vid
ip link add link eth1 name "$VIF" type vlan id "$vid" 2>/dev/null || true
ip link set "$VIF" up
ip addr flush dev "$VIF" 2>/dev/null || true
ip addr add "$ip" dev "$VIF"
while ip route show default 2>/dev/null | grep -q '^default'; do ip route del default 2>/dev/null || break; done
ip route add default via "$gw" dev "$VIF"
ip -o addr show dev "$VIF"
ip route show default | head -1
INNER
}
configure client5 80 172.16.80.10/24 172.16.80.1
configure client6 81 172.16.81.10/24 172.16.81.1
configure client7 82 172.16.82.10/24 172.16.82.1
echo DONE

