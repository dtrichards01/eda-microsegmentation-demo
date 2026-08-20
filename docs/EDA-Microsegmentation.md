# EDA Microsegmentation

**Environment:** WSL EDA (`kind-eda-demo-wsl2`) Ã¢â‚¬â€ UI https://127.0.0.1:9443  
**Namespace:** `clab-3-tier-leaf-spine-dcgw`  
**Services:** Seven dedicated `vnet-ms-*` VirtualNetworks (variants AÃ¢â‚¬â€œG)

---

## 1. Purpose

Microsegmentation divides an internal L3 service into **security groups** and enforces **eastÃ¢â‚¬â€œwest** rules between them. In this lab:

- **Red** can talk to **Blue**
- **Blue** can talk to **Green**
- **Red** cannot talk to **Green**
- All other cross-group traffic is denied by default (zero-trust)

This uses Nokia EDAÃ¢â‚¬â„¢s **microsegmentation** application, which programs **Group-Based Policy (GBP)** on SR Linux 26.3+ (7220 IXR-D2/D3) leaf nodes.

![Policy intent Ã¢â‚¬â€ red / blue / green](diagrams/policy-rules.png){width=6.5in}

The diagram uses a **triangle** layout: each edge is one pairwise relationship Ã¢â‚¬â€ allow on redÃ¢â€ â€blue and blueÃ¢â€ â€green, drop on redÃ¢â€ â€green.

---

## 2. Architecture overview (Variant A / `vnet-ms-vlan`)

Traffic is classified on the client edge port in the MAC-VRF, then filtered by a group-based ACL on the L3 router before forwarding locally or across EVPN.

### Physical topology

![Physical topology Ã¢â‚¬â€ clients, leaves, EVPN fabric](diagrams/physical-topology.png){width=6.5in}

### Packet path (Variant A)

![Packet path Ã¢â‚¬â€ Variant A vnet-ms-vlan](diagrams/packet-path.png){width=6.5in}

### Kubernetes object chain (per variant)

![Kubernetes object chain](diagrams/k8s-chain.png){width=6.5in}

---

## 3. The four Kubernetes objects

### 3.1 GroupTag

Defines logical segments: `red`, `blue`, `green`.

| Field | Value |
|-------|--------|
| API | `microsegmentation.eda.nokia.com/v1alpha1` |
| Kind | `GroupTag` |
| Scope | `Local` (per VirtualNetwork scope; IDs from `group-tag-pool-local`) |

### 3.2 AssociationPolicy

Maps GroupTags to **network resources** inside each `vnet-ms-*` service.

**Variant A example** (`ms-assoc-vlan` on `vnet-ms-vlan`):

| VLAN object | GroupTag |
|-------------|----------|
| `vlan-ms-vlan-red` | red |
| `vlan-ms-vlan-blue` | blue |
| `vlan-ms-vlan-green` | green |

EDA associates the tag with the **VLAN + bridge attachment** so SRL programs GBP on the edge subinterface.

### 3.3 VirtualNetwork (`vnet-ms-vlan` Ã¢â‚¬â€ Variant A)

| Component | Name | Details |
|-----------|------|---------|
| Bridge domain | `bd-ms-vlan` | EVPN VXLAN, MAC learning |
| Router | `router-ms-vlan` | IP-VRF, `nodeSelectors: [eda.nokia.com/role=leaf]` |
| IRB | `irb-ms-vlan` | `172.16.75.254/24` |
| VLANs | `vlan-ms-vlan-red/blue/green` | VLAN **75**, compound `interfaceSelectors` |

**Host route populate** (required for multi-leaf same-subnet):

```yaml
hostRoutePopulate:
  dynamic: { populate: true }
  evpn: { populate: true, datapathProgramming: true }
  static: { populate: true }
```

### 3.4 MicroSegmentationPolicy (`ms-policy-vlan`)

Ordered rules Ã¢â‚¬â€ **first match wins**:

