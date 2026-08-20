#!/usr/bin/env bash
NS=clab-3-tier-leaf-spine-dcgw
for v in vnet-ms-vlan vnet-ms-bridge vnet-ms-routed vnet-ms-irb vnet-ms-static vnet-ms-enf-router vnet-ms-enf-bd; do
  kubectl get virtualnetwork "$v" -n "$NS" -o custom-columns=NAME:.metadata.name,STATE:.status.operationalState,NODES:.status.numNodes,SUBIF:.status.numSubinterfaces 2>/dev/null
done
kubectl get interfaces -n "$NS" -o custom-columns=NAME:.metadata.name,MS:.metadata.labels.eda\\.nokia\\.com/ms-group 2>/dev/null | grep ethernet-1-5
