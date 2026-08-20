# L3 / IRB: host routes — legacy vs RFC 9135 symmetric mode

When a VirtualNetwork uses an **IRB gateway** and clients on **multiple leaves share the same subnet**, EVPN must advertise host reachability so remote leaves can forward correctly.

## Old vs new

| | **Legacy (avoid)** | **Preferred (RFC 9135)** |
|---|-------------------|--------------------------|
| **Field** | `hostRoutePopulate` on `irbInterfaces` | `rfc9135SymmetricMode` on `irbInterfaces` |
| **Mode** | Asymmetric host-route populate | Symmetric IRB (IETF RFC 9135) |
| **Use for** | Historical demos / older patterns | **New L3/IRB vnets** (multi-leaf same subnet) |

### Why prefer `rfc9135SymmetricMode`

- Symmetric VLAN / bridge scaling across leaves
- Lower TCAM use vs asymmetric host-route programming
- IETF-standard EVPN IRB behavior (RFC 9135)
- Multi-vendor interoperability
- Multi-leaf **same-subnet** reachability via **EVPN RT-2** (MAC/IP) without asymmetric host-route hacks

## Legacy pattern (in repo variants — reference only)

The checked-in `variants/virtualnetworks.yaml` IRB entries still use `hostRoutePopulate` for demo compatibility. **Do not copy this for new vnets.**

```yaml
# OLD — asymmetric; avoid for new designs
hostRoutePopulate:
  dynamic: { populate: true }
  evpn: { populate: true, datapathProgramming: true }
  static: { populate: true }
```

## Manual vnet adds (after lab testing)

When you add a **new** L3/IRB VirtualNetwork manually (post-test), use **`rfc9135SymmetricMode`** on the IRB instead of `hostRoutePopulate`.

Apply manifests in this repo (`virtualnetworks.yaml`, `apply-all.sh`) are intentionally unchanged — you add production-style vnets yourself once validated.

## This repo — which variants use which pattern

| VirtualNetwork | L3/IRB? | Pattern in YAML |
|----------------|---------|-----------------|
| `vnet-ms-vlan` | IRB gateway | **Legacy** `hostRoutePopulate` |
| `vnet-ms-bridge` | IRB gateway | **Legacy** |
| `vnet-ms-routed` | L3 routed IF only (no IRB) | **N/A** |
| `vnet-ms-irb` | IRB association demo | **Legacy** |
| `vnet-ms-static` | IRB + static route | **Legacy** |
| `vnet-ms-enf-router` | IRB gateway | **Legacy** |
| `vnet-ms-enf-bd` | L2 only | **N/A** |
| `vnet-ms-demo.yaml` | IRB gateway | **Neither** (no host-route block) |

No file in this repo currently defines `rfc9135SymmetricMode`.

## See also

- Architecture / GBP policy: [EDA-Microsegmentation.md](EDA-Microsegmentation.md) (§ host route populate — legacy wording)
- Clab VLAN ↔ vnet map: [CLAB-3-TIER-TOPOLOGY.md](CLAB-3-TIER-TOPOLOGY.md)
