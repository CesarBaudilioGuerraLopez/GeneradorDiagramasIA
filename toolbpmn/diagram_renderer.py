"""Renderiza diagrama BPMN como PNG — layout topológico adaptativo."""

import io
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

NODE_COLORS = {
    "inicio":     ("#27ae60", "white"),
    "fin":        ("#e74c3c", "white"),
    "decision":   ("#f39c12", "white"),
    "tarea":      ("#2980b9", "white"),
    "subproceso": ("#8e44ad", "white"),
    "evento":     ("#16a085", "white"),
}
LANE_BG = ["#ddeeff", "#fff8e1", "#e8f5e9", "#fce4ec",
           "#ede7f6", "#e0f7fa", "#fff3e0", "#f3e5f5"]


def render_diagram(data: dict[str, Any]) -> bytes:
    roles  = data.get("roles", [])
    pasos  = data.get("pasos", [])
    title  = data.get("nombre_proceso", "Proceso")
    n_roles = max(len(roles), 1)
    role_idx = {r["id"]: i for i, r in enumerate(roles)}

    # ── Asignación de columnas (topological longest-path) ────────────────────
    col_map = _topo_columns(pasos)
    max_col = max(col_map.values(), default=0)
    n_cols  = max_col + 1

    # ── Dimensiones adaptativas según cantidad de pasos ───────────────────────
    # Mantenemos nodos legibles; limitamos solo el DPI si la figura es grande
    LANE_H  = 2.0          # alto fijo por lane
    TITLE_H = 0.5
    LABEL_W = 1.1
    X_PAD   = 0.45
    R_PAD   = 0.5

    if n_cols <= 6:
        NODE_W, NODE_H, H_GAP, FSIZE = 1.85, 0.62, 0.65, 7.5
    elif n_cols <= 10:
        NODE_W, NODE_H, H_GAP, FSIZE = 1.55, 0.58, 0.55, 7.0
    elif n_cols <= 14:
        NODE_W, NODE_H, H_GAP, FSIZE = 1.30, 0.52, 0.45, 6.5
    else:
        NODE_W, NODE_H, H_GAP, FSIZE = 1.10, 0.46, 0.38, 6.0

    fig_w = LABEL_W + X_PAD + n_cols * (NODE_W + H_GAP) + R_PAD
    fig_h = TITLE_H + n_roles * LANE_H + 0.25

    # DPI: suficiente para 2400px max de ancho
    dpi = max(72, min(130, int(2400 / fig_w)))

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # ── Título ────────────────────────────────────────────────────────────────
    ax.text(fig_w / 2, fig_h - TITLE_H / 2, title,
            ha="center", va="center",
            fontsize=min(14, 9 + n_roles * 0.5),
            fontweight="bold", color="#1a2332",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"))

    # ── Swim lanes ────────────────────────────────────────────────────────────
    for i, role in enumerate(roles):
        ly = fig_h - TITLE_H - (i + 1) * LANE_H
        color = LANE_BG[i % len(LANE_BG)]

        # Fondo lane
        ax.add_patch(FancyBboxPatch(
            (LABEL_W, ly), fig_w - LABEL_W - 0.05, LANE_H,
            boxstyle="square,pad=0", lw=0.6,
            edgecolor="#b0bec5", facecolor=color, zorder=1))

        # Etiqueta lateral
        ax.add_patch(FancyBboxPatch(
            (0.04, ly), LABEL_W - 0.08, LANE_H,
            boxstyle="square,pad=0", lw=0.6,
            edgecolor="#b0bec5", facecolor="#cfd8dc", zorder=1))

        ax.text(LABEL_W / 2 + 0.02, ly + LANE_H / 2,
                _wrap(role["nombre"], 11),
                ha="center", va="center",
                fontsize=max(6.5, 8 - n_roles * 0.2),
                fontweight="bold", color="#263238", rotation=90)

        # Línea divisoria inferior
        ax.axhline(ly, xmin=0, xmax=1, color="#b0bec5", lw=0.5, zorder=1)

    # ── Calcular centros ──────────────────────────────────────────────────────
    centers: dict[str, tuple[float, float]] = {}
    for paso in pasos:
        pid = paso["id"]
        col = col_map.get(pid, 0)
        ri  = role_idx.get(paso.get("rol_id", ""), 0)
        ly_base = fig_h - TITLE_H - (ri + 1) * LANE_H
        cy = ly_base + LANE_H / 2
        cx = LABEL_W + X_PAD + col * (NODE_W + H_GAP) + NODE_W / 2
        centers[pid] = (cx, cy)

    # ── Nodos ─────────────────────────────────────────────────────────────────
    for paso in pasos:
        pid  = paso["id"]
        tipo = paso.get("tipo", "tarea")
        cx, cy = centers[pid]
        fill, fg = NODE_COLORS.get(tipo, NODE_COLORS["tarea"])
        label = _wrap(paso.get("nombre", pid), max(9, int(NODE_W / 0.11)))

        if tipo in ("inicio", "fin"):
            r = NODE_H * 0.48
            ax.add_patch(Circle((cx, cy), r, color=fill, zorder=4))
            if tipo == "fin":
                ax.add_patch(Circle((cx, cy), r * 0.62, color="white", zorder=5))
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=FSIZE * 0.85, fontweight="bold",
                    color=fill if tipo == "fin" else fg, zorder=6)

        elif tipo == "decision":
            s  = NODE_H * 0.52
            sw = NODE_W * 0.38
            xs = [cx, cx + sw, cx, cx - sw, cx]
            ys = [cy + s, cy, cy - s, cy, cy + s]
            ax.fill(xs, ys, color=fill, zorder=4)
            ax.plot(xs, ys, color=_darken(fill), lw=0.8, zorder=5)
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=FSIZE * 0.82, fontweight="bold",
                    color=fg, zorder=6, multialignment="center")

        else:
            bx, by = cx - NODE_W / 2, cy - NODE_H / 2
            ax.add_patch(FancyBboxPatch(
                (bx, by), NODE_W, NODE_H,
                boxstyle="round,pad=0.05", lw=1.1,
                edgecolor=_darken(fill), facecolor=fill, zorder=4))
            ax.text(cx, cy, label, ha="center", va="center",
                    fontsize=FSIZE, fontweight="bold",
                    color=fg, zorder=5, multialignment="center")

    # ── Flechas ───────────────────────────────────────────────────────────────
    arrow_kw = dict(color="#455a64", lw=1.1, mutation_scale=10, zorder=3)

    for paso in pasos:
        tipo = paso.get("tipo", "tarea")
        scx, scy = centers.get(paso["id"], (0, 0))

        for i, nxt in enumerate(paso.get("siguiente", [])):
            if nxt not in centers:
                continue
            tcx, tcy = centers[nxt]
            tgt_tipo = next((p.get("tipo","tarea") for p in pasos if p["id"] == nxt), "tarea")

            # Puntos de conexión
            sx = scx + _half_w(tipo, NODE_W, NODE_H)
            ex = tcx - _half_w(tgt_tipo, NODE_W, NODE_H)
            sy, ey = scy, tcy

            same_lane = abs(scy - tcy) < 0.05

            if same_lane:
                ax.annotate("", xy=(ex, ey), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>",
                                    connectionstyle="arc3,rad=0", **arrow_kw))
            else:
                # Dobla en L: primero horizontal hasta mid_x, luego vertical
                mid_x = sx + (ex - sx) * 0.5
                ax.annotate("", xy=(mid_x, tcy), xytext=(sx, scy),
                    arrowprops=dict(arrowstyle="-",
                                    connectionstyle="arc3,rad=0", **arrow_kw))
                ax.annotate("", xy=(ex, tcy), xytext=(mid_x, tcy),
                    arrowprops=dict(arrowstyle="-|>",
                                    connectionstyle="arc3,rad=0", **arrow_kw))

            # Etiqueta Sí / No
            if tipo == "decision":
                lbl = "Sí" if i == 0 else "No"
                mx = (sx + ex) / 2
                my = (sy + ey) / 2 + (0.12 if same_lane else 0)
                ax.text(mx, my, lbl, fontsize=FSIZE * 0.88,
                        color="#c0392b", ha="center", va="bottom",
                        fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.08",
                                  fc="white", ec="none", alpha=0.85),
                        zorder=7)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=dpi,
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Layout: topological longest-path ─────────────────────────────────────────

