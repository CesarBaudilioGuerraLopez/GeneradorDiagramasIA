"""Renderiza el proceso como imagen PNG usando matplotlib (sin dependencias externas)."""

import io
import math
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

# Colores por tipo
NODE_COLORS = {
    "inicio":     ("#27ae60", "white"),
    "fin":        ("#e74c3c", "white"),
    "decision":   ("#f39c12", "white"),
    "tarea":      ("#3498db", "white"),
    "subproceso": ("#9b59b6", "white"),
    "evento":     ("#1abc9c", "white"),
}

LANE_BG = [
    "#eaf4fb", "#fef9e7", "#eafaf1", "#fdf2f8",
    "#fef5e7", "#f0f3ff", "#f9f0ff", "#fff0f0",
]

NODE_W = 2.2
NODE_H = 0.8
H_GAP = 1.0
V_GAP = 0.5
LANE_H = 2.2
LANE_LABEL_W = 1.2
START_X = 0.4


def render_diagram(data: dict[str, Any]) -> bytes:
    roles = data.get("roles", [])
    pasos = data.get("pasos", [])
    process_name = data.get("nombre_proceso", "Proceso")

    role_index = {r["id"]: i for i, r in enumerate(roles)}
    pos = _compute_positions(pasos, roles)

    # Calcular tamaño del canvas
    max_col = max((p.get("_col", 0) for p in pasos), default=0)
    fig_w = max(12, LANE_LABEL_W + (max_col + 2) * (NODE_W + H_GAP) + 1.5)
    fig_h = max(5, len(roles) * (LANE_H + V_GAP) + 1.5)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    # Título
    ax.text(
        fig_w / 2, fig_h - 0.35, process_name,
        ha="center", va="center", fontsize=13, fontweight="bold", color="#2c3e50",
    )

    # Swim lanes
    for i, role in enumerate(roles):
        color = LANE_BG[i % len(LANE_BG)]
        lane_y = fig_h - 0.7 - (i + 1) * (LANE_H + V_GAP) + V_GAP
        lane_x = LANE_LABEL_W

        # Fondo del lane
        rect = FancyBboxPatch(
            (lane_x, lane_y), fig_w - lane_x - 0.2, LANE_H,
            boxstyle="round,pad=0.02", linewidth=1,
            edgecolor="#bdc3c7", facecolor=color,
        )
        ax.add_patch(rect)

        # Etiqueta del lane
        label_rect = FancyBboxPatch(
            (0.1, lane_y), LANE_LABEL_W - 0.1, LANE_H,
            boxstyle="round,pad=0.02", linewidth=1,
            edgecolor="#bdc3c7", facecolor="#d5d8dc",
        )
        ax.add_patch(label_rect)
        ax.text(
            LANE_LABEL_W / 2 + 0.05, lane_y + LANE_H / 2,
            _wrap_label(role["nombre"], 12),
            ha="center", va="center", fontsize=8, fontweight="bold",
            color="#2c3e50", rotation=90,
        )

    # Nodos
    node_centers = {}
    for paso in pasos:
        x, y = pos.get(paso["id"], (1.0, 1.0))
        tipo = paso.get("tipo", "tarea")
        fill, fg = NODE_COLORS.get(tipo, NODE_COLORS["tarea"])
        label = _wrap_label(paso.get("nombre", paso["id"]), 18)
        cx, cy = x + NODE_W / 2, y + NODE_H / 2
        node_centers[paso["id"]] = (cx, cy)

        if tipo == "inicio":
            circle = plt.Circle((cx, cy), 0.38, color=fill, zorder=3)
            ax.add_patch(circle)
            ax.text(cx, cy, label, ha="center", va="center", fontsize=7,
                    color=fg, fontweight="bold", zorder=4)
        elif tipo == "fin":
            outer = plt.Circle((cx, cy), 0.4, color=fill, zorder=3)
            inner = plt.Circle((cx, cy), 0.28, color="white", zorder=4)
            ax.add_patch(outer)
            ax.add_patch(inner)
            ax.text(cx, cy, label, ha="center", va="center", fontsize=7,
                    color=fill, fontweight="bold", zorder=5)
        elif tipo == "decision":
            diamond_x = [cx, cx + 0.45, cx, cx - 0.45, cx]
            diamond_y = [cy + 0.38, cy, cy - 0.38, cy, cy + 0.38]
            ax.fill(diamond_x, diamond_y, color=fill, zorder=3)
            ax.plot(diamond_x, diamond_y, color="#d68910", linewidth=1.2, zorder=4)
            ax.text(cx, cy, label, ha="center", va="center", fontsize=7,
                    color=fg, fontweight="bold", zorder=5)
        else:
            box = FancyBboxPatch(
                (x, y), NODE_W, NODE_H,
                boxstyle="round,pad=0.08", linewidth=1.2,
                edgecolor=_darken(fill), facecolor=fill, zorder=3,
            )
            ax.add_patch(box)
            ax.text(cx, cy, label, ha="center", va="center", fontsize=7.5,
                    color=fg, fontweight="bold", zorder=4,
                    multialignment="center")

    # Flechas
    drawn = set()
    for paso in pasos:
        tipo = paso.get("tipo", "tarea")
        for i, next_id in enumerate(paso.get("siguiente", [])):
            key = (paso["id"], next_id)
            if key in drawn:
                continue
            drawn.add(key)

            src = node_centers.get(paso["id"])
            tgt = node_centers.get(next_id)
            if not src or not tgt:
                continue

            ax.annotate(
                "",
                xy=tgt, xytext=src,
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#5d6d7e",
                    lw=1.4,
                    connectionstyle="arc3,rad=0.0",
                ),
                zorder=2,
            )

            # Etiqueta Sí/No en decisiones
            if tipo == "decision":
                mx = (src[0] + tgt[0]) / 2
                my = (src[1] + tgt[1]) / 2
                label_sf = "Sí" if i == 0 else "No"
                ax.text(mx, my + 0.12, label_sf, fontsize=7.5, color="#922b21",
                        ha="center", va="bottom", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.7))

    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _compute_positions(pasos: list, roles: list) -> dict[str, tuple[float, float]]:
    role_index = {r["id"]: i for i, r in enumerate(roles)}
    n_roles = max(len(roles), 1)
    pos = {}
    visited = set()

    def lane_y_center(rid):
        i = role_index.get(rid, 0)
        # El lane i está a: fig_h - 0.7 - (i+1)*(LANE_H+V_GAP) + V_GAP + LANE_H/2
        # Usamos coordenadas relativas; fig_h se calcula luego — aquí usamos 10 como estimado
        return 10 - 0.7 - (i + 1) * (LANE_H + V_GAP) + V_GAP + LANE_H / 2 - NODE_H / 2

    def traverse(pid, depth):
        if pid in visited:
            return
        visited.add(pid)
        paso = next((p for p in pasos if p["id"] == pid), None)
        if not paso:
            return
        rid = paso.get("rol_id", "")
        x = LANE_LABEL_W + 0.3 + depth * (NODE_W + H_GAP)
        y = lane_y_center(rid)
        pos[pid] = (x, y)
        paso["_col"] = depth
        for nxt in paso.get("siguiente", []):
            traverse(nxt, depth + 1)

    starts = [p["id"] for p in pasos if p.get("tipo") == "inicio"]
    if not starts and pasos:
        starts = [pasos[0]["id"]]
    for s in starts:
        traverse(s, 0)

    col = max((p.get("_col", 0) for p in pasos), default=0) + 1
    for paso in pasos:
        if paso["id"] not in pos:
            rid = paso.get("rol_id", "")
            pos[paso["id"]] = (LANE_LABEL_W + 0.3 + col * (NODE_W + H_GAP), lane_y_center(rid))
            col += 1

    return pos


def _wrap_label(text: str, width: int) -> str:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _darken(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = int(r * 0.75), int(g * 0.75), int(b * 0.75)
    return f"#{r:02x}{g:02x}{b:02x}"