| Order | Source | Destination | Action |
|-------|--------|-------------|--------|
| 1Ã¢â‚¬â€œ3 | same group | same group | Accept |
| 4 | red | blue | Accept |
| 5 | blue | green | Accept |
| 6 | red | green | Drop |
| 7 | * | * | Drop (implicit deny) |

`bidirectional: true` generates reverse ACL entries on the switch.

```yaml
serviceTargets:
  virtualNetworks:
    - vnet-ms-vlan
```

### 3.5 Rule design Ã¢â‚¬â€ minimal allows, explicit combinations, and logging

GBP evaluates each packet against **source group + destination group** (not hop-by-hop). Rules are **ordered**; the **first match wins**. `bidirectional: true` programs the reverse direction on the switch (e.g. red Ã¢â€ â€™ blue also covers blue Ã¢â€ â€™ red).

#### Minimal cross-group policy (smallest enforceable set)

For the chain intent (red Ã¢â€ â€ blue, blue Ã¢â€ â€ green, red Ã¢â€ â€ green blocked), only **two allow entries** are required:

| Entry | Match | Action | Covers (with `bidirectional: true`) |
|-------|--------|--------|-------------------------------------|
| 1 | red Ã¢â€ â€™ blue | Accept | red Ã¢â€ â€ blue |
| 2 | blue Ã¢â€ â€™ green | Accept | blue Ã¢â€ â€ green |

Anything else Ã¢â‚¬â€ including **red Ã¢â€ â€ green** and **green Ã¢â€ â€ red** Ã¢â‚¬â€ falls through to deny. GBP is **not transitive**: red Ã¢â€ â€™ blue and blue Ã¢â€ â€™ green allowed does **not** allow red Ã¢â€ â€™ green.

Add **same-group** allow entries (red Ã¢â€ â€ red, blue Ã¢â€ â€ blue, green Ã¢â€ â€ green) only if you need intra-group or self traffic; the two cross-group rules do not cover them.

#### What the lab policy adds beyond the minimum

The generated policies (`variants/gen-microsegmentation-policies.py`) use a **richer** entry list on purpose:

| Entry | Enforcement need | Why keep it |
|-------|------------------|-------------|
| Same-group Ãƒâ€” 3 | Required for self / intra-group pings in tests | Not redundant with cross-group allows |
| red Ã¢â€ â€ blue, blue Ã¢â€ â€ green | Core chain | Minimum cross-group set |
| **red Ã¢â€ â€ green Drop** | **Not required** for correctness (implicit deny already blocks) | **Explicit combination** for operations |
| **default deny** (`match: {}`) | May be required by the platform to program a terminal deny on SRL | Catch-all for any pair not listed above |

#### Why an explicit deny can still be a valid combination

An explicit **red Ã¢â€ â€™ green Drop** duplicates the outcome of implicit deny, but it is still useful when you want that **pair** to be visible and measurable:

| Benefit | Explanation |
|---------|-------------|
| **Entry counters** | EDA UI Ã¢â€ â€™ Policy Ã¢â€ â€™ **Entry Counters** show hits on that rule, not buried in a generic catch-all |
| **Logging** | `action.log: true` on a specific Drop entry surfaces blocked red Ã¢â€ â€™ green attempts in logs without logging every other denied pair |
| **Intent in the CR** | Operators see Ã¢â‚¬Å“block red Ã¢â€ â€ greenÃ¢â‚¬Â in the policy object without inferring from absence of allows |
| **Ordering** | Placed **before** the catch-all, it wins first for that pair Ã¢â‚¬â€ useful if the catch-all is ever broadened |

In the generator, the red Ã¢â€ â€ green rule uses `log: true`; allows and the default deny use `log: false` to avoid noise.

#### Logging Ã¢â‚¬â€ when to enable it

