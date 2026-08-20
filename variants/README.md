# Microsegmentation variant catalog

Each **VirtualNetwork** in this folder is a **dedicated** demo service for one association or enforcement option. Look up services in the EDA UI by label `eda.nokia.com/ms-variant` or annotation `eda.nokia.com/ms-demo-description`.

## Service catalog

| ID | VirtualNetwork | Variant label | Association method | Enforcement (`serviceTargets`) | Subnet / GW | Client ports |
|----|----------------|---------------|--------------------|--------------------------------|-------------|--------------|
| **A** | `vnet-ms-vlan` | `vlan-association` | **VLANs** (`vlan-ms-vlan-red`, ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦) | `virtualNetworks` | `172.16.75.0/24` GW `.254` | leaf-1/2/3 `ethernet-1/5` |
| **B** | `vnet-ms-bridge` | `bridge-interface-association` | **BridgeInterfaces** (`bi-red-5`, ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦) | `virtualNetworks` | `172.16.75.0/24` GW `.254` | leaf-5/6/7 `ethernet-1/5` |
| **C** | `vnet-ms-routed` | `routed-interface-association` | **RoutedInterfaces** (`ri-red-5`, `ri-blue-6`, `ri-green-7`) | `virtualNetworks` | `80.1/24`, `81.1/24`, `82.1/24` per leaf | leaf-5/6/7 `ethernet-1/5` |
| **D** | `vnet-ms-irb` | `irb-interface-association` | **IRBInterfaces** (`irb-ms-irb`) + VLAN helpers | `virtualNetworks` | `172.16.85.0/24` GW `.254` | leaf-2=blue, leaf-3=green, leaf-4=red (`client2/3/4`) |
| **E** | `vnet-ms-static` | `static-route-association` | **StaticRoutes** + VLAN clients | `virtualNetworks` | `172.16.90.0/24` GW `.254` | leaf-6=blue, leaf-7=green, leaf-8=red (`client6/7/8`) |
| **F** | `vnet-ms-enf-router` | `enforcement-router-target` | VLAN tagging | **`routers: [router-ms-enf-router]`** | `172.16.100.0/24` GW `.254` | leaf-5/6/7 `ethernet-1/5` |
| **G** | `vnet-ms-enf-bd` | `enforcement-bridge-domain-target` | VLAN tagging | **`bridgeDomains: [bd-ms-enf-bd]`** (L2 only) | L2 only | leaf-5/6/7 `ethernet-1/5` |

### Policy objects per variant

| Variant | AssociationPolicy | MicroSegmentationPolicy |
|---------|-------------------|-------------------------|
| A | `ms-assoc-vlan` | `ms-policy-vlan` |
| B | `ms-assoc-bridge` | `ms-policy-bridge` |
| C | `ms-assoc-routed` | `ms-policy-routed` |
| D | `ms-assoc-irb` | `ms-policy-irb` |
| E | `ms-assoc-static` | `ms-policy-static` |
| F | `ms-assoc-enf-router` | `ms-policy-enf-router` |
| G | `ms-assoc-enf-bd` | `ms-policy-enf-bd` |

Common rule intent: redÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Âblue **allow**, blueÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Âgreen **allow**, redÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬Âgreen **drop**, same-group allow, implicit default deny.

Rule design notes (minimal vs explicit entries, logging): `docs/EDA-Microsegmentation.md` Ãƒâ€šÃ‚Â§3.5.

Routers use `nodeSelectors: [eda.nokia.com/role=leaf]` ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â GBP on SR Linux leaves only.



### Variant B lab note (isolation test 2026-08-19)

`bridgeInterfaceSelectors` on parent Interface labels (`eda.nokia.com/ms-group` on `leaf-5/6/7-ethernet-1-5`) did **not** program GBP tags on dot1q subinterface `ethernet-1/5.75`. Use explicit `associationTargets.bridgeInterfaces` in `ms-assoc-bridge`: `bi-red-5`, `bi-blue-6`, `bi-green-7` (leaf5/6/7 + client5/6/7). See `docs/manifests/ms-assoc-bridge-patch.yaml`.

## Dot1q VLANs (multi-service on same edge port)

| Variant | VLAN | Dot1q subif |
|---------|------|-------------|
| A | 75 | `ethernet-1/5.75` |
| B | 75 | `ethernet-1/5.75` |
| C | 80/81/82 | `ethernet-1/5.80` / `.81` / `.82` |
| D | 85 | `ethernet-1/5.85` |
| E | 90 | `ethernet-1/5.90` |
| F | 100 | `ethernet-1/5.100` |
| G | 110 | `ethernet-1/5.110` |
## Activation

```bash
cd variants
bash apply-all.sh
bash apply-dot1q.sh
python3 ../scripts/configure-client-ms-eth1.py --variant A --apply
```

## Files

| File | Purpose |
|------|---------|
| `virtualnetworks.yaml` | Seven `vnet-ms-*` VirtualNetworks |
| `association-policies.yaml` | `ms-assoc-*` |
| `microsegmentation-policies.yaml` | Generated `ms-policy-*` |
| `gen-microsegmentation-policies.py` | Regenerate policies YAML |
| `edge-interfaces-dot1q.yaml` | Dot1q + labels (full Interface spec) |
| `apply-dot1q.sh` | Edge + vnets + policies |
| `apply-all.sh` | Vnets + policies (no edge) |

