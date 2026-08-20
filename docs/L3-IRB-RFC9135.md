# L3 / IRB: EVPN route advertisement (RFC 9135 symmetric mode)

When a VirtualNetwork uses an **IRB gateway** and clients on **multiple leaves share the same subnet**, EVPN must advertise host reachability so remote leaves can forward correctly.

## Current pattern (this repo)

IRB interfaces in `variants/virtualnetworks.yaml` and scoped apply bundles use **`evpnRouteAdvertisementType`** with **`rfc9135SymmetricMode: true`** — not legacy `hostRoutePopulate`.

```yaml
evpnRouteAdvertisementType:
  arpDynamic: true
  arpStatic: true
  ndDynamic: true
  ndStatic: true
  rfc9135SymmetricMode: true
```

### Why prefer `rfc9135SymmetricMode`

- Symmetric VLAN / bridge scaling across leaves
- Lower TCAM use vs asymmetric host-route programming
- IETF-standard EVPN IRB behavior (RFC 9135)
- Multi-vendor interoperability
- Multi-leaf **same-subnet** reachability via **EVPN RT-2** (MAC/IP) without asymmetric host-route hacks

## Legacy pattern (avoid for new designs)

```yaml
# OLD — asymmetric; do not copy for new vnets
hostRoutePopulate:
  dynamic: { populate: true }
  evpn: { populate: true, datapathProgramming: true }
  static: { populate: true }
```

## Variants without IRB EVPN advertisement

| VirtualNetwork | L3/IRB? | `evpnRouteAdvertisementType` |
|----------------|---------|------------------------------|
| `vnet-ms-routed` | Routed subifs only (no shared IRB) | **N/A** |
| `vnet-ms-enf-bd` | L2 only | **N/A** |

All other catalog variants (A, B, D, E, F) use the block above on their IRB where present.

## See also

- Architecture / GBP policy: [EDA-Microsegmentation.md](EDA-Microsegmentation.md) §3.3
- Clab VLAN ↔ vnet map: [CLAB-3-TIER-TOPOLOGY.md](CLAB-3-TIER-TOPOLOGY.md)