| Pattern | Typical `log` | Rationale |
|---------|---------------|-----------|
| Cross-group **Allow** (red Ã¢â€ â€ blue) | `false` | High volume; counters (`collectStats: true`) usually enough |
| **Explicit Drop** for a sensitive pair (red Ã¢â€ â€ green) | `true` | Security signal: prove the deny is firing and aid troubleshooting |
| **Default deny** catch-all | `false` | Would flood logs with every unexpected flow |
| Gateway / IRB entries (variant D) | per entry | Log gateway violations separately from host-to-host rules |

`collectStats: true` on each entry is low-cost and complements logging: use counters for volume, logging for exceptions you care about.

#### Valid combination summary

| Goal | Suggested entries |
|------|-------------------|
| **Leanest cross-group** | 2 allows (redÃ¢â€ â€blue, blueÃ¢â€ â€green) + platform deny |
| **Lab / connectivity tests** | + 3 same-group allows |
| **Auditable deny of red Ã¢â€ â€ green** | + explicit redÃ¢â€ â€green Drop with `log: true` (redundant for enforcement, valid for ops) |
| **Explicit zero-trust tail** | + `match: {}` Drop as last entry |
| **Gateway-centric (IRB variant)** | + red/blue/green Ã¢â€ â€ gateway allows **before** host rules |

Choose **minimal allows** for simplicity; add **explicit combinations** when counters, logs, or readable policy intent matter more than the shortest YAML.

---

## 4. Lab endpoint mapping (Variant A)

| Group | Container | Leaf | Edge port | IPv4 |
|-------|-----------|------|-----------|------|
| Red | client1 | leaf-1 | ethernet-1/5 | 172.16.75.1/24 |
| Blue | client2 | leaf-2 | ethernet-1/5 | 172.16.75.2/24 |
| Green | client3 | leaf-3 | ethernet-1/5 | 172.16.75.4/24 |

Gateway: `172.16.75.254` on VLAN **75** (`eth1.75`).

Interface labels: `eda.nokia.com/ms-group=red|blue|green` and `eda.nokia.com/vnet-ms-vlan=bd-ms-vlan`.

**Scoped validation (Aug 2026)** — see `docs/VARIANT-SCOPE-LOCK.md`:

| Variant | Leaves | Clients | VLAN | Subnet |
|---------|--------|---------|------|--------|
| **D** | leaf-2=blue, leaf-3=green, leaf-4=red | client2/3/4 | 85 | `172.16.85.0/24` |
| **E** | leaf-6=blue, leaf-7=green, leaf-8=red | client6/7/8 | 90 | `172.16.90.0/24` |

Legacy catalog variants **B–G** reference leaf-5/6/7 in `variants/README.md`; use scoped apply bundles for D/E only.

---

## 5. Packet walkthrough (Variant A)

### Red Ã¢â€ â€™ Blue (allowed)

1. client1 sends ICMP to `172.16.75.2` via gateway `172.16.75.254`.
2. On leaf-1, source traffic from `ethernet-1/5.75` is group **red**.
3. `router-ms-vlan` has host route `172.16.75.2/32` (EVPN).
4. GBP ACL: red Ã¢â€ â€™ blue Ã¢â€ â€™ **Accept**.
5. Ping succeeds.

### Red Ã¢â€ â€™ Green (blocked)

GBP ACL: red Ã¢â€ â€™ green Ã¢â€ â€™ **Drop**.

### Blue Ã¢â€ â€™ Green (allowed)

GBP ACL: blue Ã¢â€ â€™ green Ã¢â€ â€™ **Accept**.

---

## 6. Where policy is applied

| Location | Applied? |
|----------|----------|
| MAC-VRF (`bd-ms-*`) on each **leaf** | Yes Ã¢â‚¬â€ group tag on edge subinterface |
| IP-VRF (`router-ms-*`) on each **leaf** | Yes Ã¢â‚¬â€ GBP ACL |
| Fabric underlay (`default` NI) | No Ã¢â‚¬â€ BGP only |
| Other `vnet-ms-*` services | No Ã¢â‚¬â€ separate VirtualNetwork scope |

