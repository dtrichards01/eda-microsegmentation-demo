#!/bin/bash
# Move the DCI clients' eth1 IPv4 address and routes onto eth1.<vlan> (Talos gate 1), or back.
# Run on k0r4 right after the gate 1 transaction commits (or after its rollback).
#   dci-clients-to-vlan.sh check | apply | rollback
set -u
MODE=${1:-check}

# client  vlan  address          default gateway (empty = none)
CLIENTS="
client-1 101 172.16.101.1/24 172.16.101.254
client-2 101 172.16.101.2/24 172.16.101.254
client-3 103 172.16.105.3/24 -
client-4 105 172.16.151.1/24 172.16.151.254
client-5 102 172.16.201.1/24 172.16.201.254
client-6 102 172.16.201.2/24 172.16.201.254
client-7 104 172.16.105.1/24 172.16.105.254
client-8 104 172.16.105.2/24 172.16.105.254
"

echo "$CLIENTS" | while read -r c vlan addr gw; do
  [ -z "$c" ] && continue
  [ "$gw" = "-" ] && gw=""
  case $MODE in
    check)
      echo "--- $c (want eth1.$vlan $addr${gw:+ default via $gw})"
      docker exec "$c" sh -c "ip -o -4 addr show | grep -E ' eth1(\.$vlan)? '; ip route show default"
      ;;
    apply)
      docker exec "$c" sh -c "
        set -e
        ip link show eth1.$vlan >/dev/null 2>&1 || ip link add link eth1 name eth1.$vlan type vlan id $vlan
        ip link set eth1.$vlan up
        ip addr del $addr dev eth1 2>/dev/null || true
        ip -o -4 addr show dev eth1.$vlan | grep -q ' $addr ' || ip addr add $addr dev eth1.$vlan
        if [ -n '$gw' ]; then ip route replace default via $gw dev eth1.$vlan; fi
      " && echo "OK   $c eth1.$vlan $addr${gw:+ gw $gw}" || echo "FAIL $c"
      ;;
    rollback)
      docker exec "$c" sh -c "
        set -e
        ip addr del $addr dev eth1.$vlan 2>/dev/null || true
        ip -o -4 addr show dev eth1 | grep -q ' $addr ' || ip addr add $addr dev eth1
        if [ -n '$gw' ]; then ip route replace default via $gw dev eth1; fi
      " && echo "OK   $c back on eth1 $addr (eth1.$vlan left in place, no address)" || echo "FAIL $c"
      ;;
  esac
done
