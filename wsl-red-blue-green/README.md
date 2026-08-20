# WSL EDA microsegmentation — legacy folder

**Use `variants/` for all deploy and test artifacts.** This folder is kept for reference only.

Active services are the seven dedicated `vnet-ms-*` VirtualNetworks (variants A–G). See `variants/README.md` and `docs/EDA-Microsegmentation.md`.

Policy rules (red/blue/green) live in `variants/microsegmentation-policies.yaml` (`ms-policy-vlan`, …).

Variant A example: `vnet-ms-vlan`, `ms-assoc-vlan`, `ms-policy-vlan`, subnet `172.16.101.0/24`, VLAN 101 on leaf-1/2/3.
