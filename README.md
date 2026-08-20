# EDA microsegmentation demo (red / blue / green)

Standard **VirtualNetwork** services on an EVPN leaf fabric, using the **microsegmentation** app (GBP on SR Linux 26.3+).

## Policy intent

| Traffic | Result |
|---------|--------|
| red â†” red, blue â†” blue, green â†” green | Allow |
| red â†” blue | Allow |
| blue â†” green | Allow |
| red â†” green | **Drop** |
| Any other cross-group pair | Drop (implicit default deny) |

## Prerequisites

1. EDA UI: `https://127.0.0.1:9443`
2. **microsegmentation** catalog app installed and healthy
3. Bootstrap pools: `vni-pool`, `evi-pool`, `tunnel-index-pool`, `group-tag-pool-local`, `group-tag-pool-global`
4. Fabric operational (leaf/spine EVPN)
5. SR Linux **26.3.1+** on **7220 IXR-D2/D3** leaves

Change `namespace: clab-3-tier-leaf-spine-dcgw` in YAML if your clab namespace differs.

## Deploy

```bash
cd variants
bash apply-all.sh      # vnet-ms-* + policies
bash apply-dot1q.sh    # edge Dot1q + labels
```

## Variant catalog (dedicated services only)

| ID | VirtualNetwork | Association | Enforcement |
|----|----------------|-------------|-------------|
| A | `vnet-ms-vlan` | VLAN | `virtualNetworks` |
| B | `vnet-ms-bridge` | BridgeInterface | `virtualNetworks` |
| C | `vnet-ms-routed` | RoutedInterface | `virtualNetworks` |
| D | `vnet-ms-irb` | IRBInterface | `virtualNetworks` |
| E | `vnet-ms-static` | StaticRoute | `virtualNetworks` |
| F | `vnet-ms-enf-router` | VLAN | `routers` |
| G | `vnet-ms-enf-bd` | VLAN | `bridgeDomains` |

Full matrix: ariants/README.md.
## Architecture + Variant Glossary

### Architecture flow (operator view)

- `VirtualNetwork` defines the service chain: `bridgeDomain`/`vlan` for L2 edge, optional `irbInterface` + `routedInterface`, and `router` for L3 forwarding.
- Endpoint labels are attached on interface CRs in `variants/edge-interfaces-dot1q.yaml` (for example `eda.nokia.com/ms-group` and `eda.nokia.com/vnet-ms-*`).
- `AssociationPolicy` maps variant resources (VLAN, BridgeInterface, RoutedInterface, IRBInterface, or StaticRoute) to `GroupTag` values (`red`/`blue`/`green`/`gateway`).
- `MicroSegmentationPolicy` enforces traffic by matching source/destination GroupTags and applying allow/deny on its `serviceTargets` (`virtualNetworks`, `routers`, or `bridgeDomains`).

### Variant glossary (A-G)

- **A**: VLAN association and `virtualNetworks` enforcement on `vnet-ms-vlan`; validated on leaf-1/2/3.
- **B**: BridgeInterface association and `virtualNetworks` enforcement on `vnet-ms-bridge`; validated on leaf-5/6/7.
- **C**: RoutedInterface association and `virtualNetworks` enforcement on `vnet-ms-routed`; validated on leaf-5/6/7.
- **D**: IRB-focused segmentation (`gateway` + host groups) on `vnet-ms-irb`; validated on **leaf-2=blue, leaf-3=green, leaf-4=red** (`client2/3/4`, VLAN 85).
- **E**: StaticRoute + segmentation checks on `vnet-ms-static`; validated on **leaf-6=blue, leaf-7=green, leaf-8=red** (`client6/7/8`, VLAN 90).
- **F**: VLAN association with `router`-target enforcement on `vnet-ms-enf-router`; validated on leaf-5/6/7.
- **G**: VLAN association with `bridgeDomain`-target (L2) enforcement on `vnet-ms-enf-bd`; validated on leaf-5/6/7.

**Scope:** current automated validation is leaf-local only; no across-DC test path is included yet.

## L3 / IRB

Multi-leaf same-subnet gateways: prefer **`rfc9135SymmetricMode`** over legacy **`hostRoutePopulate`** â€” see [docs/L3-IRB-RFC9135.md](docs/L3-IRB-RFC9135.md).

## Client setup

```bash
python3 scripts/configure-client-ms-eth1.py --variant A --apply   # VLAN 75, vnet-ms-vlan
python3 scripts/run-ms-tests.py                                    # all variants Aâ€“G
```

**Clab topology:** `docs/CLAB-3-TIER-TOPOLOGY.md`

## Key files

| Path | Purpose |
|------|---------|
| `variants/virtualnetworks.yaml` | Seven `vnet-ms-*` VirtualNetworks |
| `variants/association-policies.yaml` | `ms-assoc-*` per variant |
| `variants/microsegmentation-policies.yaml` | `ms-policy-*` per variant |
| `docs/EDA-Microsegmentation.md` | Architecture and policy guide |
| `docs/EDA-Microsegmentation-Test-Report.md` | Test results |



