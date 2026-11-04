#!/bin/bash
# Dry-run only (no --commit): does EDA accept a MicroSegmentationPolicy before its GroupTags exist?
# 1 control (existing tags), 2 policy naming a missing tag, 3 policy + new tag together, 4 delete in-use ms-green.
# Runs in /tmp on k0r4 next to eda-txn.py and txn-diff.sh.
cd /tmp
NS=clab-srl-leaf-spine-dcgw
MS=microsegmentation.eda.nokia.com/v1alpha1
pol() {  # pol <src-tag> <dst-tag>
cat <<EOF
apiVersion: $MS
kind: MicroSegmentationPolicy
metadata:
  name: ms-order-test
  namespace: $NS
spec:
  serviceTargets:
    bridgeDomains: [bd-ms-enf-router-red]
  entries:
  - description: order test
    bidirectional: true
    match: {sourceGroupTag: [$1], destinationGroupTag: [$2]}
    action: {forward: Accept, collectStats: true, log: false}
EOF
}
tag() {
cat <<EOF
apiVersion: $MS
kind: GroupTag
metadata:
  name: $1
  namespace: $NS
spec: {description: order test, scope: Global}
EOF
}
pol ms-red ms-green                                   > ord-1-control.yaml
pol ms-red ms-order-missing                           > ord-2-missing.yaml
{ tag ms-order-missing; echo '---'; pol ms-red ms-order-missing; } > ord-3-together.yaml
printf 'apiVersion: %s\nkind: GroupTag\nmetadata:\n  name: ms-green\n  namespace: %s\nx-op: delete\n' $MS $NS > ord-4-delete-used.yaml
ALL=(ord-1-control ord-2-missing ord-3-together ord-4-delete-used)
SEL=()  # order-tests.sh [1 2 3 4]; no arguments = all
for n in "$@"; do SEL+=("${ALL[$((n-1))]}"); done
[ ${#SEL[@]} -gt 0 ] || SEL=("${ALL[@]}")
for f in "${SEL[@]}"; do
  echo "################ $f"
  out=$(python3 eda-txn.py $f.yaml --desc "dry-run order test $f" 2>&1)
  echo "$out" | head -40
  tid=$(echo "$out" | grep -oiE 'transaction[^0-9]*[0-9]+' | grep -oE '[0-9]+' | tail -1)
  [ -n "$tid" ] || continue
  bash txn-diff.sh $tid 2>&1 | sed -n '1,25p'
  echo "-- leaf-5 GBP lines in diff"
  TB=$(kubectl -n eda-system get pods -l eda.nokia.com/app=eda-toolbox -o jsonpath='{.items[0].metadata.name}')
  kubectl -n eda-system exec "$TB" -- edactl -n $NS transaction $tid node-change srl-leaf-5 2>&1 \
    | grep -E '^[-+]' | grep -iE 'group-based|acl|entry|order|tag' | head -15
done
