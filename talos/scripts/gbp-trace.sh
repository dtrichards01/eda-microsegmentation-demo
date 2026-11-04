#!/bin/bash
# Read-only trace: which network-instance's GBP ACL counts red->green drops, per test.
snap() {  # snap <leaf> <out>
  docker exec srl-leaf-$1 sr_cli -e 'info flat from state network-instance * group-based-policy acl' 2>/dev/null \
    | grep -E 'ms-[^ ]* group-based-policy acl entry [0-9]+ statistics matched-packets' \
    | awk '{print $3"#"$7, $10}' | sort > $2
}
desc() {  # desc <leaf> <ni> <entry>
  docker exec srl-leaf-$1 sr_cli -e "info flat network-instance $2 group-based-policy acl entry $3 description" 2>/dev/null \
    | sed -E 's/.*description //'
}
trace() {  # trace <test> <src> <vlan> <dst> <src-leaf> <dst-leaf>
  local t=$1 c=$2 v=$3 d=$4 sl=$5 dl=$6
  for l in $sl $dl; do snap $l /tmp/tr-$l-a; done
  docker exec $c ping -I eth1.$v -c 10 -i 0.3 -W 1 -q $d >/dev/null 2>&1
  sleep 8
  echo "### $t: $c (leaf-$sl) -> $d (leaf-$dl)"
  for l in $sl $dl; do
    snap $l /tmp/tr-$l-b
    join /tmp/tr-$l-a /tmp/tr-$l-b | awk -v l=$l '$3>$2 {print l, $1, $3-$2}' | while read lf k n; do
      ni=${k%#*}; e=${k#*#}
      printf '  leaf-%s %-22s entry %-3s +%-3s %s\n' $lf $ni $e $n "$(desc $lf $ni $e)"
    done
  done
}
want() { local t; for t in "${SEL[@]}"; do [ "$t" = "${1%%-*}" ] && return 0; done; return 1; }
SEL=("$@")  # gbp-trace.sh [A B ... H]; no arguments = all
while read -r t c v d s r; do
  if [ ${#SEL[@]} -eq 0 ] || want "$t"; then trace "$t" "$c" "$v" "$d" "$s" "$r"; fi
done <<'EOF'
A        client-1 75  172.16.75.3   1 3
B        client-5 76  172.16.76.7   5 7
C        client-1 80  172.16.82.10  1 4
D        client-4 85  172.16.85.3   4 3
E        client-8 90  172.16.90.7   8 7
E-static client-8 90  172.16.91.1   8 7
F        client-5 100 172.16.142.8  5 8
G        client-5 110 172.16.110.8  5 8
H        client-1 120 172.16.121.7  1 7
EOF

