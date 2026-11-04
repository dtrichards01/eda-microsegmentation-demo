#!/usr/bin/env python3
"""
Configure clab client eth1 for EDA microsegmentation variant demos (Dot1q VLANs).

Each variant uses a dedicated VLAN on eth1 so multiple services can coexist on the
same leaf edge port; switch tests with --variant A|B|C|D|E|F|G.

Changes are additive only (docs/VARIANT-SCOPE-LOCK.md rule 3): the VLAN subif and
IP are created if missing, other subifs and the default route are left alone, and
off-subnet test prefixes get a specific route via the variant gateway.

Examples:
  python3 configure-client-ms-eth1.py --list
  python3 configure-client-ms-eth1.py --variant A --apply
  python3 configure-client-ms-eth1.py --variant B --apply --clients client4,client5,client6
  python3 configure-client-ms-eth1.py --variant A --fetch-only
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Literal

VariantId = Literal["A", "B", "C", "D", "E", "F", "G"]

SSH_OPTS = ["-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
DEFAULT_CLAB_NAME = ""

# Matches clab-s-spine-spine-leaf-sr-sim-srl.yaml edge links
# Authoritative MS scope: docs/VARIANT-SCOPE-LOCK.md
CLIENT_LEAF: dict[str, str] = {
    "client1": "leaf-1",
    "client2": "leaf-2",
    "client3": "leaf-3",
    "client4": "leaf-4",
    "client5": "leaf-5",
    "client6": "leaf-6",
    "client7": "leaf-7",
    "client8": "leaf-8",
}


@dataclass(frozen=True)
class Variant:
    id: VariantId
    name: str
    vlan: int
    vnet: str
    notes: str


VARIANTS: dict[VariantId, Variant] = {
    "A": Variant("A", "vlan-association", 75, "vnet-ms-vlan", "VLAN tagging + virtualNetworks enforcement"),
    "B": Variant("B", "bridge-interface-association", 75, "vnet-ms-bridge", "BridgeInterface association"),
    "C": Variant("C", "routed-interface-association", 80, "vnet-ms-routed", "RoutedInterface L3 handoff"),
    "D": Variant("D", "irb-interface-association", 85, "vnet-ms-irb", "IRB gateway tagging"),
    "E": Variant("E", "static-route-association", 90, "vnet-ms-static", "StaticRoute prefix tagging"),
    "F": Variant("F", "enforcement-router-target", 100, "vnet-ms-enf-router", "Policy on routers target"),
    "G": Variant("G", "enforcement-bridge-domain-target", 110, "vnet-ms-enf-bd", "L2 only — policy on bridgeDomains"),
}


@dataclass(frozen=True)
class ClientProfile:
    client: str
    # (ip, gateway) per variant — empty gateway = L2 only (G), no routes added
    addresses: dict[VariantId, tuple[str, str]]


# Off-subnet prefixes each variant's tests reach via the variant gateway.
# The client's own connected subnet is skipped automatically.
VARIANT_ROUTES: dict[VariantId, list[str]] = {
    "C": ["172.16.80.0/24", "172.16.81.0/24", "172.16.82.0/24"],
    "E": ["172.16.91.0/24"],
}


CLIENTS: list[ClientProfile] = [
    ClientProfile(
        "client1",
        {
            "A": ("172.16.75.1/24", "172.16.75.254"),
        },
    ),
    ClientProfile(
        "client2",
        {
            "A": ("172.16.75.2/24", "172.16.75.254"),
            "D": ("172.16.85.2/24", "172.16.85.254"),
        },
    ),
    ClientProfile(
        "client3",
        {
            "A": ("172.16.75.4/24", "172.16.75.254"),
            "D": ("172.16.85.3/24", "172.16.85.254"),
        },
    ),
    ClientProfile(
        "client4",
        {
            "B": ("172.16.75.1/24", "172.16.75.254"),
            "C": ("172.16.80.10/24", "172.16.80.1"),
            "D": ("172.16.85.4/24", "172.16.85.254"),
            "F": ("172.16.100.1/24", "172.16.100.254"),
            "G": ("172.16.110.1/24", ""),
        },
    ),
    ClientProfile(
        "client5",
        {
            "B": ("172.16.75.2/24", "172.16.75.254"),
            "C": ("172.16.81.10/24", "172.16.81.1"),
            "F": ("172.16.100.2/24", "172.16.100.254"),
            "G": ("172.16.110.2/24", ""),
        },
    ),
    ClientProfile(
        "client6",
        {
            "B": ("172.16.75.4/24", "172.16.75.254"),
            "C": ("172.16.82.10/24", "172.16.82.1"),
            "E": ("172.16.90.6/24", "172.16.90.254"),
            "F": ("172.16.100.4/24", "172.16.100.254"),
            "G": ("172.16.110.4/24", ""),
        },
    ),
    ClientProfile(
        "client7",
        {
            "E": ("172.16.90.7/24", "172.16.90.254"),
        },
    ),
    ClientProfile(
        "client8",
        {
            "E": ("172.16.90.8/24", "172.16.90.254"),
        },
    ),
]


def run_cmd(cmd: list[str], ssh_host: str | None = None, timeout: int = 45) -> subprocess.CompletedProcess[str]:
    if ssh_host:
        remote = subprocess.list2cmdline(cmd)
        return subprocess.run(
            ["ssh", *SSH_OPTS, ssh_host, remote],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def docker_name(client: str, clab_name: str) -> str:
    if not clab_name:
        return client
    return f"{clab_name}-{client}"


def clients_for_variant(variant: VariantId) -> list[ClientProfile]:
    return [c for c in CLIENTS if variant in c.addresses]


def subnet_of(ip_cidr: str) -> str:
    return str(ipaddress.ip_interface(ip_cidr).network)


def apply_client(
    client: str,
    vlan: int,
    ip_cidr: str,
    gateway: str,
    routes: list[str],
    ssh_host: str | None,
    clab_name: str,
) -> str:
    parent = "eth1"
    vlan_if = f"{parent}.{vlan}"
    own = subnet_of(ip_cidr)
    extra = " ".join(r for r in routes if r != own) if gateway else ""
    script = f"""