def _topo_columns(pasos: list) -> dict[str, int]:
    """Asigna columnas por longest-path desde el inicio (correcto para BPMN)."""
    id_map  = {p["id"]: p for p in pasos}
    all_ids = list(id_map.keys())

    # Mapa de predecesores
    pred: dict[str, list] = {pid: [] for pid in all_ids}
    for p in pasos:
        for nxt in p.get("siguiente", []):
            if nxt in pred:
                pred[nxt].append(p["id"])

    # Orden topológico (Kahn)
    in_deg = {pid: len(pred[pid]) for pid in all_ids}
    ready  = sorted(pid for pid, d in in_deg.items() if d == 0)
    topo: list[str] = []

    while ready:
        pid = ready.pop(0)
        topo.append(pid)
        for nxt in id_map.get(pid, {}).get("siguiente", []):
            if nxt in in_deg:
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    ready.append(nxt)
                    ready.sort()

    # Nodos con ciclos o no alcanzados
    topo.extend(pid for pid in all_ids if pid not in topo)

    # Columna = max(col de predecesores) + 1
    col_map: dict[str, int] = {}
    for pid in topo:
        preds = [p for p in pred.get(pid, []) if p in col_map]
        col_map[pid] = (max(col_map[p] for p in preds) + 1) if preds else 0

    # Resolver conflicto: mismo (col, lane) en el mismo rol
    role_of = {p["id"]: p.get("rol_id", "") for p in pasos}
    topo_pos = {pid: i for i, pid in enumerate(topo)}

    for _ in range(len(pasos) * 3):
        slot: dict[tuple, list] = {}
        for pid, col in col_map.items():
            slot.setdefault((col, role_of.get(pid, "")), []).append(pid)

        conflict = False
        for nodes in slot.values():
            if len(nodes) > 1:
                # Mantener el que viene primero en orden topológico
                nodes.sort(key=lambda x: topo_pos.get(x, 999))
                base = col_map[nodes[0]]
                for i, pid in enumerate(nodes[1:], 1):
                    if col_map[pid] < base + i:
                        col_map[pid] = base + i
                        conflict = True
        if not conflict:
            break

    # Propagación final: col[nxt] > col[src]
    changed = True
    while changed:
        changed = False
        for p in pasos:
            for nxt in p.get("siguiente", []):
                if nxt in col_map and col_map[nxt] <= col_map[p["id"]]:
                    col_map[nxt] = col_map[p["id"]] + 1
                    changed = True

    return col_map


# ── Utilidades ────────────────────────────────────────────────────────────────

def _half_w(tipo: str, nw: float, nh: float) -> float:
    if tipo in ("inicio", "fin"):
        return nh * 0.48
    if tipo == "decision":
        return nw * 0.38
    return nw / 2


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
    return "\n".join(lines[:4])   # máx 4 líneas


def _darken(h: str) -> str:
    c = h.lstrip("#")
    return "#{:02x}{:02x}{:02x}".format(
        int(int(c[0:2], 16) * .72),
        int(int(c[2:4], 16) * .72),
        int(int(c[4:6], 16) * .72))
