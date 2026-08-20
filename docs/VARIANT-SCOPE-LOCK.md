# Variant scope lock (authoritative)

This document overrides older tables in `docs/CLAB-3-TIER-TOPOLOGY.md` and any agent notes that used leaf-1/2/3 or client1/2/3 for the current MS test.

## Active scopes

| Phase | Variant | Leaves (max 3) | Clients | Leaf colours |
|-------|---------|----------------|---------|--------------|
| **IRB test (done)** | **D** | `leaf-2`, `leaf-3`, `leaf-4` | `client2`, `client3`, `client4` | leaf-2=**blue**, leaf-3=**green**, leaf-4=**red** |
| **Static route test (current)** | **E** | `leaf-6`, `leaf-7`, `leaf-8` | `client6`, `client7`, `client8` | leaf-6=**blue**, leaf-7=**green**, leaf-8=**red** |

**Never** build a single `vnet-ms-*` VirtualNetwork (or matching `ms-assoc-*` / `ms-policy-*`) across all eight leafs or spanning both groups.

## Client to leaf mapping (verify in lab)

| Client | Leaf | Colour | Variant D IP (`eth1.85`) | Variant E IP (`eth1.90`) |
|--------|------|--------|--------------------------|--------------------------|
| client2 | leaf-2 | blue | `172.16.85.2/24` | — |
| client3 | leaf-3 | green | `172.16.85.3/24` | — |
| client4 | leaf-4 | red | `172.16.85.4/24` | — |
| client6 | leaf-6 | blue | — | `172.16.90.6/24` |
| client7 | leaf-7 | green | — | `172.16.90.7/24` |
| client8 | leaf-8 | red | — | `172.16.90.8/24` |

Gateway: Variant D `172.16.85.254`; Variant E `172.16.90.254`.  
Variant E static-route test prefix: `172.16.91.0/24` (tagged green via `static-remote-green`).

Stock `CLAB-3-TIER-TOPOLOGY.md` still lists client4→leaf-5; **this file is authoritative** for MS variant work.

## Rules

1. **Three leaves maximum** per MS variant service (`vnet-ms-*` + policies).
2. **Do not change** service or host IP addresses without explicit user approval.
3. **Do not delete** client subinterfaces on hosts; cluster/host changes are additive only on clients.
4. **Never** use `nodeSelectors: [eda.nokia.com/role=leaf]` on MS demo routers (causes 8-leaf blowout).
5. **Do not redeploy** variants until the user requests; except scoped apply per phase above.

## Pre-apply gate (required)

Before `kubectl apply` of any MS variant manifest, confirm VirtualNetwork node lists are a subset of the allowed leaves for that phase:

```bash
NS=clab-3-tier-leaf-spine-dcgw
# Variant D: ALLOWED='leaf-2 leaf-3 leaf-4'
# Variant E: ALLOWED='leaf-6 leaf-7 leaf-8'
ALLOWED='leaf-6 leaf-7 leaf-8'
for vn in vnet-ms-static; do
  nodes=$(kubectl get virtualnetwork "$vn" -n "$NS" -o jsonpath='{.status.nodes}{"\n"}' 2>/dev/null)
  [ -z "$nodes" ] && continue
  for n in $nodes; do
    echo "$vn $n"
  done
done | while read vn n; do
  case $n in leaf-6|leaf-7|leaf-8) ;; *) echo "BLOCK: $vn node $n not in ALLOWED"; esac
done
```

## Forbidden apply

- **Never** apply the full `variants/edge-interfaces-dot1q.yaml` (labels all eight leafs).
- Use leaf-scoped label snippets only: `labels-vnet-ms-irb.yaml` (D) or `labels-vnet-ms-static.yaml` (E).

## Apply manifests

| Variant | Labels | Apply bundle |
|---------|--------|--------------|
| D | `variants/labels-vnet-ms-irb.yaml` | `variants/_variant-d-leaf234-apply.yaml` |
| E | `variants/labels-vnet-ms-static.yaml` | `variants/_variant-e-leaf678-apply.yaml` |

## Cleanup baseline (2026-02-20)

All cluster `vnet-ms-*`, `ms-assoc-*`, and `ms-policy-*` objects were removed once during scope cleanup. See `docs/CLEANUP-SNAPSHOT-2026-02-20.md`.
