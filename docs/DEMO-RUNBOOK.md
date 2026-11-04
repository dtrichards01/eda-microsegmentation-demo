# EDA microsegmentation demo runbook (Talos #2)

A walk-through of how GroupTags, AssociationPolicies and MicroSegmentationPolicies build microsegmentation,
in the order they depend on each other. It uses the live tests built on Talos #2 (results:
`docs/EDA-Microsegmentation-Test-Report.md` §0). Steps 1–6 and 8–9 only read state, send pings or run dry-run
transactions; nothing is committed. Step 7 has an optional live change that needs approval on the day.

| Item | Value |
|------|-------|
| Server | k0r4, `ssh nokia@100.124.186.51` |
| EDA UI | `https://100.124.186.55` |
| Namespace | `clab-srl-leaf-spine-dcgw` |
| Main example | Test A, VLAN 75, subnet 172.16.75.0/24: client-1 red on leaf-1, client-2 blue on leaf-2, client-3 green on leaf-3 |
| Colours | `ms-red` = 5, `ms-green` = 6, `ms-blue` = 7 |

## 0. Preparation (before the audience arrives)

Copy the tools to `/tmp` on k0r4; `/tmp` does not survive a reboot.

```bash
# from the repo root on the laptop
scp talos/scripts/{ms-tests.sh,gbp-trace.sh,order-tests.sh,txn-diff.sh} nokia@100.124.186.51:/tmp/
scp ../eda-dci-lab/scripts/eda-txn.py nokia@100.124.186.51:/tmp/
ssh nokia@100.124.186.51
cd /tmp && NS=clab-srl-leaf-spine-dcgw
bash ms-tests.sh test A B C D E F G H     # expect 66/66, exit code 0
```

Shorthand used below: `cli N '<command>'` means `docker exec srl-leaf-N sr_cli -e '<command>'`.

```bash
cli() { docker exec srl-leaf-$1 sr_cli -e "$2"; }
```

## 1. The service and the labels

Message: labels only choose which ports get each VLAN subinterface. They do not set the colour.

```bash
kubectl -n $NS get virtualnetworks.services.eda.nokia.com vnet-ms-vlan \
  -o jsonpath='{range .spec.vlans[*]}{.name}{"  vlan "}{.spec.vlanID}{"  "}{.spec.interfaceSelectors}{"\n"}{end}'
kubectl -n $NS get interfaces.interfaces.eda.nokia.com srl-leaf-2-ethernet-1-6 -o jsonpath='{.metadata.labels}'; echo
```

- `vnet-ms-vlan` has three VLAN entries, all VLAN 75, each selecting ports with one label:
  `eda.nokia.com/ms-vlan=red|blue|green`.
- leaf-2 `ethernet-1/6` carries `ms-vlan=blue` next to other services' labels (`ms-irb=blue`, `vnet-1=…`). One
  label key per service, so a port can be a different colour in each service.
- BridgeInterface (B) and RoutedInterface (C) name the port directly and need no label.

## 2. Identity: GroupTags

Message: a GroupTag is just a named identity. EDA allocates its number.

```bash
kubectl -n $NS get grouptags.microsegmentation.eda.nokia.com ms-red -o jsonpath='{.spec}'; echo
cli 1 'info flat network-instance bd-ms-vlan group-based-policy group *' | grep tag-value
```

- The spec is only a description and a scope (Global).
- On the leaf each tag becomes `group ms-red tag-value 5` inside every network-instance in scope.

## 3. Dependency order, live with dry-runs

Message: GroupTag first; the platform enforces it. Building everything in one transaction is the practical way.

```bash
bash order-tests.sh 2    # policy naming a missing tag    -> FAILED: missing dependency of type Group tag
bash order-tests.sh 3    # same policy + its GroupTag      -> OK, EDA allocates tag-value 8
bash order-tests.sh 4    # delete ms-green while in use    -> FAILED, every policy using it reports it
```

All three are dry-runs (`eda-txn.py` without `--commit`). Show the transactions in the EDA UI transaction
list as well. Reference output: `talos/evidence/cap-order-tests.txt`.

## 4. Classification: AssociationPolicy

Message: the tag lands on a subinterface, not the port; the AssociationPolicy filters nothing by itself.

```bash
kubectl -n $NS get associationpolicies.microsegmentation.eda.nokia.com ms-assoc-vlan -o yaml | sed -n '/^spec:/,/^status:/p'
cli 2 'info flat network-instance bd-ms-vlan group-based-policy interface *'
```

- Each VLAN object is bound to one GroupTag (`vlan-ms-vlan-blue` → `ms-blue`).
- On leaf-2: `interface ethernet-1/6.75 group [ ms-blue ]`.
- Other targets in this lab: BridgeInterface (B), RoutedInterface (C), IRB for the gateway (D), StaticRoute
  prefix (E).

## 5. The control plane carries the tags

Message: the tag travels in BGP EVPN as the `gbp-tag` community, not in the VXLAN packet. Every leaf learns
remote hosts' colours from it.

```bash
cli 3 'show network-instance default protocols bgp routes evpn route-type 2 detail' | grep -B14 'gbp-tag:0:5' | head -30
cli 3 'show network-instance bd-ms-vlan bridge-table mac-table all'
```

