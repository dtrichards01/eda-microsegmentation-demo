# EDA Microsegmentation — Test Report

**Last updated:** 2026-08-20  
**Lab:** `3-tier-leaf-spine-dcgw` (clab on WSL)  
**EDA:** `kind-eda-demo-wsl2` — https://127.0.0.1:9443  
**Namespace:** `clab-3-tier-leaf-spine-dcgw`  
**Repo:** https://github.com/dtrichards01/eda-microsegmentation-demo  
**Policy intent (all variants):** red↔blue allow, blue↔green allow, red↔green drop, same-group allow, implicit default deny  

![Policy intent](diagrams/policy-rules.png){width=6.5in}

**Scope authority:** `docs/VARIANT-SCOPE-LOCK.md` — max **3 leaves** per `vnet-ms-*`; never span all eight leaves.

---

## 1. Executive summary (2026-08-20)

| Variant | Scope | Association | Result | Notes |
|---------|-------|-------------|--------|-------|
| **D** IRB | leaf-2/3/4 | IRB + VLAN helpers | **GO** | Full GBP matrix after 4-entry `ms-assoc-irb` |
| **E** StaticRoute | leaf-6/7/8 | StaticRoute + VLAN | **GO** | Includes red→`172.16.91.1` static-prefix deny |
| **C** RoutedIF | leaf-5/6/7 | RoutedInterface | **PARKED** | Policy on → all cross-subnet fails (platform?) |
| **A** VLAN | leaf-1/2/3 | VLAN | **GO** (historical) | July 2026 baseline |
| **B, F, G** | catalog | various | **Not re-validated** | See §6 historical run |

**Key findings (Aug 2026):**

1. **Variant D** requires **both** `irb-ms-irb`→gateway **and** VLAN→red/blue/green in `ms-assoc-irb`. IRB-only association blocks all inter-host traffic; gateway ping still works.
2. **Variant E** tags `172.16.91.0/24` green via `static-remote-green` (blackhole); client tags via VLAN; standard host matrix + prefix deny validated.
3. **Never** use `nodeSelectors: [eda.nokia.com/role=leaf]` on MS demo routers — causes 8-leaf scope blowout.
4. **Never** apply full `variants/edge-interfaces-dot1q.yaml` — use scoped label snippets only.

Apply bundles: `variants/_variant-d-leaf234-apply.yaml`, `variants/_variant-e-leaf678-apply.yaml`.

---

## 2. Test environment (current)

### Scoped client ↔ leaf mapping (validated)

| Phase | Client | Leaf | Colour | Interface | Subnet / VLAN |
|-------|--------|------|--------|-----------|---------------|
| **D** | client2 | leaf-2 | blue | `eth1.85` | `172.16.85.2/24` |
| **D** | client3 | leaf-3 | green | `eth1.85` | `172.16.85.3/24` |
| **D** | client4 | leaf-4 | red | `eth1.85` | `172.16.85.4/24` |
| **E** | client6 | leaf-6 | blue | `eth1.90` | `172.16.90.6/24` |
| **E** | client7 | leaf-7 | green | `eth1.90` | `172.16.90.7/24` |
| **E** | client8 | leaf-8 | red | `eth1.90` | `172.16.90.8/24` |

Gateways: D `172.16.85.254`, E `172.16.90.254`. Client IP last octet = client number.

Docker container names: `clientN` (not `clab-*-clientN`) in WSL clab.

### Variant catalog (Dot1q VLAN IDs — current manifests)

| ID | VLAN | VirtualNetwork | AssociationPolicy | MicroSegmentationPolicy |
|----|------|----------------|-------------------|-------------------------|
| A | 75 | `vnet-ms-vlan` | `ms-assoc-vlan` | `ms-policy-vlan` |
| B | 75 | `vnet-ms-bridge` | `ms-assoc-bridge` | `ms-policy-bridge` |
| C | 80/81/82 | `vnet-ms-routed` | `ms-assoc-routed` | `ms-policy-routed` |
| D | 85 | `vnet-ms-irb` | `ms-assoc-irb` | `ms-policy-irb` |
| E | 90 | `vnet-ms-static` | `ms-assoc-static` | `ms-policy-static` |
| F | 100 | `vnet-ms-enf-router` | `ms-assoc-enf-router` | `ms-policy-enf-router` |
| G | 110 | `vnet-ms-enf-bd` | `ms-assoc-enf-bd` | `ms-policy-enf-bd` |

