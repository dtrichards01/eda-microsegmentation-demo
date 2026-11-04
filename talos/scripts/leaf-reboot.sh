#!/bin/bash
# Reboot one containerlab SR Linux leaf so platform settings that need a chassis reboot take effect
# (lpm-source-lookup for microsegmentation), and repair what the reboot breaks. Run on k0r4.
#   leaf-reboot.sh plan <leaf>   read-only: record live links, far ends and client-side state
#   leaf-reboot.sh run  <leaf>   plan, reboot, docker start, recreate links, fix mgmt0, restore clients, verify
# Why the repairs are needed: in containerlab the SR Linux reboot stops the container (restart policy no),
# which deletes its veth links and the client-side interfaces (VLAN subinterfaces, bond membership,
# addresses, routes) with them. docker start also re-adds the management IP to the container's own mgmt0,
# which then answers for the address and refuses EDA's gNMI (57410), so the node stays NotSynced.
set -u
MODE=${1:?plan|run}; L=${2:?leaf container name}
NS=clab-srl-leaf-spine-dcgw
D=/tmp/leaf-reboot/$L
SUDO=""; sudo -n true 2>/dev/null && SUDO="sudo -n"
log() { echo "$(date +%T) $*"; }

bgp_up() { docker exec $L sr_cli -e "show network-instance default protocols bgp neighbor" 2>/dev/null | grep -c established; }

plan() {
  rm -rf "$D"; mkdir -p "$D/peers"
  for c in $(docker ps --format '{{.Names}}'); do
    docker exec $c sh -c 'for i in /sys/class/net/*; do n=${i##*/}; echo "$n $(cat $i/ifindex) $(cat $i/iflink) $(cat $i/mtu)"; done' 2>/dev/null \
      | awk -v c=$c '{print c, $0}'
  done > "$D/all-ifs.txt"
  ip -o link | awk -F': ' '{split($2, a, "@"); print $1, a[1]}' > "$D/host-ifs.txt"
  python3 - "$D" "$L" <<'EOF'
import re, subprocess, sys
d, leaf = sys.argv[1], sys.argv[2]
rows = [l.split() for l in open(f"{d}/all-ifs.txt") if len(l.split()) == 5]
host = dict(l.split(None, 1) for l in open(f"{d}/host-ifs.txt"))
out = open(f"{d}/links.txt", "w")
for c, n, idx, link, mtu in rows:
    if c != leaf or not re.fullmatch(r"e1-\d+", n):
        continue
    peer = [(pc, pn) for pc, pn, pi, pl, _ in rows if pi == link and pl == idx and pc != leaf]
    if peer:
        out.write(f"container {n} {mtu} {peer[0][0]} {peer[0][1]}\n")
    elif link in host:
        h = host[link].strip()
        m = re.search(r"master (\S+)", subprocess.run(["ip", "-o", "link", "show", h], capture_output=True, text=True).stdout)
        hmtu = open(f"/sys/class/net/{h}/mtu").read().strip()
        out.write(f"host {n} {mtu} {h} {m.group(1) if m else '-'} {hmtu}\n")
    else:
        out.write(f"unknown {n} {mtu} - -\n")
EOF
  # Client-side state to replay after the link is recreated (non-SR Linux container peers only).
  while read -r kind li mtu pc pi; do
    [ "$kind" = container ] || continue
    case $pc in srl-*) continue ;; esac
    docker exec $pc sh -c "
      P=$pi
      echo \"ip link set \$P mtu $mtu\"
      m=\$(ip -o link show \$P | grep -oE 'master [^ ]+' | cut -d' ' -f2)
      [ -n \"\$m\" ] && echo \"ip link set \$P down; ip link set \$P master \$m\"
      echo \"ip link set \$P up\"
      kids=\$(ip -d -o link | awk -F': ' -v p=\$P '\$2 ~ \"@\"p\"\$\" {split(\$2, a, \"@\"); print a[1]}')
      for k in \$kids; do
        id=\$(ip -d -o link show \$k | grep -oE 'vlan protocol 802.1Q id [0-9]+' | awk '{print \$NF}')
        [ -n \"\$id\" ] && echo \"ip link show \$k >/dev/null 2>&1 || ip link add link \$P name \$k type vlan id \$id; ip link set \$k up\"
      done
      for x in \$P \$kids; do
        ip -4 -o addr show dev \$x | awk -v x=\$x '{print \"ip -o -4 addr show dev \"x\" | grep -q \\\" \"\$4\" \\\" || ip addr add \"\$4\" dev \"x}'
      done
      for x in \$P \$kids; do
        ip -4 route show | grep -E \" dev \$x( |\$)\" | grep -v 'proto kernel' | sed 's/^/ip route replace /'
      done
    " > "$D/peers/${pc}__${pi}.sh" 2>/dev/null
  done < "$D/links.txt"
  bgp_up > "$D/bgp-baseline.txt"
  log "plan for $L ($(wc -l < $D/links.txt) links, BGP established $(cat $D/bgp-baseline.txt)):"
  sed 's/^/   /' "$D/links.txt"
  for f in "$D"/peers/*.sh; do [ -s "$f" ] && { echo "   restore ${f##*/}:"; sed 's/^/      /' "$f"; }; done
  grep -q '^unknown' "$D/links.txt" && { log "STOP: link with unknown far end"; return 1; }
  return 0
}