- The type-2 route for client-1 (red) carries `Communities: [target:1:4122, gbp-tag:0:5, bgp-tunnel-encap:VXLAN]`.
  In A these are MAC-only routes (`IP Address: 0.0.0.0`).
- The MAC table's GBP Tags column shows client-1's MAC (type `evpn`, via `vxlan0.520`) as `5 (ms-red)`, and the
  local green client (`learnt` on `ethernet-1/5.75`) as `6 (ms-green)`. leaf-3 has no local config for the red MAC.
- The other leaves' IRB MACs (type `evpn-static`) show tag `0`. That is why routed-then-bridged traffic in test E
  cannot use a default deny (report §0.5).
- Config that enables it, from the AssociationPolicy: `protocols bgp-evpn bgp-instance 1 group-based-policy
  add-community true` and `install-from-community true`.
- Reference output: `talos/evidence/cap-l8-t2.txt`, `cap-l8-mac.txt`; report §0.8.

## 6. Enforcement: MicroSegmentationPolicy

Message: the policy becomes an ACL in the network-instances of its target. A packet is checked by the first one
it enters, on the sending leaf.

```bash
kubectl -n $NS get microsegmentationpolicies.microsegmentation.eda.nokia.com ms-policy-vlan -o yaml | sed -n '/^spec:/,/^status:/p'
cli 1 'info flat network-instance bd-ms-vlan group-based-policy acl' | grep description
bash ms-tests.sh test A       # 8/8: four allows, red<->green dropped, gateway pings
bash gbp-trace.sh A           # leaf-1 bd-ms-vlan entry 55 "block red to/from green" +10
```

- `serviceTargets: virtualNetworks [vnet-ms-vlan]` puts the same ACL in both `bd-ms-vlan` and `router-ms-vlan`.
- Red and green share the subnet, so the traffic is bridged and the bridge domain on leaf-1 drops it. The
  receiving leaf never sees it.
- Gateway pings go to the CPU and bypass the ACL: they prove reachability, not policy.

## 7. No implicit deny

Message: without a final `default deny` entry, any pair with no rule is forwarded.

- Show the last entry of `ms-policy-vlan`: `default deny`. It is a normal entry you add yourself.
- Optional live proof (changes config; get approval on the day): the probe used in testing removes G's
  blue↔green allow and its default deny, shows blue↔green still passing, then restores G
  (`talos/gen-probe-implicit.py` → `probe-g-*.yaml`; historic transactions 136682 / 136683).
- Without a live change, tell the story from report §0.4. The G first-packet case also fits here: after the MAC
  entries age out, one flooded packet reached the receiving leaf with an unknown source tag and only the default
  deny stopped it (`talos/evidence/cap-g-first-packet.txt`).

## 8. Choosing where the policy is enforced

Message: the policy target decides where the ACL lives; the association target only decides the tag.

```bash
bash ms-tests.sh test F G
bash gbp-trace.sh C D E F G
```

| Test | Target | Dropped by (sending leaf) |
|------|--------|---------------------------|
| C | VirtualNetwork, routed only | router `router-ms-routed` |
| D | VirtualNetwork, IRB gateway tagged | bridge domain `bd-ms-irb` (clients share a subnet) |
| E | VirtualNetwork + StaticRoute tag | hosts: `bd-ms-static`; static prefix: router `router-ms-static` |
| F | Router only | router `router-ms-enf-router`; the per-colour bridge domains have no ACL |
| G | BridgeDomain only (L2) | bridge domain `bd-ms-enf-bd` |

## 9. Across data centres (H)

Message: tags survive the DC gateways' EVPN → IPVPN → EVPN re-origination, so one policy spans both DCs and the
drop still happens before the DCI.

```bash
docker exec dcgw-3 sr_cli -e 'show network-instance default protocols bgp routes l3vpn-ipv4-unicast prefix 172.16.120.1/32' | grep Communities
cli 7 'info flat from state network-instance router-ms-dci-2 route-table ipv4-unicast' \
  | grep -E '172\.16\.120\.[13]/32 .*group-based-policy-tag'
bash ms-tests.sh test H       # 10/10
bash gbp-trace.sh H           # leaf-1 router-ms-dci-1 entry 55 +10, nothing on leaf-7
```

- dcgw-3's IPVPN route still carries `gbp-tag:0:5`; the gateways have no group-based policy config.
- leaf-7 in DC2 installs DC1's hosts as `/32`s with their tags (`hostRoutePopulate.dynamic` on the IRBs).
- Reference output: report §0.6 and §0.8.

## Wrap-up

| Object | Created | Does |
|--------|---------|------|
| VirtualNetwork + interface labels | First | Builds the service; labels pick the ports |
| GroupTag | Before anything that names it | Identity; EDA allocates the number |
| AssociationPolicy | After its GroupTags | Tags subinterfaces / IRB / prefixes and turns on the EVPN `gbp-tag` community |
| MicroSegmentationPolicy | After its GroupTags | Ordered allow/drop entries, installed as an ACL in the target's network-instances |

Delete in reverse: policies first, GroupTags last.