---

## 7. Expected behaviour matrix

| Source Ã¢â€ â€™ Destination | Result |
|----------------------|--------|
| red Ã¢â€ â€ blue | Allow |
| blue Ã¢â€ â€ green | Allow |
| red Ã¢â€ â€ green | Drop |
| green Ã¢â€ â€ red | Drop (implicit deny) |
| same group | Allow |
| Host Ã¢â€ â€™ gateway | Allow |

---

## 8. Validation

```bash
python3 scripts/configure-client-ms-eth1.py --variant A --apply
docker exec client1 ping -c 3 172.16.75.2   # redÃ¢â€ â€™blue OK
docker exec client2 ping -c 3 172.16.75.4 # blueÃ¢â€ â€™green OK
docker exec client1 ping -c 3 172.16.75.4 # redÃ¢â€ â€™green FAIL
```

**EDA UI:** Microsegmentation Ã¢â€ â€™ Policies Ã¢â€ â€™ `ms-policy-vlan` Ã¢â€ â€™ Entry Counters.

---

## 9. Deploy

```bash
cd variants && bash apply-all.sh && bash apply-dot1q.sh
```

---

## 10. Troubleshooting

| Symptom | Check |
|---------|--------|
| Policy on but redÃ¢â€ â€blue fails | VLAN subif on leaf; parent `eth1` must not hold the IP (use `eth1.75`) |
| Tags missing on switch | AssociationPolicy VLAN targets; interface `ms-group` + `vnet-ms-vlan` labels |
| VNet not Up | `kubectl get virtualnetwork vnet-ms-vlan -n clab-3-tier-leaf-spine-dcgw` |

---

## 11. Artifact files

| Path | Purpose |
|------|---------|
| `variants/virtualnetworks.yaml` | All seven `vnet-ms-*` services |
| `variants/association-policies.yaml` | Per-variant AssociationPolicy |
| `variants/microsegmentation-policies.yaml` | Per-variant MicroSegmentationPolicy |
| `variants/edge-interfaces-dot1q.yaml` | Dot1q + MS labels on edge ports |
| `variants/apply-dot1q.sh` | Apply edge + vnets + policies |
| `scripts/configure-client-ms-eth1.py` | Client VLAN/IP switcher |
| `scripts/run-ms-tests.py` | Automated test suite AÃ¢â‚¬â€œG |
| `variants/README.md` | Full service catalog |
| `docs/diagrams/generate_diagrams.py` | Regenerate PNG diagrams for docs |

---

## 12. Association and enforcement options (full catalog)

Microsegmentation uses two independent choices:

1. **Where endpoints get a GroupTag** Ã¢â‚¬â€ `AssociationPolicy.associationTargets`
2. **Where the GBP ACL is applied** Ã¢â‚¬â€ `MicroSegmentationPolicy.serviceTargets`

### 12.1 Association targets

| Target | Typical use |
|--------|-------------|
| **VLAN** | Variant **A** Ã¢â‚¬â€ `vnet-ms-vlan` |
| **BridgeInterface** | Variant **B** Ã¢â‚¬â€ `vnet-ms-bridge` |
| **RoutedInterface** | Variant **C** Ã¢â‚¬â€ `vnet-ms-routed` |
| **IRBInterface** | Variant **D** Ã¢â‚¬â€ `vnet-ms-irb` |
| **StaticRoute** | Variant **E** Ã¢â‚¬â€ `vnet-ms-static` |

### 12.2 Enforcement targets

| Target | Typical use |
|--------|-------------|
| **VirtualNetwork** | Variants AÃ¢â‚¬â€œE Ã¢â‚¬â€ recommended |
| **Router** | Variant **F** Ã¢â‚¬â€ `vnet-ms-enf-router` |
| **BridgeDomain** | Variant **G** Ã¢â‚¬â€ `vnet-ms-enf-bd` (L2 only) |

### 12.3 Lab variant services

