#!/usr/bin/env python3
"""Generate talos/gate3-pod2-befg.yaml: pod-2 tests B (BridgeInterface), E (StaticRoute),
F (router enforcement target) and G (bridge-domain enforcement target, L2 only)."""
import pathlib

from ms_common import COLOURS, assoc, bd, interface, irb, policy, router, vlan, vlans, vnet, write

HERE = pathlib.Path(__file__).resolve().parent

# Port -> (DCI vnet label from gate 1, client, per-test colour labels). B uses explicit bridge interfaces, no label.
PORTS = {
    "srl-leaf-5-ethernet-1-5": ("vnet-2", "vlan-bd-2", "client-5", {"ms-enf-router": "red", "ms-enf-bd": "red"}),
    "srl-leaf-6-ethernet-1-6": ("vnet-2", "vlan-bd-2", "client-6", {"ms-static": "blue", "ms-enf-router": "blue"}),
    "srl-leaf-7-ethernet-1-5": ("vnet-4", "vlan-bd-4", "client-7", {"ms-static": "green", "ms-enf-bd": "blue"}),
    "srl-leaf-8-ethernet-1-5": ("vnet-4", "vlan-bd-4", "client-8", {"ms-static": "red", "ms-enf-router": "green",
                                                                    "ms-enf-bd": "green"}),
}

docs = [interface(n, *v) for n, v in PORTS.items()]

# B: explicit BridgeInterfaces. leaf-5 red, leaf-6 blue, leaf-7 green. VLAN 76, 172.16.76.0/24.
bis = [("red", "srl-leaf-5-ethernet-1-5"), ("blue", "srl-leaf-6-ethernet-1-6"), ("green", "srl-leaf-7-ethernet-1-5")]
docs.append(vnet("vnet-ms-bridge", "bridge-interface-association",
                 "Test B: GroupTag on explicit BridgeInterfaces. leaf-5 red (client-5), leaf-6 blue (client-6), leaf-7 green (client-7). VLAN 76.",
                 {"routers": [router("router-ms-bridge", 4131, "10.41.3.1")],
                  "bridgeDomains": [bd("bd-ms-bridge", 4132)],
                  "irbInterfaces": [irb("irb-ms-bridge", "bd-ms-bridge", "router-ms-bridge", "172.16.76.254/24")],
                  "bridgeInterfaces": [{"name": f"bi-ms-{c}", "spec": {"bridgeDomain": "bd-ms-bridge", "interface": ifc,
                                                                       "vlanID": "76"}} for c, ifc in bis]}))
docs.append(assoc("ms-assoc-bridge", "bridge-interface-association", "Test B: tags on bridge interfaces bi-ms-red/blue/green",
                  [(f"ms-{c}", {"bridgeInterfaces": [f"bi-ms-{c}"]}) for c, _ in bis]))
docs.append(policy("ms-policy-bridge", {"virtualNetworks": ["vnet-ms-bridge"]}, "bridge-interface-association",
                   "Test B policy, serviceTargets.virtualNetworks"))

# E: StaticRoute association. leaf-8 red, leaf-6 blue, leaf-7 green. VLAN 90, 172.16.90.0/24.
# 172.16.91.0/24 points at client-7 (green, 172.16.91.1 on its loopback) and is tagged green.
docs.append(vnet("vnet-ms-static", "static-route-association",
                 "Test E: GroupTag on StaticRoute 172.16.91.0/24 (next hop client-7) plus VLAN client tags. leaf-8 red (client-8), leaf-6 blue (client-6), leaf-7 green (client-7). VLAN 90.",
                 {"routers": [router("router-ms-static", 4141, "10.41.4.1")],
                  "bridgeDomains": [bd("bd-ms-static", 4142)],
                  "irbInterfaces": [irb("irb-ms-static", "bd-ms-static", "router-ms-static", "172.16.90.254/24")],
                  "vlans": vlans("vlan-ms-static", "bd-ms-static", "ms-static", 90),
                  "protocols": {"staticRoutes": [{"name": "static-ms-remote-green", "spec": {
                      "router": "router-ms-static", "prefixes": ["172.16.91.0/24"],
                      "nexthopGroup": {"nexthops": [{"ipPrefix": "172.16.90.7", "resolve": True}]}}}]}}))
