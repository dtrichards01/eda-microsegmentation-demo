# PRE-APPLY CHECKLIST

**Authoritative scope:** `docs/VARIANT-SCOPE-LOCK.md`

| Variant | Leaves | Colours | Clients | Apply bundle |
|---------|--------|---------|---------|--------------|
| **D** | leaf-2/3/4 | blue / green / red | client2/3/4 | `_variant-d-leaf234-apply.yaml` + `labels-vnet-ms-irb.yaml` |
| **E** | leaf-6/7/8 | blue / green / red | client6/7/8 | `_variant-e-leaf678-apply.yaml` + `labels-vnet-ms-static.yaml` |

Do **not** apply full `edge-interfaces-dot1q.yaml`. Never use `nodeSelectors: role=leaf` on MS demo routers.

## 1) Field-by-field checklist

- D (`vnet-ms-irb`)
  - `variants/virtualnetworks.yaml`: `irb-ms-irb`, VLAN `85`; leaf-2=blue, leaf-3=green, leaf-4=red.
  - `variants/association-policies.yaml`: `ms-assoc-irb` — `irb-ms-irb`→gateway + three VLAN helpers.
  - `variants/labels-vnet-ms-irb.yaml`: labels on leaf-2/3/4 only.
- E (`vnet-ms-static`)
  - `variants/virtualnetworks.yaml`: `static-remote-green` (172.16.91.0/24), VLAN `90`; leaf-6=blue, leaf-7=green, leaf-8=red.
  - `variants/association-policies.yaml`: `ms-assoc-static` — static route + three VLAN helpers.
  - `variants/labels-vnet-ms-static.yaml`: labels on leaf-6/7/8 only.
- A–C, F–G (legacy catalog leaf sets — not current scoped test path)
  - See `variants/README.md` for object names; use scope lock before any apply.

## 2) Scoped apply (D or E)

```bash
NS=clab-3-tier-leaf-spine-dcgw
# Variant E example:
kubectl apply -f variants/labels-vnet-ms-static.yaml
kubectl apply -f variants/_variant-e-leaf678-apply.yaml
kubectl get virtualnetwork vnet-ms-static -n $NS -o jsonpath='{.status.nodes}{"\n"}'
# Must be subset of {leaf-6, leaf-7, leaf-8}
```

## 3) Client configure + test

```bash
python3 scripts/configure-client-ms-eth1.py --variant E --apply
python3 scripts/run-ms-tests.py E
# or: bash scripts/rollout-variant-e-leaf678.sh
```

## 4) Verify CR presence

```bash
kubectl -n clab-3-tier-leaf-spine-dcgw get virtualnetwork vnet-ms-irb vnet-ms-static
kubectl -n clab-3-tier-leaf-spine-dcgw get associationpolicy ms-assoc-irb ms-assoc-static
kubectl -n clab-3-tier-leaf-spine-dcgw get microsegmentationpolicy ms-policy-irb ms-policy-static
```