![Variant catalog Ã¢â‚¬â€ association and enforcement](diagrams/variant-catalog.png){width=6.5in}

| ID | VirtualNetwork | Association | Enforcement |
|----|----------------|-------------|-------------|
| A | `vnet-ms-vlan` | VLAN | `virtualNetworks` |
| B | `vnet-ms-bridge` | BridgeInterface | `virtualNetworks` |
| C | `vnet-ms-routed` | RoutedInterface | `virtualNetworks` |
| D | `vnet-ms-irb` | IRBInterface | `virtualNetworks` |
| E | `vnet-ms-static` | StaticRoute | `virtualNetworks` |
| F | `vnet-ms-enf-router` | VLAN | `routers` |
| G | `vnet-ms-enf-bd` | VLAN | `bridgeDomains` |

**Port sharing:** Variant A uses leaf-1/2/3 (VLAN **75**). Scoped validation uses **D** on leaf-2/3/4 (VLAN **85**) and **E** on leaf-6/7/8 (VLAN **90**). Legacy catalog entries for B–G reference leaf-5/6/7 on the same `ethernet-1/5` (Dot1q). See `docs/VARIANT-SCOPE-LOCK.md` for authoritative scope.

### 12.4 Variant descriptions (A–G)

Each variant is a **dedicated** `vnet-ms-*` VirtualNetwork plus matching `ms-assoc-*` and `ms-policy-*` objects. All variants share the same **policy intent** (red↔blue allow, blue↔green allow, red↔green drop, same-group allow, default deny) unless noted. They differ in **where GroupTags are bound** (association) and **where GBP is applied** (enforcement target).

#### Variant A — VLAN association (`vnet-ms-vlan`)

| Item | Detail |
|------|--------|
| **Purpose** | Baseline L2 model: classify clients by **VLAN membership** inside the service bridge domain. |
| **Association** | `ms-assoc-vlan` maps `vlan-ms-vlan-red` / `-blue` / `-green` → red / blue / green. |
| **Enforcement** | `ms-policy-vlan` → `serviceTargets.virtualNetworks: [vnet-ms-vlan]`. GBP on the VirtualNetwork (MAC-VRF + IRB path). |
| **Service** | Single subnet `172.16.75.0/24`, IRB `172.16.75.254`, VLAN **75**, symmetric IRB (`rfc9135SymmetricMode`). |
| **Scope (catalog)** | leaf-1/2/3, client1/2/3. |
| **What it proves** | GroupTags programmed from **VLAN objects**; east–west filtering on a shared L3 gateway subnet. |

#### Variant B — BridgeInterface association (`vnet-ms-bridge`)

| Item | Detail |
|------|--------|
| **Purpose** | Classify at the **BridgeInterface CR** (dot1q subinterface object) instead of the VLAN CR. |
| **Association** | `ms-assoc-bridge` must use **explicit** `bridgeInterfaces: [bi-red-5, bi-blue-6, bi-green-7]`. Label selectors on parent `Interface` CRs did **not** program GBP on `ethernet-1/5.75` in lab testing. |
| **Enforcement** | `ms-policy-bridge` → `virtualNetworks: [vnet-ms-bridge]`. |
| **Service** | Same subnet pattern as A (`172.16.75.0/24`), VLAN **75**. |
| **Scope (catalog)** | leaf-5/6/7, client4/5/6. |
| **What it proves** | Association target type **BridgeInterface** works when named explicitly; selector indirection is unreliable on access subifs. |

#### Variant C — RoutedInterface association (`vnet-ms-routed`)

