#!/bin/bash
# Read-only regression for the projects sharing the Talos dcgw lab (DCI, firewall, tenancy).
# Run on k0r4 after every microsegmentation gate. Exit code = number of failed checks.
set -u
NS=clab-srl-leaf-spine-dcgw
fail=0
chk() {  # chk <want ok|fail> <desc> <src> <dst>
  local want=$1 desc=$2 src=$3 dst=$4 got
  if docker exec "$src" ping -c 3 -W 1 -q "$dst" >/dev/null 2>&1; then got=ok; else got=fail; fi
  if [ "$got" = "$want" ]; then r=PASS; else r=FAIL; fail=$((fail+1)); fi
  printf '%-4s %-46s %-22s -> %-14s (want %s)\n' "$r" "$desc" "$src" "$dst" "$want"
}
echo "== EDA state"
kubectl -n $NS get virtualnetwork --no-headers -o custom-columns=N:.metadata.name,S:.status.operationalState | awk '{printf "%s=%s ", $1, $2}'; echo
kubectl get routerinterconnect,bridgedomaininterconnect -A --no-headers | awk '{printf "%s=%s ", $2, $3}'; echo
kubectl -n $NS get interface --no-headers -o custom-columns=N:.metadata.name,S:.status.operationalState | awk '$2!="Up" {print "IF-NOT-UP", $0}'

echo "== DCI (L3 hub-spoke + L2 stretch)"
chk ok   "vnet-1 local leaf-1 -> leaf-2"        client-1 172.16.101.2
chk ok   "vnet-1 -> hub vnet-2 (DCI)"           client-1 172.16.201.1
chk ok   "vnet-1 leaf-2 -> hub leaf-6 (DCI)"    client-2 172.16.201.2
chk ok   "hub -> vnet-1 (DCI)"                  client-5 172.16.101.1
chk ok   "hub -> spoke vnet-5 (DCI)"            client-5 172.16.151.1
chk ok   "spoke vnet-5 -> hub (DCI)"            client-4 172.16.201.1
chk fail "spoke isolation vnet-1 -> vnet-5"     client-1 172.16.151.1
chk ok   "L2 stretch vnet-3 -> vnet-4 (BDI)"    client-3 172.16.105.1
chk ok   "L2 vnet-4 leaf-7 -> leaf-8"           client-7 172.16.105.2

echo "== Tenancy (eth2, untouched)"
chk ok   "tenant-a client-1 -> client-2"        client-1 10.99.0.2

echo "== Firewall"
chk ok   "PAN inside -> outside"                fw-demo-red-1         10.31.2.10
chk ok   "PAN outside -> inside"                fw-client-pan-outside 10.31.1.10
chk ok   "FG1 inside -> outside"                fw-client-fg-inside   10.21.2.10
chk ok   "FG1 outside -> inside"                fw-client-fg-outside  10.21.1.10
chk fail "PAN zone -> FG zone"                  fw-demo-red-1         10.21.2.10

echo "== Isolation"
chk fail "DCI client-1 -> firewall client"      client-1 10.31.1.10
chk fail "DCI client-5 -> firewall client"      client-5 10.21.1.10
gbp=0
for n in srl-leaf-1 srl-leaf-2 srl-leaf-4 srl-leaf-5; do
  for ni in bd-1 bd-2 bd-5; do
    c=$(docker exec $n sr_cli -e "info network-instance $ni protocols bgp-evpn bgp-instance 1 group-based-policy" 2>/dev/null | grep -cvE '^\s*$|!!!|network-instance|protocols|bgp-evpn|bgp-instance|group-based-policy|^\s*}')
    [ "$c" != "0" ] && { echo "FAIL GBP lines in DCI $n $ni: $c"; gbp=$((gbp+1)); }
  done
done
[ $gbp -eq 0 ] && echo "PASS no group-based-policy in DCI bridge domains"
fail=$((fail+gbp))
echo "failed checks: $fail"
exit $fail
