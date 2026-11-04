#!/bin/bash
# Talos microsegmentation tests. Run on k0r4.
#   ms-tests.sh setup <A|B|C|D|E|F|G|H ...>   additive client config: eth1.<vlan>, IP, specific routes (never the default route)
#   ms-tests.sh test  <A|B|C|D|E|F|G|H ...>   ping matrix; exit code = failed checks
set -u
MODE=${1:?setup|test}; shift
VARIANTS=${*:-A B C D E F G}
fail=0

# variant: client colour vlan address gateway(- = none) [routes...]
cfg() {
  case $1 in
    A) cat <<EOF
client-1 red   75 172.16.75.1/24 172.16.75.254
client-2 blue  75 172.16.75.2/24 172.16.75.254
client-3 green 75 172.16.75.3/24 172.16.75.254
EOF
    ;;
    B) cat <<EOF
client-5 red   76 172.16.76.5/24 172.16.76.254
client-6 blue  76 172.16.76.6/24 172.16.76.254
client-7 green 76 172.16.76.7/24 172.16.76.254
EOF
    ;;
    C) cat <<EOF
client-1 red   80 172.16.80.10/24 172.16.80.1 172.16.81.0/24 172.16.82.0/24
client-2 blue  80 172.16.81.10/24 172.16.81.1 172.16.80.0/24 172.16.82.0/24
client-4 green 80 172.16.82.10/24 172.16.82.1 172.16.80.0/24 172.16.81.0/24
EOF
    ;;
    D) cat <<EOF
client-4 red   85 172.16.85.4/24 172.16.85.254
client-2 blue  85 172.16.85.2/24 172.16.85.254
client-3 green 85 172.16.85.3/24 172.16.85.254
EOF
    ;;
    E) cat <<EOF
client-8 red   90 172.16.90.8/24 172.16.90.254 172.16.91.0/24
client-6 blue  90 172.16.90.6/24 172.16.90.254 172.16.91.0/24
client-7 green 90 172.16.90.7/24 172.16.90.254
EOF
    ;;
    F) cat <<EOF
client-5 red   100 172.16.140.5/24 172.16.140.254 172.16.141.0/24 172.16.142.0/24
client-6 blue  100 172.16.141.6/24 172.16.141.254 172.16.140.0/24 172.16.142.0/24
client-8 green 100 172.16.142.8/24 172.16.142.254 172.16.140.0/24 172.16.141.0/24
EOF
    ;;
    G) cat <<EOF
client-5 red   110 172.16.110.5/24 -
client-7 blue  110 172.16.110.7/24 -
client-8 green 110 172.16.110.8/24 -
EOF
    ;;
    # H: cross-DC. DC1 (pod-1) 172.16.120.0/24, DC2 (pod-2) 172.16.121.0/24, joined over the IPVPN DCI.
    H) cat <<EOF
client-1 red    120 172.16.120.1/24 172.16.120.254 172.16.121.0/24
client-3 green1 120 172.16.120.3/24 172.16.120.254 172.16.121.0/24
client-5 blue   120 172.16.121.5/24 172.16.121.254 172.16.120.0/24
client-7 green2 120 172.16.121.7/24 172.16.121.254 172.16.120.0/24
EOF
    ;;
  esac
}

setup() {
  cfg "$1" | while read -r c col vlan addr gw routes; do
    docker exec "$c" sh -c "
      set -e
      ip link show eth1.$vlan >/dev/null 2>&1 || ip link add link eth1 name eth1.$vlan type vlan id $vlan
      ip link set eth1.$vlan up
      ip -o -4 addr show dev eth1.$vlan | grep -q ' $addr ' || ip addr add $addr dev eth1.$vlan
      for r in $routes; do ip route show \$r | grep -q . || ip route add \$r via $gw dev eth1.$vlan; done
    " && echo "OK   $1 $c ($col) eth1.$vlan $addr" || echo "FAIL $1 $c"
  done
  # E: client-7 (green) answers for the static-route prefix 172.16.91.0/24.
  if [ "$1" = E ]; then
    docker exec client-7 sh -c "ip -o -4 addr show dev lo | grep -q ' 172.16.91.1/32 ' || ip addr add 172.16.91.1/32 dev lo" \
      && echo "OK   E client-7 lo 172.16.91.1/32" || echo "FAIL E client-7 lo"
  fi
}