| Item | Detail |
|------|--------|
| **Purpose** | Classify at **L3 routed handoff** — each colour gets its own routed subinterface and subnet on the leaf. |
| **Association** | `ms-assoc-routed` → `ri-red-5`, `ri-blue-6`, `ri-green-7`. |
| **Enforcement** | `ms-policy-routed` → `virtualNetworks: [vnet-ms-routed]`. |
| **Service** | Per-leaf gateways: `172.16.80.1/24`, `.81.1/24`, `.82.1/24`; VLANs **80/81/82**. No shared IRB subnet. |
| **Scope (catalog)** | leaf-5/6/7. |
| **Status** | **PARKED** in this lab — with policy applied, cross-subnet traffic fails even for explicit Allow rules; likely platform limitation on GBP over routed-interface paths. See `docs/tmp/variant-c-policy-fix-*/SUMMARY.md`. |

#### Variant D — IRB + VLAN association (`vnet-ms-irb`)

| Item | Detail |
|------|--------|
| **Purpose** | L3 enforcement at the **IRB gateway** while clients are tagged via VLAN helpers at ingress. |
| **Association** | `ms-assoc-irb`: `irb-ms-irb` → **gateway**; `vlan-ms-irb-red/blue/green` → red/blue/green. VLAN entries classify **client** traffic; IRB entry classifies the **gateway**. |
| **Enforcement** | `ms-policy-irb` → `virtualNetworks: [vnet-ms-irb]`. Rules include gateway pairs (red↔gateway, etc.) plus host matrix. Filtering decision at **IRB**, not on L2 VLAN bridge alone. |
| **Service** | `172.16.85.0/24`, IRB `172.16.85.254`, VLAN **85**, no `nodeSelectors: role=leaf` on router (3-leaf scope via label selectors). |
| **Scope (validated)** | **leaf-2=blue**, **leaf-3=green**, **leaf-4=red** — client2/3/4, IPs `172.16.85.2/3/4`. Apply: `variants/_variant-d-leaf234-apply.yaml`. |
| **What it proves** | IRB-level GBP with ingress VLAN tagging; IRB-only association (gateway tag alone) is **insufficient** — client VLAN associations required. |

#### Variant E — StaticRoute + VLAN association (`vnet-ms-static`)

| Item | Detail |
|------|--------|
| **Purpose** | Tag a **remote prefix** via StaticRoute association, plus client tagging via VLANs — prefix-based destination classification. |
| **Association** | `ms-assoc-static`: `static-remote-green` → **green** for prefix `172.16.91.0/24`; VLAN objects → red/blue/green for clients. Static route uses **blackhole** nexthop (no real network — tag anchor only). |
| **Enforcement** | `ms-policy-static` → `virtualNetworks: [vnet-ms-static]`. Standard host matrix; static route supplies **destination** tag for remote prefix traffic. |
| **Service** | `172.16.90.0/24`, IRB `172.16.90.254`, VLAN **90**, static route `172.16.91.0/24` on `router-ms-static`. |
| **Scope (validated)** | **leaf-6=blue**, **leaf-7=green**, **leaf-8=red** — client6/7/8, IPs `172.16.90.6/7/8`. Apply: `variants/_variant-e-leaf678-apply.yaml`. |
| **Extra test** | red → `172.16.91.1` **deny** (dest classified green via static route, red↔green blocked). |
| **What it proves** | GroupTags can bind to **StaticRoute** prefixes, not only VLAN/BI/RI/IRB objects. |

#### Variant F — Router enforcement target (`vnet-ms-enf-router`)

| Item | Detail |
|------|--------|
| **Purpose** | Same VLAN client tagging as A, but GBP ACL applied via **`serviceTargets.routers`** instead of `virtualNetworks`. |
| **Association** | `ms-assoc-enf-router` → `vlan-enf-router-red/blue/green`. |
| **Enforcement** | `ms-policy-enf-router` → `routers: [router-ms-enf-router]`. |
| **Service** | `172.16.100.0/24`, VLAN **100**. |
| **Scope (catalog)** | leaf-5/6/7. |
| **What it proves** | Enforcement anchor can be the **router CR** rather than the whole VirtualNetwork. |

#### Variant G — BridgeDomain enforcement target (`vnet-ms-enf-bd`)