docs.append(assoc("ms-assoc-static", "static-route-association",
                  "Test E: static-ms-remote-green is ms-green; VLANs tag the clients",
                  [("ms-green", {"staticRoutes": ["static-ms-remote-green"]})] +
                  [(f"ms-{c}", {"vlans": [f"vlan-ms-static-{c}"]}) for c in COLOURS]))
# No default deny for E: traffic to the static prefix is routed on the sending leaf and then bridged to the
# next hop with that leaf's IRB MAC as source. The next-hop leaf takes the source tag from its MAC table,
# where remote IRB MACs have tag 0, so a default deny drops it even with lpm-source-lookup active.
docs.append(policy("ms-policy-static", {"virtualNetworks": ["vnet-ms-static"]}, "static-route-association",
                   "Test E policy, serviceTargets.virtualNetworks; no default deny", default_deny=False))

# F: enforcement on the router only. One subnet per colour so inter-colour traffic is routed through
# router-ms-enf-router. leaf-5 red 172.16.140.0/24, leaf-6 blue .141, leaf-8 green .142. VLAN 100 on each port.
enfr = [("red", "172.16.140.254/24", 4152), ("blue", "172.16.141.254/24", 4153), ("green", "172.16.142.254/24", 4154)]
docs.append(vnet("vnet-ms-enf-router", "enforcement-router-target",
                 "Test F: VLAN client tags, MicroSegmentationPolicy serviceTargets.routers. One subnet per colour: leaf-5 red 172.16.140/24 (client-5), leaf-6 blue 172.16.141/24 (client-6), leaf-8 green 172.16.142/24 (client-8). VLAN 100.",
                 {"routers": [router("router-ms-enf-router", 4151, "10.41.5.1")],
                  "bridgeDomains": [bd(f"bd-ms-enf-router-{c}", evi) for c, _, evi in enfr],
                  "irbInterfaces": [irb(f"irb-ms-enf-router-{c}", f"bd-ms-enf-router-{c}", "router-ms-enf-router", p)
                                    for c, p, _ in enfr],
                  "vlans": [vlan(f"vlan-ms-enf-router-{c}", f"bd-ms-enf-router-{c}", "ms-enf-router", c, 100)
                            for c, _, _ in enfr]}))
docs.append(assoc("ms-assoc-enf-router", "enforcement-router-target", "Test F: tags on VLANs vlan-ms-enf-router-red/blue/green",
                  [(f"ms-{c}", {"vlans": [f"vlan-ms-enf-router-{c}"]}) for c in COLOURS]))
docs.append(policy("ms-policy-enf-router", {"routers": ["router-ms-enf-router"]}, "enforcement-router-target",
                   "Test F policy, serviceTargets.routers only"))

# G: L2 only, enforcement on the bridge domain. leaf-5 red, leaf-7 blue, leaf-8 green. VLAN 110, 172.16.110.0/24.
docs.append(vnet("vnet-ms-enf-bd", "enforcement-bridge-domain-target",
                 "Test G: L2-only bridge domain, MicroSegmentationPolicy serviceTargets.bridgeDomains. leaf-5 red (client-5), leaf-7 blue (client-7), leaf-8 green (client-8). VLAN 110.",
                 {"bridgeDomains": [bd("bd-ms-enf-bd", 4162)],
                  "vlans": vlans("vlan-ms-enf-bd", "bd-ms-enf-bd", "ms-enf-bd", 110)}))
docs.append(assoc("ms-assoc-enf-bd", "enforcement-bridge-domain-target", "Test G: tags on VLANs vlan-ms-enf-bd-red/blue/green",
                  [(f"ms-{c}", {"vlans": [f"vlan-ms-enf-bd-{c}"]}) for c in COLOURS]))
docs.append(policy("ms-policy-enf-bd", {"bridgeDomains": ["bd-ms-enf-bd"]}, "enforcement-bridge-domain-target",
                   "Test G policy, serviceTargets.bridgeDomains only (L2)"))

write(HERE / "gate3-pod2-befg.yaml", "# Gate 3: pod-2 tests B, E, F, G. Generated by gen-gate3.py.", docs)
