#!/usr/bin/env python3
"""Run MS variant connectivity tests; capture EDA state + full ping matrix."""
from __future__ import annotations

import json
import subprocess
import time

NS = "clab-3-tier-leaf-spine-dcgw"

# Authoritative scope: docs/VARIANT-SCOPE-LOCK.md
VARIANT_META = {
    "A": {
        "vlan": 75,
        "vnet": "vnet-ms-vlan",
        "association": "VLAN (vlan-ms-vlan-red / blue / green)",
        "enforcement": "serviceTargets.virtualNetworks",
        "policy": "ms-policy-vlan",
        "assoc_policy": "ms-assoc-vlan",
        "clients": ["client1", "client2", "client3"],
        "scope": "leaf-1/2/3",
    },
    "B": {
        "vlan": 75,
        "vnet": "vnet-ms-bridge",
        "association": "BridgeInterface (bi-red-5, bi-blue-6, bi-green-7)",
        "enforcement": "serviceTargets.virtualNetworks",
        "policy": "ms-policy-bridge",
        "assoc_policy": "ms-assoc-bridge",
        "clients": ["client4", "client5", "client6"],
        "scope": "leaf-5/6/7 (legacy catalog)",
    },
    "C": {
        "vlan": 80,
        "vnet": "vnet-ms-routed",
        "association": "RoutedInterface (ri-red-5, ri-blue-6, ri-green-7)",
        "enforcement": "serviceTargets.virtualNetworks",
        "policy": "ms-policy-routed",
        "assoc_policy": "ms-assoc-routed",
        "clients": ["client4", "client5", "client6"],
        "scope": "leaf-5/6/7 (legacy catalog)",
    },
    "D": {
        "vlan": 85,
        "vnet": "vnet-ms-irb",
        "association": "IRB (irb-ms-irb→gateway) + VLAN client helpers",
        "enforcement": "serviceTargets.virtualNetworks",
        "policy": "ms-policy-irb",
        "assoc_policy": "ms-assoc-irb",
        "clients": ["client2", "client3", "client4"],
        "scope": "leaf-2=blue, leaf-3=green, leaf-4=red",
    },
    "E": {
        "vlan": 90,
        "vnet": "vnet-ms-static",
        "association": "StaticRoute (static-remote-green) + VLAN clients",
        "enforcement": "serviceTargets.virtualNetworks",
        "policy": "ms-policy-static",
        "assoc_policy": "ms-assoc-static",
        "clients": ["client6", "client7", "client8"],
        "scope": "leaf-6=blue, leaf-7=green, leaf-8=red",
    },
    "F": {
        "vlan": 100,
        "vnet": "vnet-ms-enf-router",
        "association": "VLAN (vlan-enf-router-red/blue/green)",
        "enforcement": "serviceTargets.routers (router-ms-enf-router)",
        "policy": "ms-policy-enf-router",
        "assoc_policy": "ms-assoc-enf-router",
        "clients": ["client4", "client5", "client6"],
        "scope": "leaf-5/6/7 (legacy catalog)",
    },
    "G": {
        "vlan": 110,
        "vnet": "vnet-ms-enf-bd",
        "association": "VLAN (vlan-enf-bd-red/blue/green)",
        "enforcement": "serviceTargets.bridgeDomains (bd-ms-enf-bd)",
        "policy": "ms-policy-enf-bd",
        "assoc_policy": "ms-assoc-enf-bd",
        "clients": ["client4", "client5", "client6"],
        "scope": "leaf-5/6/7 (legacy catalog)",
    },
}

CLIENT_CFG = {
    "A": {
        "client1": ("172.16.75.1/24", "172.16.75.254"),
        "client2": ("172.16.75.2/24", "172.16.75.254"),
        "client3": ("172.16.75.4/24", "172.16.75.254"),
    },
    "B": {
        "client4": ("172.16.75.1/24", "172.16.75.254"),
        "client5": ("172.16.75.2/24", "172.16.75.254"),
        "client6": ("172.16.75.4/24", "172.16.75.254"),
    },
    "C": {
        "client4": ("172.16.80.10/24", "172.16.80.1"),
        "client5": ("172.16.81.10/24", "172.16.81.1"),
        "client6": ("172.16.82.10/24", "172.16.82.1"),
    },
    "D": {
        "client2": ("172.16.85.2/24", "172.16.85.254"),
        "client3": ("172.16.85.3/24", "172.16.85.254"),
        "client4": ("172.16.85.4/24", "172.16.85.254"),
    },
    "E": {
        "client6": ("172.16.90.6/24", "172.16.90.254"),
        "client7": ("172.16.90.7/24", "172.16.90.254"),
        "client8": ("172.16.90.8/24", "172.16.90.254"),
    },
    "F": {
        "client4": ("172.16.100.1/24", "172.16.100.254"),
        "client5": ("172.16.100.2/24", "172.16.100.254"),
        "client6": ("172.16.100.4/24", "172.16.100.254"),
    },
    "G": {
        "client4": ("172.16.110.1/24", ""),
        "client5": ("172.16.110.2/24", ""),
        "client6": ("172.16.110.4/24", ""),
    },
}

GROUP = {
    "client1": "red",
    "client2": "blue",
    "client3": "green",
    "client4": "red",
    "client5": "blue",
    "client6": "green",
    "client7": "green",
    "client8": "red",
}

VARIANT_GROUP = {
    "D": {"client2": "blue", "client3": "green", "client4": "red"},
    "E": {"client6": "blue", "client7": "green", "client8": "red"},
}