| Item | Detail |
|------|--------|
| **Purpose** | **L2-only** service — no IRB/router; GBP on the **bridge domain** (MAC-VRF). |
| **Association** | `ms-assoc-enf-bd` → `vlan-enf-bd-red/blue/green`. |
| **Enforcement** | `ms-policy-enf-bd` → `bridgeDomains: [bd-ms-enf-bd]`. |
| **Service** | VLAN **110**, no L3 gateway on clients. |
| **Scope (catalog)** | leaf-5/6/7. |
| **What it proves** | Pure L2 microsegmentation with enforcement on **bridgeDomains**; hosts have no default route. |

**Scope lock:** Never span all eight leaves in one `vnet-ms-*`. Authoritative mapping: `docs/VARIANT-SCOPE-LOCK.md`.

---


## 14. Architecture + Variant Glossary

### 14.1 Architecture flow (operator view)

- `VirtualNetwork` builds the service path with `bridgeDomain`/`vlan` at the edge and `irbInterface`/`routedInterface`/`router` for L3 handling.
- Interface labels are applied on edge Interface CRs via **scoped label snippets** (`variants/labels-vnet-ms-*.yaml`) — never the full `edge-interfaces-dot1q.yaml` (labels all eight leaves).
- `AssociationPolicy` translates those resource targets into `GroupTag` identities used by GBP.
- `MicroSegmentationPolicy` enforces the matrix with allow/deny entries on defined `serviceTargets`: `virtualNetworks`, `routers`, or `bridgeDomains`.

### 14.2 Variant glossary (A–G)

Short index — full descriptions in **§12.4**.

| ID | One-line summary | Validated scope |
|----|------------------|-----------------|
| **A** | VLAN → GroupTag; enforce on VirtualNetwork | leaf-1/2/3 (catalog) |
| **B** | BridgeInterface → GroupTag (explicit BI names required) | leaf-5/6/7 (catalog) |
| **C** | RoutedInterface → GroupTag; **parked** (GBP on routed path broken) | leaf-5/6/7 (catalog) |
| **D** | IRB gateway tag + VLAN client tags; enforce at IRB | **leaf-2/3/4** — GO |
| **E** | StaticRoute prefix tag + VLAN client tags | **leaf-6/7/8** — GO |
| **F** | VLAN tags; enforce on **router** not VirtualNetwork | leaf-5/6/7 (catalog) |
| **G** | VLAN tags; enforce on **bridgeDomain** (L2 only) | leaf-5/6/7 (catalog) |

- **B lab note:** `bridgeInterfaceSelectors` on parent Interface labels did not program GBP on `ethernet-1/5.75`. Use explicit `bridgeInterfaces` in `ms-assoc-bridge`. See `docs/manifests/ms-assoc-bridge-patch.yaml`.
- **D/E:** See `variants/_variant-d-leaf234-apply.yaml` and `variants/_variant-e-leaf678-apply.yaml` for scoped apply bundles.

**Scope:** three leaves maximum per variant; see `docs/VARIANT-SCOPE-LOCK.md`.

## 13. Test results

See **`docs/EDA-Microsegmentation-Test-Report.md`** for ping matrices and sign-off status.

| Variant | Last validated | Result |
|---------|----------------|--------|
| **D** IRB (leaf-2/3/4) | 2026-08-20 | **GO** |
| **E** StaticRoute (leaf-6/7/8) | 2026-08-20 | **GO** |
| **C** RoutedIF | 2026-08-20 | **Parked** |
| A baseline | 2026-07-31 | GO (historical) |

Rollout artifacts (gitignored): `docs/tmp/variant-d-leaf234-*`, `docs/tmp/variant-e-leaf678-*`.

**Word export:** `docs/EDA-Microsegmentation.docx` — regenerate with `bash scripts/generate-word-docs.sh` (requires pandoc).

---

*Document version: scoped D/E validation, August 2026. Repo: https://github.com/dtrichards01/eda-microsegmentation-demo*