recreate() {
  while read -r kind li mtu a b hmtu; do
    case $kind in
      container) $SUDO containerlab tools veth create -a $L:$li -b $a:$b --mtu $mtu 2>&1 | tail -1 ;;
      host)
        # containerlab is setuid root; the host-end MTU needs a privileged helper on the host netns.
        if [ "$b" = - ]; then ep=host:$a; else ep=bridge:$b:$a; fi
        $SUDO containerlab tools veth create -a $L:$li -b $ep --mtu $mtu 2>&1 | tail -1
        [ "${hmtu:-$mtu}" = "$mtu" ] || docker run --rm --privileged --net host --entrypoint ip \
          ghcr.io/hellt/network-multitool link set $a mtu $hmtu ;;
    esac
  done < "$D/links.txt"
}

run() {
  plan || exit 1
  local base; base=$(cat "$D/bgp-baseline.txt")
  log "reboot $L"
  local t0; t0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  docker exec $L sr_cli -e "tools platform chassis reboot force" >/dev/null 2>&1
  for i in $(seq 1 18); do sleep 5; [ "$(docker inspect -f '{{.State.Status}}' $L)" != running ] && break; done
  if [ "$(docker inspect -f '{{.State.Status}}' $L)" != running ]; then
    log "container stopped; starting it and recreating links"
    docker start $L >/dev/null && sleep 5
    recreate
  fi
  for a in $(docker exec $L ip -4 -o addr show dev mgmt0 2>/dev/null | awk '{print $4}'); do
    docker exec $L ip addr del $a dev mgmt0 && log "removed stray $a from container mgmt0"
  done
  for i in $(seq 1 60); do n=$(bgp_up); [ "$n" -ge "$base" ] && break; sleep 10; done
  log "BGP established $n (baseline $base)"
  for f in "$D"/peers/*.sh; do
    [ -s "$f" ] || continue
    c=${f##*/}; c=${c%%__*}
    docker exec --privileged $c sh -c "$(cat $f)" && log "restored $c (${f##*__})" || log "RESTORE FAILED $c"
  done
  # Only trust a Synced state that changed after the reboot.
  for i in $(seq 1 40); do
    s=$(kubectl -n $NS get toponode $L -o jsonpath='{.status.node-state} {.status.nodeStateLastChange}')
    set -- $s; [ "$1" = Synced ] && [[ "$2" > "$t0" ]] && break; sleep 15
  done
  log "EDA $L: $s (reboot at $t0)"
  docker exec $L sr_cli -e "info from state platform resource-management group-based-policy" 2>&1 | grep -vE '^\s*$' | sed 's/^/   /'
  live=$(docker exec $L ip -o link | awk -F': ' '{split($2, a, "@"); print a[1]}' | grep -cE '^e1-[0-9]+$')
  log "links $live/$(wc -l < $D/links.txt)"
}

case $MODE in
  plan) plan ;;
  run)  run ;;
esac
