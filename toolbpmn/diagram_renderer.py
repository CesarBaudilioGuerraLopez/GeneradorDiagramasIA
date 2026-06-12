"""Renderiza el proceso como imagen PNG usando matplotlib."""

import io
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np

# ── Dimensiones en pulgadas (coordenadas del canvas) ─────────────────────────
TITLE_H    = 0.55   # espacio para el título del proceso
LANE_H     = 2.0    # alto de cada swim lane
LABEL_W    = 1.1    # ancho de la etiqueta lateral del lane
NODE_W     = 1.9    # ancho de las tareas rectangulares
NODE_H     = 0.65   # alto de las tareas rectangulares
H_GAP      = 0.7    # separación horizontal entre nodos
X_OFFSET   = 0.5    # margen izquierdo dentro del lane

# Colores
NODE_COLORS = {
    "inicio":     ("#27ae60", "white"),
    "fin":        ("#e74c3c", "white"),
    "decision":   ("#f39c12", "white"),
    "tarea":      ("#2980b9", "white"),
    "subproceso": ("#8e44ad", "white"),
    "evento":     ("#16a085", "white"),
}
LANE_BG = ["#eaf4fb", "#fef9e7", "#eafaf1", "#fdf2f8",
           "#fef5e7", "#f0f3ff", "#f9f0ff", "#fff0f0"]


