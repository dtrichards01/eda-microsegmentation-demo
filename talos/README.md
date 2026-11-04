# Talos #2 replication (tests A–H)

The WSL microsegmentation tests A–G, plus a cross-DC test H, rebuilt on the Talos #2 lab alongside the DCI,
firewall and tenancy projects that share it. Results and findings: `docs/EDA-Microsegmentation-Test-Report.md` §0.

| Item | Value |
|------|-------|
| Server | k0r4, `nokia@100.124.186.51` (containerlab 0.82.0, topology `/home/nokia/3-tier-dci/clab-s-spine-spine-leaf-srl-only.yaml`) |
| EDA | `https://100.124.186.55` |
| Namespaces | `clab-srl-leaf-spine-dcgw` (pods 1 and 2, dcgw-1/2), `clab-srl-dcgw-wan` (dcgw-3/4, WAN) |
| Leaves | srl-leaf-1..4 (pod-1 / DC1), srl-leaf-5..8 (pod-2 / DC2); 7220 IXR-D2L/D3L, SR Linux 26.7.1 |
| Group tags | `ms-red`=5, `ms-blue`=7, `ms-green`=6, `ms-gateway`=4 (Global scope; the firewall uses `eda-*`) |
| Numbering | EVI/VNI 4101–4199 (`target:1:<evi>`); DCI uses 100–111, the firewall 3101–3212 |

## Last result (2026-11-04)

All 66 checks pass and the other projects' regression has 0 failures:
A 8/8, B 8/8, C 8/8, D 8/8, E 10/10, F 8/8, G 6/6, H 10/10.

## Layout

| Path | Purpose |
|------|---------|
| `ms_common.py` | Shared CR builders used by the generators |
| `gate1-edge-dot1q.yaml`, `gate1-rollback.yaml` | Client ports to Dot1q, DCI services on VLANs 101–105 (and its rollback) |
| `gen-gate2.py` → `gate2-pod1-acd.yaml` | Tags plus pod-1 tests A, C, D |
| `gen-gate3.py` → `gate3-pod2-befg.yaml` | Pod-2 tests B, E, F, G |
| `gen-gate4.py` → `gate4-dci-h.yaml` | Cross-DC test H: two VNETs and a RouterInterconnect on each DC gateway pair |
| `extract-default-deny.py` → `default-deny-cf.yaml` | C and F policies with the default deny (apply only after the leaf reboots) |
| `extract-fix-c.py` → `fix-c-policy.yaml` | Historical: C without default deny (before the root cause was found) |
| `gen-probe-implicit.py` → `probe-g-*.yaml` | Historical: the probe proving there is no implicit deny |
| `snapshot-2026-11-03/` | Live CRs before gate 1 (rollback reference) |
| `scripts/ms-tests.sh` | `setup` / `test` for A–H on k0r4; exit code = failed checks |
| `scripts/regression-other-projects.sh` | Read-only DCI, firewall and tenancy checks |
| `scripts/txn-diff.sh` | Summarise a dry-run transaction and flag lines touching other projects |
| `scripts/leaf-reboot.sh` | Reboot one containerlab leaf and repair what the reboot breaks (below) |
| `scripts/dci-clients-to-vlan.sh` | Gate 1 client move (DCI clients to `eth1.<vlan>`) |

Every change was dry-run with `eda-dci-lab/scripts/eda-txn.py` (copied to k0r4 `/tmp`) and committed only after
review: `python3 eda-txn.py <file> [--commit] --desc '...'`.

## Transactions

| Transaction | Change |
|-------------|--------|
| 136211 | Gate 1: client ports Dot1q, DCI on VLANs 101–105 |
| 136219 | Gate 2: tags, A, C, D |
| 136225 | C without default deny (workaround, superseded) |
| 136233 | Gate 3: B, E, F, G |
| 136682 / 136683 | Implicit-deny probe on G, then restore |
| 136806 | Default deny back on C, E, F (after all leaves rebooted) |
| 136818 | E back to no default deny (see the test report for why) |
| 136821 | Gate 4: test H |
| 136865 | Delete unused GroupTag `ms-remote` (`delete-ms-remote.yaml`) |

## Leaf reboot (`lpm-source-lookup`)

EDA configures `platform resource-management group-based-policy lpm-source-lookup true`, but SR Linux only
activates it after a chassis reboot. Until then, a routed packet arriving from VXLAN gets source tag 0 and a
default deny drops it. Check with:

```bash
docker exec srl-leaf-N sr_cli -e "info from state platform resource-management group-based-policy"
# want: lpm-source-lookup true, chassis-reboot-required false
```

In containerlab the reboot stops the container, which deletes its veth links and the client-side interfaces
(VLAN subinterfaces, bond membership, addresses, routes). `docker start` also puts the management IP back on the
container's own `mgmt0`, which then refuses EDA's gNMI (57410) and leaves the node NotSynced. `leaf-reboot.sh`
handles all of this:

```bash
bash leaf-reboot.sh plan srl-leaf-N   # read-only: links, far ends, client state to replay; STOP on unknown far ends
bash leaf-reboot.sh run  srl-leaf-N   # plan, reboot, docker start, recreate links, remove stray mgmt0 IP,
                                      # wait for BGP, replay clients, wait for a Synced state newer than the reboot
```

- Container links are recreated with `containerlab tools veth create` (setuid root, so no sudo needed).
- Host bridge links (leaf-1..4 `e1-30` to the firewall bridges) use the `bridge:<br>:<if>` endpoint. The host end
  keeps its own MTU (9500) through a throwaway privileged `network-multitool` container on the host network.
- Client replay uses `docker exec --privileged`, because the `tnt-port-*` containers lack `NET_ADMIN`.
- One leaf at a time, then `ms-tests.sh test A B C D E F G H` and `regression-other-projects.sh`. All eight leaves
  were rebooted this way on 2026-11-04 (about 70 s each).
