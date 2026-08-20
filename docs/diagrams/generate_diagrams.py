#!/usr/bin/env python3
"""Generate documentation PNG diagrams — consistent layout for Word / pandoc."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = pathlib.Path(__file__).resolve().parent

# --- Design system (all figures share width + typography) ---
CANVAS_W = 16.0  # inches — fixed width for Word consistency
DPI = 300
MARGIN_L = 0.75
MARGIN_R = 0.75
MARGIN_TOP = 0.55
MARGIN_BOTTOM = 0.45

FONT = "DejaVu Sans"
mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Arial", "Helvetica"],
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
    }
)

WHITE = "#ffffff"
TEXT = "#0f172a"
TEXT_MUTED = "#475569"
PANEL_BG = "#f8fafc"
PANEL_EDGE = "#e2e8f0"
ARROW = "#64748b"
ALLOW = "#15803d"
DENY = "#dc2626"

RED, RED_E = "#fecaca", "#dc2626"
BLUE, BLUE_E = "#bfdbfe", "#2563eb"
GREEN, GREEN_E = "#bbf7d0", "#16a34a"
LEAF, LEAF_E = "#f1f5f9", "#475569"
FABRIC, FABRIC_E = "#e2e8f0", "#334155"
CR, CR_E = "#fef3c7", "#d97706"
MAC, MAC_E = "#dbeafe", "#2563eb"
IP, IP_E = "#e0e7ff", "#4338ca"
NOTE, NOTE_E = "#f1f5f9", "#94a3b8"

GROUP_COLORS = {
    "red": (RED, RED_E),
    "blue": (BLUE, BLUE_E),
    "green": (GREEN, GREEN_E),
}


@dataclass
class FigureSpec:
    height: float
    title: str
    subtitle: Optional[str] = None


class Diagram:
    def __init__(self, spec: FigureSpec) -> None:
        self.spec = spec
        self.fig, self.ax = plt.subplots(figsize=(CANVAS_W, spec.height))
        self.ax.set_xlim(0, CANVAS_W)
        self.ax.set_ylim(0, spec.height)
        self.ax.axis("off")
        y = spec.height - MARGIN_TOP
        self.ax.text(
            CANVAS_W / 2,
            y,
            spec.title,
            ha="center",
            va="top",
            fontsize=20,
            fontweight="bold",
            color=TEXT,
        )
        if spec.subtitle:
            self.ax.text(
                CANVAS_W / 2,
                y - 0.52,
                spec.subtitle,
                ha="center",
                va="top",
                fontsize=12,
                color=TEXT_MUTED,
            )
            self.content_top = y - 1.0
        else:
            self.content_top = y - 0.55

    def panel(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str,
    ) -> Tuple[float, float, float, float]:
        """Draw panel background; return inner content bounds (x, y, w, h)."""
        pad = 0.18
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.01,rounding_size=0.12",
            linewidth=1.2,
            edgecolor=PANEL_EDGE,
            facecolor=PANEL_BG,
            zorder=0,
        )
        self.ax.add_patch(patch)
        self.ax.text(
            x + w / 2,
            y + h - 0.22,
            title,
            ha="center",
            va="top",
            fontsize=12,
            fontweight="bold",
            color=TEXT,
            zorder=2,
        )
        return (x + pad, y + pad, w - 2 * pad, h - 0.55 - pad)

    def node(
        self,
        cx: float,
        cy: float,
        w: float,
        h: float,
        label: str,
        face: str,
        edge: str,
        fontsize: int = 11,
        bold: bool = False,
        zorder: int = 3,
    ) -> None:
        x, y = cx - w / 2, cy - h / 2
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.8,
            edgecolor=edge,
            facecolor=face,
            zorder=zorder,
        )
        self.ax.add_patch(patch)
        self.ax.text(
            cx,
            cy,
            label,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold" if bold else "normal",
            color=TEXT,
            linespacing=1.35,
            zorder=zorder + 1,
        )

    def arrow_v(self, x: float, y1: float, y2: float, dashed: bool = False) -> None:
        self._arrow((x, y1), (x, y2), dashed)

    def arrow_h(self, x1: float, x2: float, y: float, dashed: bool = False) -> None:
        self._arrow((x1, y), (x2, y), dashed)

    def arrow(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        dashed: bool = False,
        color: str = ARROW,
        lw: float = 1.8,
    ) -> None:
        self._arrow(start, end, dashed, color, lw)

    def _arrow(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        dashed: bool = False,
        color: str = ARROW,
        lw: float = 1.8,
    ) -> None:
        style = (0, (5, 4)) if dashed else "-"
        patch = FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=lw,
            color=color,
            linestyle=style,
            shrinkA=8,
            shrinkB=8,
            zorder=2,
        )
        self.ax.add_patch(patch)

    def edge_label(
        self,
        x: float,
        y: float,
        text: str,
        color: str,
        bg: str = WHITE,
        fontsize: int = 11,
    ) -> None:
        self.ax.text(
            x,
            y,
            text,
            ha="center",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=color,
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor=bg,
                edgecolor=PANEL_EDGE,
                linewidth=1.0,
            ),
            zorder=6,
            clip_on=False,
        )

    def line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        dashed: bool = False,
        color: str = ARROW,
        lw: float = 1.8,
    ) -> None:
        style = (0, (6, 5)) if dashed else "-"
        self.ax.plot(
            [start[0], end[0]],
            [start[1], end[1]],
            color=color,
            linewidth=lw,
            linestyle=style,
            zorder=2,
            solid_capstyle="round",
        )

    def footnote(self, text: str) -> None:
        self.ax.text(
            CANVAS_W / 2,
            MARGIN_BOTTOM,
            text,
            ha="center",
            va="bottom",
            fontsize=10,
            color=TEXT_MUTED,
        )

    def save(self, name: str) -> None:
        path = HERE / name
        self.fig.savefig(
            path,
            dpi=DPI,
            bbox_inches="tight",
            pad_inches=0.12,
            facecolor=WHITE,
        )
        plt.close(self.fig)
        print(f"wrote {path.name} ({path.stat().st_size} bytes, {DPI} dpi)")


def client_node(cx: float, cy: float, name: str, group: str, ip: Optional[str], d: Diagram, w: float, h: float) -> None:
    face, edge = GROUP_COLORS[group]
    label = f"{name}\n{group}"
    if ip:
        label += f"\n{ip}"
    d.node(cx, cy, w, h, label, face, edge, fontsize=10)


def leaf_node(cx: float, cy: float, label: str, d: Diagram, w: float, h: float) -> None:
    d.node(cx, cy, w, h, label, LEAF, LEAF_E, fontsize=10)


def draw_client_leaf_grid(
    d: Diagram,
    panel_x: float,
    panel_y: float,
    panel_w: float,
    panel_h: float,
    title: str,
    pairs: Sequence[Tuple[str, str, str, str, Optional[str]]],
) -> None:
    """pairs: (client_name, group, leaf_label, ip optional)"""
    ix, iy, iw, ih = d.panel(panel_x, panel_y, panel_w, panel_h, title)
    n = len(pairs)
    col_w = iw / n
    nw, nh = min(2.35, col_w * 0.82), 0.95
    lw, lh = nw, 0.82
    gap = 0.35
    client_y = iy + ih * 0.62
    leaf_y = iy + ih * 0.22

    for i, (client, group, leaf, ip) in enumerate(pairs):
        cx = ix + col_w * (i + 0.5)
        client_node(cx, client_y, client, group, ip, d, nw, nh)
        leaf_node(cx, leaf_y, leaf, d, lw, lh)
        d.arrow_v(cx, client_y - nh / 2 - 0.05, leaf_y + lh / 2 + 0.05)


def physical_topology() -> None:
    d = Diagram(
        FigureSpec(
            9.0,
            "Physical topology",
            "Clients on leaf edge ports · EVPN VXLAN fabric",
        )
    )
    pw = (CANVAS_W - 2 * MARGIN_L - 0.4) / 2
    ph = 4.2
    py = 2.55
    left_x = MARGIN_L
    right_x = MARGIN_L + pw + 0.4

    draw_client_leaf_grid(
        d,
        left_x,
        py,
        pw,
        ph,
        "Variant A · vnet-ms-vlan · VLAN 101",
        [
            ("client1", "red", "leaf-1 · e1-5.101", "172.16.101.1"),
            ("client2", "blue", "leaf-2 · e1-5.101", "172.16.101.2"),
            ("client3", "green", "leaf-3 · e1-5.101", "172.16.101.4"),
        ],
    )
    draw_client_leaf_grid(
        d,
        right_x,
        py,
        pw,
        ph,
        "Variants B–G · vnet-ms-* · VLAN 102–108",
        [
            ("client4", "red", "leaf-4 · e1-5", None),
            ("client5", "blue", "leaf-5 · e1-5", None),
            ("client6", "green", "leaf-8 · e1-5", None),
        ],
    )

    fabric_y = 1.05
    fabric_h = 0.95
    d.node(
        CANVAS_W / 2,
        fabric_y + fabric_h / 2,
        CANVAS_W - 2 * MARGIN_L,
        fabric_h,
        "EVPN VXLAN fabric  ·  leaf ↔ spine",
        FABRIC,
        FABRIC_E,
        fontsize=13,
        bold=True,
    )

    leaf_ys = py + 0.22 + 0.41
    leaf_xs = [
        left_x + 0.18 + pw / 6,
        left_x + 0.18 + pw / 2,
        left_x + 0.18 + 5 * pw / 6,
        right_x + 0.18 + pw / 6,
        right_x + 0.18 + pw / 2,
        right_x + 0.18 + 5 * pw / 6,
    ]
    fy = fabric_y + fabric_h + 0.08
    for lx in leaf_xs:
        d.arrow((lx, leaf_ys), (lx + (CANVAS_W / 2 - lx) * 0.15, fy), lw=1.4)

    d.save("physical-topology.png")


def packet_path() -> None:
    d = Diagram(
        FigureSpec(
            5.5,
            "Packet path",
            "Variant A · vnet-ms-vlan · east–west on leaf IP-VRF",
        )
    )
    steps = [
        ("1", "Client", "eth1.101\nDot1q", NOTE, NOTE_E),
        ("2", "Leaf edge", "e1-5.101\nGBP tag", NOTE, NOTE_E),
        ("3", "MAC-VRF", "bd-ms-vlan", MAC, MAC_E),
        ("4", "IRB", "172.16.101.254", IP, IP_E),
        ("5", "GBP ACL", "allow / drop", IP, IP_E),
        ("6", "EVPN", "/32 routes", IP, IP_E),
        ("7", "Peer", "remote host", GREEN, GREEN_E),
    ]
    n = len(steps)
    usable = CANVAS_W - MARGIN_L - MARGIN_R
    gap = 0.28
    nw = (usable - gap * (n - 1)) / n
    nh = 1.35
    y_body = 2.35
    y_step = 4.15

    xs = []
    for i, (num, title, body, face, edge) in enumerate(steps):
        cx = MARGIN_L + nw / 2 + i * (nw + gap)
        xs.append(cx)
        d.ax.text(cx, y_step, f"Step {num}", ha="center", va="center", fontsize=10, fontweight="bold", color=TEXT_MUTED)
        d.ax.text(cx, y_step - 0.28, title, ha="center", va="center", fontsize=11, fontweight="bold", color=TEXT)
        d.node(cx, y_body, nw, nh, body, face, edge, fontsize=10)

    for i in range(n - 1):
        d.arrow_h(xs[i] + nw / 2 + 0.06, xs[i + 1] - nw / 2 - 0.06, y_body)

    d.save("packet-path.png")


def k8s_chain() -> None:
    d = Diagram(
        FigureSpec(
            5.8,
            "Kubernetes object chain",
            "Per variant · programs GBP on SR Linux leaf",
        )
    )
    items = [
        ("GroupTag", "red · blue · green"),
        ("AssociationPolicy", "ms-assoc-*"),
        ("VirtualNetwork", "vnet-ms-*"),
        ("MicroSegmentationPolicy", "ms-policy-*"),
    ]
    n_main = len(items)
    usable = CANVAS_W - MARGIN_L - MARGIN_R - 3.2
    gap = 0.35
    nw = (usable - gap * (n_main - 1)) / n_main
    nh = 1.25
    cy = 3.0
    centers = []

    for i, (title, sub) in enumerate(items):
        cx = MARGIN_L + nw / 2 + i * (nw + gap)
        centers.append(cx)
        d.node(cx, cy, nw, nh, f"{title}\n{sub}", CR, CR_E, fontsize=10)

    fork_x = MARGIN_L + usable + 1.6
    d.node(fork_x, cy + 0.55, 2.8, 0.95, "MAC-VRF GBP\nedge group tag", MAC, MAC_E, fontsize=10)
    d.node(fork_x, cy - 0.55, 2.8, 0.95, "IP-VRF GBP\nACL rules", IP, IP_E, fontsize=10)

    last = centers[-1]
    d.arrow((last + nw / 2 + 0.05, cy + 0.35), (fork_x - 1.4, cy + 0.55))
    d.arrow((last + nw / 2 + 0.05, cy - 0.35), (fork_x - 1.4, cy - 0.55))

    for i in range(n_main - 1):
        d.arrow_h(centers[i] + nw / 2 + 0.05, centers[i + 1] - nw / 2 - 0.05, cy)

    d.save("k8s-chain.png")


def policy_rules() -> None:
    d = Diagram(
        FigureSpec(
            8.8,
            "Policy intent",
            "Pairwise GBP rules · red / blue / green",
        )
    )

    cx = CANVAS_W / 2
    bw, bh = 2.15, 1.05
    # Triangle vertices — wide base, apex high; room below for footnote and labels
    red_c = (cx - 3.35, 2.35)
    blue_c = (cx + 3.35, 2.35)
    green_c = (cx, 5.85)

    def clip_edge(start: Tuple[float, float], end: Tuple[float, float], shrink: float = 0.72) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        dx, dy = end[0] - start[0], end[1] - start[1]
        dist = (dx ** 2 + dy ** 2) ** 0.5
        s = (start[0] + dx * shrink / dist, start[1] + dy * shrink / dist)
        e = (end[0] - dx * shrink / dist, end[1] - dy * shrink / dist)
        return s, e

    # Edges first (under nodes)
    s, e = clip_edge(red_c, blue_c)
    d.arrow(s, e, lw=1.8)

    s, e = clip_edge(blue_c, green_c)
    d.arrow(s, e, lw=1.8)

    s, e = clip_edge(red_c, green_c)
    d.line(s, e, dashed=True, color=DENY, lw=2.4)

    # Labels — fixed positions outside triangle (no overlap with boxes or edges)
    d.edge_label(cx, red_c[1] - bh / 2 - 0.55, "allow ↔", ALLOW, bg="#f0fdf4")
    d.edge_label(cx + 2.05, 4.35, "allow ↔", ALLOW, bg="#f0fdf4")
    d.edge_label(cx - 2.05, 4.35, "drop", DENY, bg="#fef2f2")

    # Nodes on top
    d.node(red_c[0], red_c[1], bw, bh, "RED", RED, RED_E, fontsize=14, bold=True, zorder=4)
    d.node(blue_c[0], blue_c[1], bw, bh, "BLUE", BLUE, BLUE_E, fontsize=14, bold=True, zorder=4)
    d.node(green_c[0], green_c[1], bw, bh, "GREEN", GREEN, GREEN_E, fontsize=14, bold=True, zorder=4)

    d.footnote("Same-group traffic: allow · all other pairs: implicit deny")
    d.save("policy-rules.png")


def variant_catalog() -> None:
    d = Diagram(
        FigureSpec(
            7.2,
            "Variant catalog",
            "Association target and enforcement target per VirtualNetwork",
        )
    )
    headers = ["Variant", "VirtualNetwork", "Association", "Enforcement", "VLAN", "Clients"]
    rows = [
        ["A", "vnet-ms-vlan", "VLAN", "virtualNetworks", "101", "client1–3 → leaf-1/2/3"],
        ["B", "vnet-ms-bridge", "BridgeInterface", "virtualNetworks", "102", "client4–6 → leaf-4/5/8"],
        ["C", "vnet-ms-routed", "RoutedInterface", "virtualNetworks", "103", "client4–6 → leaf-4/5/8"],
        ["D", "vnet-ms-irb", "IRBInterface", "virtualNetworks", "104", "client4–6 → leaf-4/5/8"],
        ["E", "vnet-ms-static", "StaticRoute", "virtualNetworks", "106", "client4–6 → leaf-4/5/8"],
        ["F", "vnet-ms-enf-router", "VLAN", "routers", "107", "client4–6 → leaf-4/5/8"],
        ["G", "vnet-ms-enf-bd", "VLAN", "bridgeDomains (L2)", "108", "client4–6 → leaf-4/5/8"],
    ]

    table = d.ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        bbox=[MARGIN_L / CANVAS_W, 0.22, (CANVAS_W - MARGIN_L - MARGIN_R) / CANVAS_W, 0.62],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 2.1)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(PANEL_EDGE)
        cell.set_linewidth(1.0)
        if row == 0:
            cell.set_facecolor(FABRIC)
            cell.set_text_props(fontweight="bold", color=TEXT)
        elif col == 0:
            cell.set_facecolor(PANEL_BG)
            cell.set_text_props(fontweight="bold")
        else:
            cell.set_facecolor(WHITE)

    d.footnote("Variants B–G share Dot1q edge ethernet-1/5 on leaf-4, leaf-5, leaf-8")
    d.save("variant-catalog.png")


def client_leaf() -> None:
    d = Diagram(
        FigureSpec(
            6.5,
            "Test topology",
            "Client ↔ leaf mapping for automated ping tests",
        )
    )
    pw = (CANVAS_W - 2 * MARGIN_L - 0.4) / 2
    ph = 3.8
    py = 1.85
    draw_client_leaf_grid(
        d,
        MARGIN_L,
        py,
        pw,
        ph,
        "Variant A",
        [
            ("client1", "red", "leaf-1", None),
            ("client2", "blue", "leaf-2", None),
            ("client3", "green", "leaf-3", None),
        ],
    )
    draw_client_leaf_grid(
        d,
        MARGIN_L + pw + 0.4,
        py,
        pw,
        ph,
        "Variants B–G",
        [
            ("client4", "red", "leaf-4", None),
            ("client5", "blue", "leaf-5", None),
            ("client6", "green", "leaf-8", None),
        ],
    )
    d.save("client-leaf.png")


def main() -> None:
    physical_topology()
    packet_path()
    k8s_chain()
    policy_rules()
    variant_catalog()
    client_leaf()
    print("Done.")


if __name__ == "__main__":
    main()