def render_diagram(data: dict[str, Any]) -> bytes:
    roles  = data.get("roles", [])
    pasos  = data.get("pasos", [])
    title  = data.get("nombre_proceso", "Proceso")

    n_roles  = max(len(roles), 1)
    role_idx = {r["id"]: i for i, r in enumerate(roles)}

    # ── Calcular columnas con BFS ────────────────────────────────────────────
    col_map: dict[str, int] = {}
    visited: set[str] = set()

    def bfs(pid: str, col: int):
        if pid in visited:
            return
        visited.add(pid)
        col_map[pid] = max(col_map.get(pid, 0), col)
        paso = next((p for p in pasos if p["id"] == pid), None)
        if paso:
            for nxt in paso.get("siguiente", []):
                bfs(nxt, col + 1)

    starts = [p["id"] for p in pasos if p.get("tipo") == "inicio"]
    if not starts and pasos:
        starts = [pasos[0]["id"]]
    for s in starts:
        bfs(s, 0)
    for p in pasos:
        if p["id"] not in col_map:
            col_map[p["id"]] = max(col_map.values(), default=0) + 1

    # ── Resolver conflictos: nodos en mismo (col, lane) se superponen ────────
    for _ in range(len(pasos) * 2):
        slot: dict[tuple, list] = {}
        for pid, col in col_map.items():
            paso = next((p for p in pasos if p["id"] == pid), None)
            ri   = role_idx.get(paso.get("rol_id", ""), 0) if paso else 0
            slot.setdefault((col, ri), []).append(pid)

        conflict = False
        for nodes in slot.values():
            if len(nodes) > 1:
                nodes.sort()
                for i, pid in enumerate(nodes[1:], 1):
                    col_map[pid] = max(col_map[pid], nodes[0] and col_map[nodes[0]] + i)
                    col_map[pid] = col_map[nodes[0]] + i
                conflict = True
        if not conflict:
            break

    # Propagar: cada nodo debe estar en col > todos sus predecesores
    for _ in range(len(pasos) * 2):
        moved = False
        for paso in pasos:
            for nxt in paso.get("siguiente", []):
                if nxt in col_map and col_map[nxt] <= col_map[paso["id"]]:
                    col_map[nxt] = col_map[paso["id"]] + 1
                    moved = True
        if not moved:
            break

    max_col  = max(col_map.values(), default=0)
    fig_w    = LABEL_W + X_OFFSET + (max_col + 1) * (NODE_W + H_GAP) + 0.8
    fig_h    = TITLE_H + n_roles * LANE_H + 0.2

    fig, ax = plt.subplots(figsize=(max(10, fig_w), max(4, fig_h)))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # ── Título ───────────────────────────────────────────────────────────────
    ax.text(fig_w / 2, fig_h - TITLE_H / 2, title,
            ha="center", va="center", fontsize=12, fontweight="bold",
            color="#1a2332", fontfamily="DejaVu Sans")

    # ── Swim lanes ───────────────────────────────────────────────────────────
    for i, role in enumerate(roles):
        color  = LANE_BG[i % len(LANE_BG)]
        lane_y = fig_h - TITLE_H - (i + 1) * LANE_H   # y base (abajo del lane)

        # Fondo del lane
        ax.add_patch(FancyBboxPatch(
            (LABEL_W, lane_y), fig_w - LABEL_W - 0.05, LANE_H,
            boxstyle="square,pad=0", linewidth=0.8,
            edgecolor="#c5cfe0", facecolor=color, zorder=1))

        # Etiqueta lateral
        ax.add_patch(FancyBboxPatch(
            (0.05, lane_y), LABEL_W - 0.1, LANE_H,
            boxstyle="square,pad=0", linewidth=0.8,
            edgecolor="#c5cfe0", facecolor="#d5dce8", zorder=1))

        ax.text(LABEL_W / 2, lane_y + LANE_H / 2,
                _wrap(role["nombre"], 10),
                ha="center", va="center", fontsize=7.5,
                fontweight="bold", color="#2c3e50", rotation=90,
                fontfamily="DejaVu Sans")

    # ── Posición central (cx, cy) de cada nodo ───────────────────────────────
    centers: dict[str, tuple[float, float]] = {}
    for paso in pasos:
        pid  = paso["id"]
        tipo = paso.get("tipo", "tarea")
        col  = col_map.get(pid, 0)
        ri   = role_idx.get(paso.get("rol_id", ""), 0)

        lane_y_base = fig_h - TITLE_H - (ri + 1) * LANE_H
        cy = lane_y_base + LANE_H / 2           # centrado vertical en el lane
        cx = LABEL_W + X_OFFSET + col * (NODE_W + H_GAP) + NODE_W / 2
        centers[pid] = (cx, cy)

    # ── Dibujar nodos ─────────────────────────────────────────────────────────
    for paso in pasos:
        pid  = paso["id"]
        tipo = paso.get("tipo", "tarea")
        cx, cy = centers[pid]
        fill, fg = NODE_COLORS.get(tipo, NODE_COLORS["tarea"])
        label = _wrap(paso.get("nombre", pid), 20)

        if tipo in ("inicio", "fin"):
            r = 0.32
            circle = plt.Circle((cx, cy), r, color=fill, zorder=3)
            ax.add_patch(circle)
            if tipo == "fin":
                ax.add_patch(plt.Circle((cx, cy), r * 0.7, color="white", zorder=4))
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=6.5, fontweight="bold", color=fill if tipo=="fin" else fg,
                    zorder=5, fontfamily="DejaVu Sans")

        elif tipo == "decision":
            s = 0.42
            xs = [cx, cx+s, cx, cx-s, cx]
            ys = [cy+s*0.65, cy, cy-s*0.65, cy, cy+s*0.65]
            ax.fill(xs, ys, color=fill, zorder=3)
            ax.plot(xs, ys, color=_darken(fill), lw=1, zorder=4)
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=6, fontweight="bold", color=fg,
                    zorder=5, multialignment="center", fontfamily="DejaVu Sans")

        else:
            bx = cx - NODE_W / 2
            by = cy - NODE_H / 2
            ax.add_patch(FancyBboxPatch(
                (bx, by), NODE_W, NODE_H,
                boxstyle="round,pad=0.07", linewidth=1.2,
                edgecolor=_darken(fill), facecolor=fill, zorder=3))
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=7, fontweight="bold", color=fg,
                    zorder=4, multialignment="center", fontfamily="DejaVu Sans")

    # ── Dibujar flechas ───────────────────────────────────────────────────────
    for paso in pasos:
        tipo = paso.get("tipo", "tarea")
        scx, scy = centers.get(paso["id"], (0, 0))

        for i, nxt in enumerate(paso.get("siguiente", [])):
            if nxt not in centers:
                continue
            tcx, tcy = centers[nxt]
            tgt_tipo = next((p.get("tipo","tarea") for p in pasos if p["id"] == nxt), "tarea")

            # Punto de salida: borde derecho del origen
            if tipo in ("inicio", "fin"):
                sx, sy = scx + 0.32, scy
            elif tipo == "decision":
                sx, sy = scx + 0.42, scy
            else:
                sx, sy = scx + NODE_W / 2, scy

            # Punto de entrada: borde izquierdo del destino
            if tgt_tipo in ("inicio", "fin"):
                ex, ey = tcx - 0.32, tcy
            elif tgt_tipo == "decision":
                ex, ey = tcx - 0.42, tcy
            else:
                ex, ey = tcx - NODE_W / 2, tcy

            # Si cambia de lane, dobla la flecha con punto intermedio
            if abs(scy - tcy) > 0.1:
                mid_x = (sx + ex) / 2
                ax.annotate("", xy=(mid_x, tcy), xytext=(sx, scy),
                    arrowprops=dict(arrowstyle="-", color="#5d6d7e", lw=1.3,
                                    connectionstyle="arc3,rad=0"), zorder=2)
                ax.annotate("", xy=(ex, tcy), xytext=(mid_x, tcy),
                    arrowprops=dict(arrowstyle="-|>", color="#5d6d7e", lw=1.3,
                                    mutation_scale=12,
                                    connectionstyle="arc3,rad=0"), zorder=2)
            else:
                ax.annotate("", xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", color="#5d6d7e", lw=1.3,
                                    mutation_scale=12,
                                    connectionstyle="arc3,rad=0"), zorder=2)

            # Etiqueta Sí/No en decisiones
            if tipo == "decision":
                lbl = "Sí" if i == 0 else "No"
                mx, my = (sx + ex) / 2, (sy + ey) / 2
                ax.text(mx, my + 0.1, lbl, fontsize=7, color="#922b21",
                        ha="center", va="bottom", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="none", alpha=0.8))

    plt.tight_layout(pad=0.3)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _wrap(text: str, width: int) -> str:
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
    return f"#{int(r*.75):02x}{int(g*.75):02x}{int(b*.75):02x}"