set -e
PARENT={parent}
VIF={vlan_if}
VID={vlan}
IP={ip_cidr}
GW={gateway}

ip link set "$PARENT" up
ip link show "$VIF" >/dev/null 2>&1 || ip link add link "$PARENT" name "$VIF" type vlan id "$VID"
ip link set "$VIF" up
ip -o -4 addr show dev "$VIF" | grep -q " $IP " || ip addr add "$IP" dev "$VIF"
for P in {extra}; do
  ip route show "$P" | grep -q . || ip route add "$P" via "$GW" dev "$VIF"
done
echo "vlan: $VID"
echo "iface: $VIF"
echo "addr: $(ip -o -4 addr show dev "$VIF" | awk '{{print $4}}' | tr '\\n' ' ')"
echo "routes: $(ip route show dev "$VIF" | grep via | tr '\\n' ';')"
echo "default (unchanged): $(ip route show default | head -1)"
"""
    container = docker_name(client, clab_name)
    proc = run_cmd(["docker", "exec", container, "bash", "-c", script], ssh_host)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def print_list() -> None:
    print("Microsegmentation variants (Dot1q on eth1):")
    for vid, v in VARIANTS.items():
        print(f"  {vid}: VLAN {v.vlan} — {v.vnet} — {v.notes}")
    print("\nClab topology (3-tier-leaf-spine-dcgw):")
    for c in CLIENTS:
        leaf = CLIENT_LEAF.get(c.client, "?")
        print(f"  {c.client} → {leaf}")
    print("\nClients per variant:")
    for vid in VARIANTS:
        names = [c.client for c in clients_for_variant(vid)]
        print(f"  {vid}: {', '.join(names) or '(none)'}")
    print(f"\nDocker: clientN or {DEFAULT_CLAB_NAME}-clientN (--clab-name to override)")


def print_plan(variant: Variant, profiles: list[ClientProfile]) -> None:
    print(f"=== Variant {variant.id} — VLAN {variant.vlan} — {variant.vnet} ===")
    print(f"    {variant.notes}")
    print(f"{'CLIENT':<10} {'LEAF':<8} {'VLAN-IF':<12} {'IP':<20} {'GATEWAY'}")
    for p in profiles:
        ip_cidr, gw = p.addresses[variant.id]
        leaf = CLIENT_LEAF.get(p.client, "?")
        print(f"{p.client:<10} {leaf:<8} eth1.{variant.vlan:<6} {ip_cidr:<20} {gw or '(L2 only)'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure client eth1 for MS variant VLAN demos")
    parser.add_argument("--variant", choices=list(VARIANTS.keys()), help="Demo variant A–G")
    parser.add_argument("--list", action="store_true", help="List variants and clients")
    parser.add_argument("--fetch-only", action="store_true", help="Show plan without applying")
    parser.add_argument("--apply", action="store_true", help="Apply VLAN subinterface config")
    parser.add_argument("--clients", default="", help="Comma-separated subset of clients")
    parser.add_argument("--ssh", dest="ssh_host", default=None, help="SSH hop to docker host")
    parser.add_argument(
        "--clab-name",
        default=os.environ.get("CLAB_NAME", DEFAULT_CLAB_NAME),
        help=f"Clab lab name prefix for docker exec (default {DEFAULT_CLAB_NAME})",
    )
    args = parser.parse_args()

    if args.list:
        print_list()
        return 0

    if not args.variant:
        parser.error("Specify --variant or --list")

    variant = VARIANTS[args.variant]
    profiles = clients_for_variant(args.variant)
    if args.clients:
        wanted = {x.strip() for x in args.clients.split(",") if x.strip()}
        profiles = [p for p in profiles if p.client in wanted]

    if not profiles:
        print(f"No clients defined for variant {args.variant}", file=sys.stderr)
        return 1

    print_plan(variant, profiles)

    if not args.apply and not args.fetch_only:
        parser.error("Specify --fetch-only or --apply")

    if args.apply:
        print("\n=== Applying ===")
        for p in profiles:
            ip_cidr, gw = p.addresses[variant.id]
            container = docker_name(p.client, args.clab_name)
            try:
                out = apply_client(
                    p.client,
                    variant.vlan,
                    ip_cidr,
                    gw,
                    VARIANT_ROUTES.get(variant.id, []),
                    args.ssh_host,
                    args.clab_name,
                )
                for line in out.splitlines():
                    print(f"  {line}")
                print(f"OK   {container}")
            except RuntimeError as exc:
                print(f"FAIL {p.client}: {exc}", file=sys.stderr)
                return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