---

## 3. Test method

1. **Labels:** leaf-scoped Interface CR labels (`variants/labels-vnet-ms-irb.yaml` or `labels-vnet-ms-static.yaml`).
2. **Apply:** scoped apply bundle (not full `virtualnetworks.yaml` without scope review).
3. **Pre-apply gate:** `kubectl get virtualnetwork <vn> -o jsonpath='{.status.nodes}'` ⊆ allowed leaves (3 max).
4. **Clients:** `scripts/configure-client-ms-eth1.py --variant D|E --apply` or manual `eth1.<vlan>`.
5. **Ping:** `docker exec clientN ping -I eth1.<vlan> -c 3 -W 2 <dest>`.
6. **Pass criteria:** Allow = 0% loss; Drop = 100% loss.

Automated: `python3 scripts/run-ms-tests.py D E`

---

## 4. Results — Variant D (2026-08-20, **GO**)

**Service:** `vnet-ms-irb` on **leaf-2, leaf-3, leaf-4** only (`numNodes: 3`, `operationalState: Up`).

**Association (`ms-assoc-irb`):**

| Target | GroupTag |
|--------|----------|
| `irb-ms-irb` | gateway |
| `vlan-ms-irb-red` | red |
| `vlan-ms-irb-blue` | blue |
| `vlan-ms-irb-green` | green |

**Enforcement:** `ms-policy-irb` → `virtualNetworks: [vnet-ms-irb]`. L3 decisions at IRB; VLAN entries classify clients at ingress.

| Test | From → To | Expected | Result |
|------|-----------|----------|--------|
| red → blue | client4 → `172.16.85.2` | Allow | **PASS** (3/3) |
| red → green | client4 → `172.16.85.3` | Drop | **PASS** (0/3) |
| blue → green | client2 → `172.16.85.3` | Allow | **PASS** (3/3) |
| blue → red | client2 → `172.16.85.4` | Allow | **PASS** (3/3) |
| green → blue | client3 → `172.16.85.2` | Allow | **PASS** (3/3) |
| green → red | client3 → `172.16.85.4` | Drop | **PASS** (0/3) |
| → gateway | all → `172.16.85.254` | Allow | **PASS** (3/3 each) |

**Failure mode (earlier same day):** IRB-only association (gateway entry without VLAN helpers) → all inter-host ALLOW paths failed; gateway ping passed. Fixed by restoring 4-entry association.

---

## 5. Results — Variant E (2026-08-20, **GO**)

**Service:** `vnet-ms-static` on **leaf-6, leaf-7, leaf-8** only (`numNodes: 3`, `operationalState: Up`).

**Association (`ms-assoc-static`):**

| Target | GroupTag |
|--------|----------|
| `static-remote-green` | green (prefix `172.16.91.0/24`, blackhole) |
| `vlan-ms-static-red` | red |
| `vlan-ms-static-blue` | blue |
| `vlan-ms-static-green` | green |

**Enforcement:** `ms-policy-static` → `virtualNetworks: [vnet-ms-static]`.

| Test | From → To | Expected | Result |
|------|-----------|----------|--------|
| red → blue | client8 → `172.16.90.6` | Allow | **PASS** (3/3) |
| red → green | client8 → `172.16.90.7` | Drop | **PASS** (0/3) |
| blue → green | client6 → `172.16.90.7` | Allow | **PASS** (3/3) |
| blue → red | client6 → `172.16.90.8` | Allow | **PASS** (3/3) |
| green → blue | client7 → `172.16.90.6` | Allow | **PASS** (3/3) |
| green → red | client7 → `172.16.90.8` | Drop | **PASS** (0/3) |
| blue → gateway | client6 → `172.16.90.254` | Allow | **PASS** (3/3) |
| red → static prefix | client8 → `172.16.91.1` | Drop | **PASS** (0/3) |

