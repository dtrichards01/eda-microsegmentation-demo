# Clab topology: `3-tier-leaf-spine-dcgw`

Active lab file: `~/3-tier-leaf-spine-s_spine/clab-s-spine-spine-leaf-sr-sim-srl.yaml`

EDA namespace: `clab-3-tier-leaf-spine-dcgw` (matches clab lab name).

![Physical topology](diagrams/physical-topology.png){width=6.5in}

## Client Ã¢â€ â€ leaf edge links

| Client | Container name | Leaf | Switch port | Clab default eth1 IP | MS role |
|--------|----------------|------|-------------|----------------------|---------|
| client1 | `clab-3-tier-leaf-spine-dcgw-client1` | leaf-1 | e1-5 | 172.16.75.1/24 | Variant **A** red |
| client2 | `clab-3-tier-leaf-spine-dcgw-client2` | leaf-2 | e1-5 | 172.16.75.2/24 | Variant **A** blue |
| client3 | `clab-3-tier-leaf-spine-dcgw-client3` | leaf-3 | e1-5 | 172.16.201.1/24 | Variant **A** green (use **75.4** + VLAN 75 for MS) |
| client4 | `clab-3-tier-leaf-spine-dcgw-client4` | leaf-5 | e1-5 | 172.16.75.1/24 | Variants **BÃ¢â‚¬â€œG** red |
| client5 | `clab-3-tier-leaf-spine-dcgw-client5` | leaf-6 | e1-5 | 172.16.75.2/24 | Variants **BÃ¢â‚¬â€œG** blue |
| client6 | `clab-3-tier-leaf-spine-dcgw-client6` | leaf-7 | e1-5 | 172.16.75.4/24 | Variants **BÃ¢â‚¬â€œG** green |

Stock `client-config.sh` puts IP on **untagged** `eth1`. With EDA **Dot1q**, clients must use **`eth1.<vlan>`** (see `configs/client-config-ms-vlan.sh`).

## VLAN IDs (EDA edge `encapType: Dot1q`)

| Variant | VLAN | VNet | Clients |
|---------|------|------|---------|
| A | 75 | vnet-ms-vlan | client1, client2, client3 |
| B | 75 | vnet-ms-bridge | client4, client5, client6 |
| C | 80/81/82 | vnet-ms-routed | client4, client5, client6 |
| D | 85 | vnet-ms-irb | client4, client5, client6 |
| E | 90 | vnet-ms-static | client4, client5, client6 |
| F | 100 | vnet-ms-enf-router | client4, client5, client6 |
| G | 110 | vnet-ms-enf-bd | client4, client5, client6 |

Leaf-5/6/7 host VLAN subifs `.75`, `.80`, `.81`, `.82`, `.85`, `.90`, `.100`, `.110` on `ethernet-1/5` for same-leaf-set tests.

## Configure clients

**Runtime (recommended)** Ã¢â‚¬â€ from repo on docker host:

```bash
cd ~/Documents/eda-microsegmentation-demo/scripts   # or /mnt/c/... on WSL
python3 configure-client-ms-eth1.py --list
python3 configure-client-ms-eth1.py --variant A --apply
python3 configure-client-ms-eth1.py --variant B --apply
```

Default clab container prefix: `clab-3-tier-leaf-spine-dcgw-`. Override with `--clab-name` or env `CLAB_NAME`.

**Boot-time** Ã¢â‚¬â€ bind `configs/client-config-ms-vlan.sh` and use exec lines in `clab/clab-ms-client-exec.snippet`.

## Deploy EDA side

```bash
cd variants && bash apply-dot1q.sh
```

## Fabric notes

- SRL leaves: `ghcr.io/nokia/srlinux:26.3.1` (GBP supported on IXR-D2/D3/D4)
- Mgmt network: `172.55.10.0/24`
- client3/client4 share `172.16.201.1` in stock yaml (different leaves) Ã¢â‚¬â€ MS demos use distinct subnets per variant

