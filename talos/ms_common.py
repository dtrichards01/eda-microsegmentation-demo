"""Shared CR builders for the Talos microsegmentation gates (gen-gate2.py, gen-gate3.py)."""
import json

NS = "clab-srl-leaf-spine-dcgw"
MS = "microsegmentation.eda.nokia.com/v1alpha1"
SVC = "services.eda.nokia.com/v2"
COLOURS = ("red", "blue", "green")


def md(name, labels=None, desc=None):
    m = {"name": name, "namespace": NS}
    if labels:
        m["labels"] = labels
    if desc:
        m["annotations"] = {"eda.nokia.com/ms-demo-description": desc}
    return m


def interface(name, vnet, val, client, ms):
    node, port = name.split("-ethernet-")
    labels = {"eda.nokia.com/role": "edge", f"eda.nokia.com/{vnet}": val}
    labels.update({f"eda.nokia.com/{k}": v for k, v in ms.items()})
    return {"apiVersion": "interfaces.eda.nokia.com/v1", "kind": "Interface", "metadata": md(name, labels),
            "spec": {"description": f"edge link to {client}", "enabled": True, "encapType": "Dot1q",
                     "ethernet": {"stormControl": {"enabled": False}}, "lldp": True,
                     "members": [{"enabled": True, "interface": "ethernet-" + port, "lacpPortPriority": 32768,
                                  "node": node}], "type": "Interface"}}


def router(name, evi, rid, asn=None):
    r = {"name": name, "spec": {"type": "EVPNVXLAN", "routerID": rid, "evi": evi,
                                "importTarget": f"target:1:{evi}", "exportTarget": f"target:1:{evi}",
                                "encapOptions": {"vxlan": {"vni": evi, "tunnelIndexPool": "tunnel-index-pool"}}}}
    if asn:
        r["spec"]["bgp"] = {"enabled": True, "autonomousSystem": asn, "ipv4Unicast": {"enabled": True}}
    return r


def bd(name, evi):
    return {"name": name, "spec": {"type": "EVPNVXLAN", "evi": evi,
                                   "importTarget": f"target:1:{evi}", "exportTarget": f"target:1:{evi}",
                                   "encapOptions": {"vxlan": {"vni": evi, "tunnelIndexPool": "tunnel-index-pool"}},
                                   "macLearning": {"agingTimeSeconds": 300, "enabled": True}, "macLimit": 2000}}


def irb(name, bdn, rtr, prefix, host_routes=False):
    s = {"bridgeDomain": bdn, "router": rtr, "ipMTU": 1500,
         "ipAddresses": [{"ipv4Address": {"ipPrefix": prefix, "primary": True}}],
         "evpnRouteAdvertisementType": {"arpDynamic": True, "arpStatic": True, "ndDynamic": True,
                                        "ndStatic": True, "rfc9135SymmetricMode": True},
         "ipv4": {"arpTimeoutSeconds": 14400, "learnUnsolicitedARP": "Disabled"}}
    if host_routes:
        s["hostRoutePopulate"] = {"dynamic": {"populate": True}}
    return {"name": name, "spec": s}


def vlan(name, bdn, test, colour, vid):
    return {"name": name, "spec": {"bridgeDomain": bdn, "vlanID": str(vid),
                                   "interfaceSelectors": [f"eda.nokia.com/{test}={colour}"]}}


def vlans(prefix, bdn, test, vid):
    return [vlan(f"{prefix}-{c}", bdn, test, c, vid) for c in COLOURS]


def entry(desc, src, dst, action):
    e = {"description": desc, "bidirectional": True, "match": {}, "action": {"forward": action, "collectStats": True, "log": action == "Drop"}}
    if src:
        e["match"] = {"sourceGroupTag": [src], "destinationGroupTag": [dst]}
    return e


def policy(name, targets, variant, desc, gateway=False, default_deny=True):
    """targets: serviceTargets dict, e.g. {"virtualNetworks": ["vnet-x"]}."""
    ents = []
    if gateway:
        ents += [entry(f"allow {c} to/from gateway IRB", f"ms-{c}", "ms-gateway", "Accept") for c in COLOURS]
    ents += [entry(f"allow {c}-{c}", f"ms-{c}", f"ms-{c}", "Accept") for c in COLOURS]
    ents += [entry("allow red to/from blue", "ms-red", "ms-blue", "Accept"),
             entry("allow blue to/from green", "ms-blue", "ms-green", "Accept"),
             entry("block red to/from green", "ms-red", "ms-green", "Drop")]
    if default_deny:
        ents.append(entry("default deny", None, None, "Drop"))
        ents[-1]["action"]["log"] = False
    return {"apiVersion": MS, "kind": "MicroSegmentationPolicy",
            "metadata": md(name, {"eda.nokia.com/ms-variant": variant}, desc),
            "spec": {"serviceTargets": targets, "entries": ents}}


def assoc(name, variant, desc, entries):
    return {"apiVersion": MS, "kind": "AssociationPolicy",
            "metadata": md(name, {"eda.nokia.com/ms-variant": variant}, desc),
            "spec": {"associationPolicyEntries": [{"groupTagNames": [t], "associationTargets": tg} for t, tg in entries]}}


def vnet(name, variant, desc, spec):
    return {"apiVersion": SVC, "kind": "VirtualNetwork", "metadata": md(name, {"eda.nokia.com/ms-variant": variant}, desc),
            "spec": spec}


def write(path, header, docs):
    path.write_text(header + "\n" + "".join("---\n" + json.dumps(d, indent=2) + "\n" for d in docs), encoding="utf-8")
    print("wrote", path, len(docs), "objects")
