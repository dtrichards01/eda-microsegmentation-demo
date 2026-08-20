#!/usr/bin/env python3
"""Assign Dot1q VLAN IDs to variant virtualnetworks.yaml."""
from pathlib import Path

path = Path(__file__).resolve().parent / "virtualnetworks.yaml"
text = path.read_text(encoding="utf-8")

# Order matters: replace per-document blocks
replacements = [
    ("vnet-ms-bridge", '"null"', '"102"', 3),  # 3 bridge ifs only in first doc - careful
]

# Safer: line-by-line state machine
VLAN_BY_MARKER = {
    "name: vnet-ms-bridge": "102",
    "name: vnet-ms-routed": "103",
    "name: vnet-ms-irb": "104",
    "name: vnet-ms-static": "106",
    "name: vnet-ms-enf-router": "107",
    "name: vnet-ms-enf-bd": "108",
}

lines = text.splitlines()
out = []
current_vlan = None
for line in lines:
    stripped = line.strip()
    for marker, vlan in VLAN_BY_MARKER.items():
        if stripped == marker:
            current_vlan = vlan
            break
    if current_vlan and "vlanID:" in line and '"null"' in line:
        line = line.replace('"null"', f'"{current_vlan}"')
    if stripped.startswith("name: vnet-ms-") and stripped not in VLAN_BY_MARKER:
        pass
    if stripped == "---" and out and out[-1] != "---":
        # next doc - reset only when we hit new vnet after bridge
        pass
    out.append(line)

path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"Updated {path}")
