#!/usr/bin/env python3
"""Generate talos/gate2-pod1-acd.yaml: ms-* GroupTags + pod-1 tests A (VLAN), C (routed), D (IRB+VLAN)."""
import pathlib

from ms_common import MS, assoc, bd, interface, irb, md, policy, router, vlans, vnet, write

HERE = pathlib.Path(__file__).resolve().parent

# Port -> (DCI vnet label, client) from gate 1, plus the per-test colour labels added here.
PORTS = {
    "srl-leaf-1-ethernet-1-5": ("vnet-1", "vlan-bd-1", "client-1", {"ms-vlan": "red"}),
    "srl-leaf-2-ethernet-1-6": ("vnet-1", "vlan-bd-1", "client-2", {"ms-vlan": "blue", "ms-irb": "blue"}),
    "srl-leaf-3-ethernet-1-5": ("vnet-3", "vlan-bd-3", "client-3", {"ms-vlan": "green", "ms-irb": "green"}),
    "srl-leaf-4-ethernet-1-5": ("vnet-5", "vlan-bd-5", "client-4", {"ms-irb": "red"}),
}

TAGS = {
    "ms-red": "Microsegmentation demo red group",
    "ms-blue": "Microsegmentation demo blue group",
    "ms-green": "Microsegmentation demo green group",
    "ms-gateway": "Microsegmentation demo gateway IRB",
}

docs = []
docs += [{"apiVersion": MS, "kind": "GroupTag", "metadata": md(n), "spec": {"description": d, "scope": "Global"}}
         for n, d in TAGS.items()]
docs += [interface(n, *v) for n, v in PORTS.items()]

# A: VLAN association. leaf-1 red, leaf-2 blue, leaf-3 green. VLAN 75, 172.16.75.0/24.
docs.append(vnet("vnet-ms-vlan", "vlan-association",
                 "Test A: GroupTag on VLAN. leaf-1 red (client-1), leaf-2 blue (client-2), leaf-3 green (client-3). VLAN 75.",
                 {"routers": [router("router-ms-vlan", 4101, "10.41.0.1")],
                  "bridgeDomains": [bd("bd-ms-vlan", 4102)],
                  "irbInterfaces": [irb("irb-ms-vlan", "bd-ms-vlan", "router-ms-vlan", "172.16.75.254/24")],
                  "vlans": vlans("vlan-ms-vlan", "bd-ms-vlan", "ms-vlan", 75)}))
docs.append(assoc("ms-assoc-vlan", "vlan-association", "Test A: tags on VLANs vlan-ms-vlan-red/blue/green",
                  [(f"ms-{c}", {"vlans": [f"vlan-ms-vlan-{c}"]}) for c in ("red", "blue", "green")]))
docs.append(policy("ms-policy-vlan", {"virtualNetworks": ["vnet-ms-vlan"]}, "vlan-association",
                   "Test A policy, serviceTargets.virtualNetworks"))

# C: RoutedInterface association. leaf-1 red 172.16.80.1, leaf-2 blue 172.16.81.1, leaf-4 green 172.16.82.1. VLAN 80.
routed = [("red", "srl-leaf-1-ethernet-1-5", "172.16.80.1/24"),
          ("blue", "srl-leaf-2-ethernet-1-6", "172.16.81.1/24"),
          ("green", "srl-leaf-4-ethernet-1-5", "172.16.82.1/24")]
docs.append(vnet("vnet-ms-routed", "routed-interface-association",
                 "Test C: GroupTag on RoutedInterface (L3 handoff, no BD/IRB). leaf-1 red, leaf-2 blue, leaf-4 green. VLAN 80.",
                 {"routers": [router("router-ms-routed", 4111, "10.41.1.1")],
                  "routedInterfaces": [{"name": f"ri-ms-{c}", "spec": {
                      "interface": ifc, "router": "router-ms-routed", "vlanID": "80", "ipMTU": 1500,
                      "ipv4Addresses": [{"ipPrefix": p, "primary": True}],
                      "ipv4": {"arpTimeoutSeconds": 14400, "learnUnsolicitedARP": "Disabled"}}}
                      for c, ifc, p in routed]}))
docs.append(assoc("ms-assoc-routed", "routed-interface-association", "Test C: tags on routed interfaces ri-ms-red/blue/green",
                  [(f"ms-{c}", {"routedInterfaces": [f"ri-ms-{c}"]}) for c, _, _ in routed]))
# Routed traffic gets its source tag from an LPM lookup on the receiving leaf. That needs
# platform group-based-policy lpm-source-lookup, which only takes effect after a leaf reboot
# (scripts/leaf-reboot.sh); without it the default deny drops allowed routed traffic.
docs.append(policy("ms-policy-routed", {"virtualNetworks": ["vnet-ms-routed"]}, "routed-interface-association",
                   "Test C policy, serviceTargets.virtualNetworks"))

# D: IRB + VLAN association. leaf-4 red, leaf-2 blue, leaf-3 green. VLAN 85, 172.16.85.0/24.
docs.append(vnet("vnet-ms-irb", "irb-interface-association",
                 "Test D: GroupTag on IRB (gateway) plus VLAN client tags. leaf-4 red (client-4), leaf-2 blue (client-2), leaf-3 green (client-3). VLAN 85.",
                 {"routers": [router("router-ms-irb", 4121, "10.41.2.1")],
                  "bridgeDomains": [bd("bd-ms-irb", 4122)],
                  "irbInterfaces": [irb("irb-ms-irb", "bd-ms-irb", "router-ms-irb", "172.16.85.254/24")],
                  "vlans": vlans("vlan-ms-irb", "bd-ms-irb", "ms-irb", 85)}))
docs.append(assoc("ms-assoc-irb", "irb-interface-association", "Test D: IRB irb-ms-irb is ms-gateway; VLANs tag the clients",
                  [("ms-gateway", {"irbInterfaces": ["irb-ms-irb"]})] +
                  [(f"ms-{c}", {"vlans": [f"vlan-ms-irb-{c}"]}) for c in ("red", "blue", "green")]))
docs.append(policy("ms-policy-irb", {"virtualNetworks": ["vnet-ms-irb"]}, "irb-interface-association",
                   "Test D policy, gateway rules plus host rules", gateway=True))

write(HERE / "gate2-pod1-acd.yaml", "# Gate 2: ms-* GroupTags + pod-1 tests A, C, D. Generated by gen-gate2.py.", docs)