Static-route test: destination tagged **green** via `static-remote-green`; red↔green policy drops even though prefix is blackhole.

---

## 6. Variant C — parked (2026-08-20)

**Symptom:** Phase 1 (no `ms-policy-routed`) — cross-subnet pings pass. Phase 2 (policy on) — **all** cross-subnet fails, including red→blue Allow.

**Conclusion:** Not fixable with YAML alone in this lab; reported as likely platform limitation on routed-interface GBP. Do not use for sign-off until Nokia/platform fix.

Details: `docs/tmp/variant-c-policy-fix-20260820-120141/SUMMARY.md`

---

## 7. Summary matrix (Aug 2026 validation)

| Variant | Scope | EDA Up (3 nodes) | GBP matrix | Policy verified? |
|---------|-------|------------------|------------|------------------|
| **D** IRB | leaf-2/3/4 | Yes | **Pass** | **Yes** |
| **E** StaticRoute | leaf-6/7/8 | Yes | **Pass** | **Yes** |
| **C** RoutedIF | leaf-5/6/7 | Yes | Fail (with policy) | **Parked** |
| A–B, F–G | catalog | — | Not re-run Aug 2026 | See §8 |

---

## 8. Historical run (2026-07-31) — superseded for D/E

An earlier automated run used VLAN **101–108** on `eth1.101`–`eth1.108`, different client/leaf mapping, and reported **FAIL** for Variants D and E (routing/scope issues). That run predates:

- Scoped 3-leaf apply bundles
- Correct Dot1q VLAN **85** (D) and **90** (E)
- 4-entry `ms-assoc-irb` (VLAN + IRB)
- Removal of `nodeSelectors: role=leaf` on MS routers

Raw JSON (historical): `test-results/test-results-full-2026-07-31-v3.json`

| Variant | Jul 2026 result | Aug 2026 status |
|---------|-----------------|-----------------|
| A VLAN | **Pass** | Still valid baseline |
| B BridgeIF | Fail (EVPN host route) | Not re-tested |
| C RoutedIF | Fail | **Parked** (confirmed Aug) |
| D IRB | Fail | **GO** (scoped re-test) |
| E StaticRoute | Partial | **GO** (scoped re-test) |
| F, G | Fail | Not re-tested |

---

## 9. How to reproduce (current)

```bash
cd /mnt/c/Users/darrenri/Documents/eda-microsegmentation-demo

# Variant D
kubectl apply -f variants/labels-vnet-ms-irb.yaml
kubectl apply -f variants/_variant-d-leaf234-apply.yaml
python3 scripts/configure-client-ms-eth1.py --variant D --apply
python3 scripts/run-ms-tests.py D

# Variant E
kubectl apply -f variants/labels-vnet-ms-static.yaml
kubectl apply -f variants/_variant-e-leaf678-apply.yaml
python3 scripts/configure-client-ms-eth1.py --variant E --apply
python3 scripts/run-ms-tests.py E
```

---

## 10. Conclusions

1. **Variants D and E** validate the full red/blue/green GBP intent on **scoped 3-leaf** deployments (Aug 2026).
2. **Association vs policy:** Association classifies (VLAN, IRB, StaticRoute); policy enforces between GroupTags. Missing VLAN associations on D blocks inter-host traffic even when gateway works.
3. **Variant C** remains **parked** for routed-interface GBP.
4. **Operational rules:** 3-leaf max, no `role=leaf` router selectors, scoped label files only, pre-apply `status.nodes` gate.

Architecture and per-variant design: `docs/EDA-Microsegmentation.md` §12.4.

---

*Report updated 2026-08-20 after scoped Variant D/E validation. Supersedes July 2026 sections for D and E.*
