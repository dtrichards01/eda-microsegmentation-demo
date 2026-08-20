# EDA microsegmentation demo (red / blue / green)

**Repo:** https://github.com/dtrichards01/eda-microsegmentation-demo

Standard **VirtualNetwork** services on an EVPN leaf fabric, using the **microsegmentation** app **6.0.2** (GBP on SR Linux 26.3+ / IXR-D2L/D3L). Lab EDA release: **26.4.2**.

## Policy intent

| Traffic | Result |
|---------|--------|
| red ↔ red, blue ↔ blue, green ↔ green | Allow |
| red ↔ blue | Allow |
| blue ↔ green | Allow |
| red ↔ green | **Drop** |
| Any other cross-group pair | Drop (implicit default deny) |

## Documentation

| Doc | Content |
|-----|---------|
| **[docs/EDA-Microsegmentation.md](docs/EDA-Microsegmentation.md)** | EDA microsegmentation intro, **§2 per-variant guide (A–G)**, CR reference, deploy |
| **[docs/EDA-Microsegmentation-Test-Report.md](docs/EDA-Microsegmentation-Test-Report.md)** | Ping matrices, sign-off (D/E GO Aug 2026) |
| **[docs/VARIANT-SCOPE-LOCK.md](docs/VARIANT-SCOPE-LOCK.md)** | Authoritative leaf/client scope (max 3 leaves) |
| **[variants/README.md](variants/README.md)** | YAML catalog and apply files |

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
bash apply-dot1q.sh    # edge Dot1q + labels (catalog only — see scope lock for D/E)
```

## Variant catalog (summary)

| ID | VirtualNetwork | Association | Enforcement |
|----|----------------|-------------|-------------|
| A | `vnet-ms-vlan` | VLAN | `virtualNetworks` |
| B | `vnet-ms-bridge` | BridgeInterface | `virtualNetworks` |
| C | `vnet-ms-routed` | RoutedInterface | `virtualNetworks` |
| D | `vnet-ms-irb` | IRB + VLAN | `virtualNetworks` |
| E | `vnet-ms-static` | StaticRoute + VLAN | `virtualNetworks` |
| F | `vnet-ms-enf-router` | VLAN | `routers` |
| G | `vnet-ms-enf-bd` | VLAN | `bridgeDomains` |

Per-variant purpose and enforcement points: **docs/EDA-Microsegmentation.md §2**.

**Validated (Aug 2026):** D on leaf-2/3/4, E on leaf-6/7/8.

## L3 / IRB

Multi-leaf same-subnet gateways: prefer **`rfc9135SymmetricMode`** over legacy **`hostRoutePopulate`** — see [docs/L3-IRB-RFC9135.md](docs/L3-IRB-RFC9135.md).

## Client setup

```bash
python3 scripts/configure-client-ms-eth1.py --variant D --apply
python3 scripts/run-ms-tests.py D E
```

**Clab topology:** `docs/CLAB-3-TIER-TOPOLOGY.md` (MS scope: `docs/VARIANT-SCOPE-LOCK.md` overrides)

## Key files

| Path | Purpose |
|------|---------|
| `variants/virtualnetworks.yaml` | Seven `vnet-ms-*` VirtualNetworks |
| `variants/association-policies.yaml` | `ms-assoc-*` per variant |
| `variants/microsegmentation-policies.yaml` | `ms-policy-*` per variant |
| `docs/EDA-Microsegmentation.md` | Architecture and policy guide |
| `docs/EDA-Microsegmentation-Test-Report.md` | Test results |
