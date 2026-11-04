#!/bin/bash
# Read-only: summarise a (dry-run) EDA transaction. txn-diff.sh <txn-id> [node ...]
set -u
TID=$1; shift
TB=$(kubectl -n eda-system get pods -l eda.nokia.com/app=eda-toolbox -o jsonpath='{.items[0].metadata.name}')
e() { kubectl -n eda-system exec "$TB" -- edactl -n clab-srl-leaf-spine-dcgw "$@" 2>&1; }
echo "== errors"
e transaction "$TID" -e | head -20
echo "== nodes touched"
e transaction "$TID" node-change | grep -vE '^\s*Node\s*$' | tr -s ' \n' ' '; echo
nodes=$(e transaction "$TID" node-change | grep -oE '(srl-leaf|srl-spine|dcgw)-[0-9]+')
echo "== changed lines in other projects' objects (want none)"
for n in $nodes; do
  e transaction "$TID" node-change "$n" | grep -E '^[-+]' | grep -vE '^(---|\+\+\+)' \
    | grep -nE 'bd-[1-5]\b|router-[1-3]\b|fw-|tenant|mh-avtep|ethernet-1/(6|20|21|30|31)\.|\.10[1-5]\b|irb0\.[0-9]+ ' \
    | sed "s/^/$n: /" | head -10
done
for n in "$@"; do
  echo "== $n diff"
  e transaction "$TID" node-change "$n"
done