ping_t() {  # ping_t <variant> <label> <src> <vlan> <dst> <allow|drop>
  local got r
  docker exec "$3" ping -I "eth1.$4" -c 1 -W 1 "$5" >/dev/null 2>&1
  if docker exec "$3" ping -I "eth1.$4" -c 3 -W 2 -q "$5" >/dev/null 2>&1; then got=allow; else got=drop; fi
  if [ "$got" = "$6" ]; then r=PASS; else r=FAIL; fail=$((fail+1)); fi
  printf '%-4s %s %-20s %-9s -> %-14s expect=%-5s got=%s\n' "$r" "$1" "$2" "$3" "$5" "$6" "$got"
}

test_h() {  # DC1: red client-1, green client-3. DC2: blue client-5, green client-7.
  ping_t H "red->blue (x-DC)"      client-1 120 172.16.121.5 allow
  ping_t H "red->green (x-DC)"     client-1 120 172.16.121.7 drop
  ping_t H "green->blue (x-DC)"    client-3 120 172.16.121.5 allow
  ping_t H "green->green (x-DC)"   client-3 120 172.16.121.7 allow
  ping_t H "blue->red (x-DC)"      client-5 120 172.16.120.1 allow
  ping_t H "green->red (x-DC)"     client-7 120 172.16.120.1 drop
  ping_t H "red->green (DC1)"      client-1 120 172.16.120.3 drop
  ping_t H "blue->green (DC2)"     client-5 120 172.16.121.7 allow
  ping_t H "red->gateway (DC1)"    client-1 120 172.16.120.254 allow
  ping_t H "blue->gateway (DC2)"   client-5 120 172.16.121.254 allow
}

test_v() {
  [ "$1" = H ] && { test_h; return; }
  local v=$1 rows red blue green rv bv gv ra ba ga rg bg gg
  rows=$(cfg "$v")
  read -r red _ rv ra rg _ <<<"$(echo "$rows" | awk '$2=="red"')"
  read -r blue _ bv ba bg _ <<<"$(echo "$rows" | awk '$2=="blue"')"
  read -r green _ gv ga gg _ <<<"$(echo "$rows" | awk '$2=="green"')"
  ra=${ra%/*}; ba=${ba%/*}; ga=${ga%/*}
  ping_t "$v" red-\>blue    "$red"   "$rv" "$ba" allow
  ping_t "$v" red-\>green   "$red"   "$rv" "$ga" drop
  ping_t "$v" blue-\>green  "$blue"  "$bv" "$ga" allow
  ping_t "$v" blue-\>red    "$blue"  "$bv" "$ra" allow
  ping_t "$v" green-\>blue  "$green" "$gv" "$ba" allow
  ping_t "$v" green-\>red   "$green" "$gv" "$ra" drop
  if [ "$rg" != - ]; then
    ping_t "$v" red-\>gateway "$red"   "$rv" "$rg" allow
    ping_t "$v" green-\>gateway "$green" "$gv" "$gg" allow
  fi
  if [ "$v" = E ]; then
    ping_t "$v" blue-\>static-green "$blue" "$bv" 172.16.91.1 allow
    ping_t "$v" red-\>static-green  "$red"  "$rv" 172.16.91.1 drop
  fi
}

for v in $VARIANTS; do
  case $MODE in
    setup) setup "$v" ;;
    test)  test_v "$v" ;;
  esac
done
[ "$MODE" = test ] && echo "failed checks: $fail"
exit $fail
