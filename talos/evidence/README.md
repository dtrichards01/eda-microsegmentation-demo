# GBP tag control-plane evidence (Talos #2, 2026-11-04)

Raw SR Linux output captured after all tests A–H passed. Read-only `show`/`info from state` commands.
Group map: ms-red = 5, ms-green = 6, ms-blue = 7. Summarised in
`docs/EDA-Microsegmentation-Test-Report.md` §0.8.

| File | Node | Command |
|---|---|---|
| `cap-l8-t2.txt` | srl-leaf-8 | `show network-instance default protocols bgp routes evpn route-type 2 detail` |
| `cap-l8-mac.txt` | srl-leaf-8 | `show network-instance bd-ms-enf-bd bridge-table mac-table all` |
| `cap-l1-t2.txt` | srl-leaf-1 | `show network-instance default protocols bgp routes evpn route-type 2 detail` |
| `cap-l1-t5.txt` | srl-leaf-1 | `show network-instance default protocols bgp routes evpn route-type 5 detail` |
| `cap-g1-t5.txt` | dcgw-1 | `show network-instance default protocols bgp routes evpn route-type 5 detail` |
| `cap-g3-vpn-summary.txt` | dcgw-3 | `show network-instance default protocols bgp routes l3vpn-ipv4-unicast summary` |
| `cap-g3-vpn.txt` | dcgw-3 | `show network-instance default protocols bgp routes l3vpn-ipv4-unicast prefix 172.16.120.1/32` |
| `cap-l7-t5.txt` | srl-leaf-7 | `show network-instance default protocols bgp routes evpn route-type 5 detail` |
| `cap-l7-rt.txt` | srl-leaf-7 | `info flat from state network-instance * route-table ipv4-unicast` (filtered to 172.16.120/121) |
| `cap-order-tests.txt` | EDA (dry-run txns 137206–137209) | `talos/scripts/order-tests.sh`: policy before / with / after its GroupTag, delete an in-use tag |
| `cap-g-first-packet.txt` | srl-leaf-5, srl-leaf-8 | G first packet after MAC/ARP aging: leaf-8 default deny +1, then leaf-5 red↔green +5 |
| `cap-enforcement-trace.txt` | sending + receiving leaf per test | `talos/scripts/gbp-trace.sh`: GBP ACL `matched-packets` deltas around 10 red→green pings per test (report §0.9) |
