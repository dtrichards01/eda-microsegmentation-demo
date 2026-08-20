# MS cleanup snapshot — 2026-02-20

Namespace: `clab-3-tier-leaf-spine-dcgw`
Context: `kind-eda-demo-wsl2`

## Pre-delete VirtualNetworks (`vnet-ms-*`) — `status.nodes`

| Name | status.nodes |
|------|----------------|
| vnet-ms-bridge | leaf-6, leaf-7, leaf-5 |
| vnet-ms-irb | leaf-6, leaf-7, leaf-4, leaf-5, leaf-2, leaf-3, leaf-8, leaf-1 |
| vnet-ms-routed | leaf-6, leaf-7, leaf-5 |
| vnet-ms-vlan | leaf-2, leaf-3, leaf-1 |

Not present in cluster: `vnet-ms-static`, `vnet-ms-enf-router`, `vnet-ms-enf-bd`.

## Pre-delete AssociationPolicies (`ms-assoc-*`)

- ms-assoc-bridge
- ms-assoc-irb
- ms-assoc-routed
- ms-assoc-vlan

## Pre-delete MicroSegmentationPolicies (`ms-policy-*`)

- ms-policy-bridge
- ms-policy-irb
- ms-policy-routed
- ms-policy-vlan

## Non-MS VirtualNetworks (retained)

| Name | status.nodes |
|------|----------------|
| vnet-1 | leaf-4, leaf-1 |
| vnet-2 | leaf-5, leaf-7 |
| vnet-3 | leaf-2 |
| vnet-4 | leaf-6 |
| vnet-5 | leaf-3 |

## Label cleanup (ethernet-1-5)

Removed MS variant labels from wrong leaves:

| Interface | Labels removed |
|-----------|----------------|
| leaf-1-ethernet-1-5 | ms-group, ms-vlan, vnet-ms-vlan |
| leaf-5-ethernet-1-5 | ms-demo, ms-group, vnet-ms-irb |
| leaf-6-ethernet-1-5 | ms-demo, ms-group, ms-vlan, vnet-ms-irb |
| leaf-7-ethernet-1-5 | ms-demo, ms-group, ms-vlan, vnet-ms-irb |

Retained on test leaves (pre-apply):

- leaf-2-ethernet-1-5: ms-group=blue, ms-vlan=101, vnet-ms-vlan=bd-ms-vlan (+ vnet-3 DCI label)
- leaf-3-ethernet-1-5: ms-group=green, ms-vlan=101, vnet-ms-vlan=bd-ms-vlan (+ vnet-5 DCI label)
- leaf-4-ethernet-1-5: no MS labels (vnet-1 DCI only)