def kubectl_json(args: list[str]) -> dict | list:
    r = subprocess.run(
        ["kubectl", "-n", NS, *args, "-o", "json"],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if r.returncode != 0:
        return {"error": r.stderr.strip()}
    return json.loads(r.stdout)


def vnet_status(name: str) -> dict:
    data = kubectl_json(["get", "virtualnetwork", name])
    if isinstance(data, dict) and data.get("error"):
        return {"name": name, "error": data["error"]}
    meta = data.get("metadata", {})
    status = data.get("status", {})
    return {
        "name": name,
        "operationalState": status.get("operationalState"),
        "numNodes": status.get("numNodes"),
        "nodes": status.get("nodes"),
        "numSubinterfaces": status.get("numSubinterfaces"),
        "failed_transaction": meta.get("annotations", {}).get(
            "core.eda.nokia.com/failed-transaction"
        ),
    }


def cr_exists(kind_path: str, name: str) -> bool:
    r = subprocess.run(
        ["kubectl", "-n", NS, "get", kind_path, name],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return r.returncode == 0


def configure_client(client: str, vlan: int, ip: str, gw: str) -> str:
    script = f"""
set -e
P=eth1; V=$P.{vlan}; IP={ip}; GW={gw}
ip link set $P up 2>/dev/null || true
ip addr flush dev $P 2>/dev/null || true
for v in 75 80 81 82 85 90 100 110; do ip link del $P.$v 2>/dev/null || true; done
ip link add link $P name $V type vlan id {vlan} 2>/dev/null || true
ip link set $V up
ip addr flush dev $V 2>/dev/null || true
ip addr add $IP dev $V
while ip route show default 2>/dev/null | grep -q '^default'; do ip route del default 2>/dev/null || break; done
if [ -n "$GW" ]; then ip route add default via $GW dev $V; fi
"""
    for prefix in ("", "clab-3-tier-leaf-spine-dcgw-"):
        name = f"{prefix}{client}"
        r = subprocess.run(
            ["docker", "exec", name, "bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            return "ok"
    return "fail"


def ping(client: str, dest: str, vlan: int, count: int = 3) -> tuple[bool, str]:
    for prefix in ("", "clab-3-tier-leaf-spine-dcgw-"):
        name = f"{prefix}{client}"
        r = subprocess.run(
            [
                "docker", "exec", name, "ping", "-I", f"eth1.{vlan}",
                "-c", str(count), "-W", "2", dest,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode in (0, 1):
            summary = ""
            for line in (r.stdout + r.stderr).splitlines():
                if "packet loss" in line or "Unreachable" in line or "bytes from" in line:
                    summary = line.strip()
            if not summary:
                summary = (r.stderr or r.stdout).strip().split("\n")[-1][:120]
            return r.returncode == 0, summary
    return False, "docker exec failed"


def build_cases(variant: str, clients: list[str]) -> list[tuple[str, str, str, str]]:
    groups = VARIANT_GROUP.get(variant, GROUP)
    red = next((c for c in clients if groups.get(c) == "red"), None)
    blue = next((c for c in clients if groups.get(c) == "blue"), None)
    green = next((c for c in clients if groups.get(c) == "green"), None)
    cfg = CLIENT_CFG[variant]
    cases: list[tuple[str, str, str, str]] = []
    if red and blue:
        cases.append((red, cfg[blue][0].split("/")[0], "red->blue", "allow"))
    if red and green:
        cases.append((red, cfg[green][0].split("/")[0], "red->green", "drop"))
    if blue and green:
        cases.append((blue, cfg[green][0].split("/")[0], "blue->green", "allow"))
    if blue and red:
        cases.append((blue, cfg[red][0].split("/")[0], "blue->red", "allow"))
    if green and blue:
        cases.append((green, cfg[blue][0].split("/")[0], "green->blue", "allow"))
    if green and red:
        cases.append((green, cfg[red][0].split("/")[0], "green->red", "drop"))
    if red:
        cases.append((red, cfg[red][0].split("/")[0], "red->self", "allow"))
    if variant == "D" and red and cfg[red][1]:
        cases.append((red, cfg[red][1], "red->gateway-IRB", "allow"))
    if variant == "E" and red:
        cases.append((red, "172.16.91.1", "red->static-prefix", "drop"))
    if variant == "E" and blue and cfg[blue][1]:
        cases.append((blue, cfg[blue][1].split("/")[0] if "/" in cfg[blue][1] else cfg[blue][1], "blue->gateway", "allow"))
    return cases


def run_variant(variant: str) -> dict:
    meta = VARIANT_META[variant]
    vlan = meta["vlan"]
    clients = meta["clients"]
    out = {
        "variant": variant,
        "scope": meta["scope"],
        "vlan": vlan,
        "virtualnetwork": meta["vnet"],
        "association_target": meta["association"],
        "enforcement_target": meta["enforcement"],
        "association_policy": meta["assoc_policy"],
        "microsegmentation_policy": meta["policy"],
        "eda": {
            "vnet_status": vnet_status(meta["vnet"]),
            "association_policy_exists": cr_exists(
                "associationpolicy", meta["assoc_policy"]
            ),
            "microsegmentation_policy_exists": cr_exists(
                "microsegmentationpolicy", meta["policy"]
            ),
        },
        "client_configure": {},
        "tests": [],
    }
    for c in clients:
        ip, gw = CLIENT_CFG[variant][c]
        out["client_configure"][c] = configure_client(c, vlan, ip, gw)
    time.sleep(4)
    for src, dst, label, exp in build_cases(variant, clients):
        ok, summary = ping(src, dst, vlan)
        out["tests"].append({
            "label": label,
            "from": src,
            "to": dst,
            "expected": exp,
            "ping_ok": ok,
            "pass": ok if exp == "allow" else not ok,
            "summary": summary,
        })
    return out


def main():
    import sys
    variants = sys.argv[1:] if len(sys.argv) > 1 else ["D", "E"]
    results = [run_variant(v) for v in variants]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
