"""Genera XML BPMN 2.0 válido para importar en Bizagi Modeler."""

import uuid
from typing import Any
from xml.dom import minidom

# Layout en píxeles
CELL_W       = 160
CELL_H       = 60
H_GAP        = 60
LANE_H       = 180
V_GAP        = 0
LANE_LABEL_W = 100
START_X      = 30
START_Y      = 60
NODE_MARGIN  = (LANE_H - CELL_H) // 2   # centrar nodo dentro del lane


def _uid() -> str:
    return uuid.uuid4().hex[:10]


def generate_bpmn(data: dict[str, Any]) -> str:
    """Genera XML BPMN 2.0 importable en Bizagi. Retorna string UTF-8."""
    roles      = data.get("roles", [])
    pasos      = data.get("pasos", [])
    proc_name  = data.get("nombre_proceso", "Proceso")
    proc_id    = f"Process_{_uid()}"
    diag_id    = f"BPMNDiagram_{_uid()}"
    plane_id   = f"BPMNPlane_{_uid()}"
    laneset_id = f"LaneSet_{_uid()}"

    # ── Posiciones de nodos ───────────────────────────────────────────────────
    pos = _layout(pasos, roles)

    # ── Construir incoming / outgoing por nodo ────────────────────────────────
    incoming: dict[str, list[str]] = {p["id"]: [] for p in pasos}
    outgoing: dict[str, list[str]] = {p["id"]: [] for p in pasos}
    seq_flows: list[tuple[str, str, str, str]] = []  # (id, src, tgt, name)

    for paso in pasos:
        for i, nxt in enumerate(paso.get("siguiente", [])):
            sf_id = f"SF_{paso['id']}_{nxt}_{_uid()[:4]}"
            lbl = ""
            if paso.get("tipo") == "decision":
                lbl = "Sí" if i == 0 else "No"
            seq_flows.append((sf_id, paso["id"], nxt, lbl))
            outgoing[paso["id"]].append(sf_id)
            if nxt in incoming:
                incoming[nxt].append(sf_id)

    # ── Lanes map ─────────────────────────────────────────────────────────────
    role_index = {r["id"]: i for i, r in enumerate(roles)}
    lane_ids   = {r["id"]: f"Lane_{r['id']}" for r in roles}

    # ── Dimensiones totales ───────────────────────────────────────────────────
    max_col  = max((p.get("_col", 0) for p in pasos), default=0)
    total_w  = LANE_LABEL_W + (max_col + 2) * (CELL_W + H_GAP)
    total_h  = max(1, len(roles)) * LANE_H
    pool_id  = f"Participant_{_uid()}"
    pool_x, pool_y = START_X, START_Y

    # ═════════════════════════════════════════════════════════════════════════
    #  XML — construido como string para control total de namespaces
    # ═════════════════════════════════════════════════════════════════════════
    parts: list[str] = []

    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<definitions'
        f' xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"'
        f' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        f' xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"'
        f' xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"'
        f' xmlns:di="http://www.omg.org/spec/DD/20100524/DI"'
        f' id="Definitions_{_uid()}"'
        f' name={_xq(proc_name)}'
        f' targetNamespace="http://www.bizagi.com">'
    )

    # ── Collaboration (pool) ──────────────────────────────────────────────────
    collab_id = f"Collaboration_{_uid()}"
    parts.append(f'  <collaboration id={_xq(collab_id)}>')
    parts.append(
        f'    <participant id={_xq(pool_id)} name={_xq(proc_name)}'
        f' processRef={_xq(proc_id)}/>'
    )
    parts.append('  </collaboration>')

    # ── Process ───────────────────────────────────────────────────────────────
    parts.append(
        f'  <process id={_xq(proc_id)} name={_xq(proc_name)}'
        f' isExecutable="false" isClosed="false" processType="None">'
    )

    # LaneSet
    parts.append(f'    <laneSet id={_xq(laneset_id)}>')
    for role in roles:
        lid = lane_ids[role["id"]]
        parts.append(f'      <lane id={_xq(lid)} name={_xq(role["nombre"])}>')
        for p in pasos:
            if p.get("rol_id") == role["id"]:
                parts.append(f'        <flowNodeRef>{p["id"]}</flowNodeRef>')
        parts.append('      </lane>')
    parts.append('    </laneSet>')

    # Documentación del proceso completo (se agrega al elemento <process>)
    proc_doc = _build_process_doc(data)
    if proc_doc:
        # Insertamos la documentation del proceso justo después del tag <process ...>
        # Lo hacemos añadiendo a parts (ya estamos dentro del proceso en este punto)
        parts.append(f'    <documentation>{_xe(proc_doc)}</documentation>')

    # Flow nodes
    for paso in pasos:
        pid  = paso["id"]
        name = paso.get("nombre", pid)
        tipo = paso.get("tipo", "tarea")

        # <documentation> con toda la ficha del paso
        doc_text = _build_step_doc(paso)
        doc_xml  = f'      <documentation>{_xe(doc_text)}</documentation>\n' if doc_text else ""

        inc_xml  = "".join(f'      <incoming>{sf}</incoming>\n' for sf in incoming[pid])
        out_xml  = "".join(f'      <outgoing>{sf}</outgoing>\n' for sf in outgoing[pid])
        children = (doc_xml + inc_xml + out_xml).rstrip("\n")

        if tipo == "inicio":
            tag = "startEvent"
        elif tipo == "fin":
            tag = "endEvent"
        elif tipo == "decision":
            tag = "exclusiveGateway"
        elif tipo == "subproceso":
            tag = "subProcess"
        else:
            tag = "task"

        extra = ' gatewayDirection="Diverging"' if tipo == "decision" else ""

        parts.append(f'    <{tag} id={_xq(pid)} name={_xq(name)}{extra}>')
        parts.append(children)
        parts.append(f'    </{tag}>')

    # Sequence flows (con conditionExpression para salidas de gateways)
    # Construir mapa de condiciones por paso de decision
    condicion_map: dict[str, str] = {p["id"]: p.get("condicion", "") for p in pasos}

    for sf_id, src, tgt, lbl in seq_flows:
        name_attr = f' name={_xq(lbl)}' if lbl else ""
        src_tipo  = next((p.get("tipo","tarea") for p in pasos if p["id"] == src), "tarea")

        if src_tipo == "decision" and lbl:
            cond_text = condicion_map.get(src, "")
            if lbl == "Sí":
                expr = cond_text if cond_text else "Condición verdadera"
            else:
                expr = f"No cumple: {cond_text}" if cond_text else "Condición falsa"
            parts.append(
                f'    <sequenceFlow id={_xq(sf_id)} sourceRef={_xq(src)}'
                f' targetRef={_xq(tgt)}{name_attr}>'
            )
            parts.append(
                f'      <conditionExpression xsi:type="tFormalExpression">'
                f'{_xe(expr)}</conditionExpression>'
            )
            parts.append('    </sequenceFlow>')
        else:
            parts.append(
                f'    <sequenceFlow id={_xq(sf_id)} sourceRef={_xq(src)}'
                f' targetRef={_xq(tgt)}{name_attr}/>'
            )

    parts.append('  </process>')

    # ── BPMNDiagram ───────────────────────────────────────────────────────────
    parts.append(f'  <bpmndi:BPMNDiagram id={_xq(diag_id)} name="diagram">')
    # BPMNPlane apunta al proceso (no a la colaboración) — más compatible con Bizagi
    parts.append(f'    <bpmndi:BPMNPlane id={_xq(plane_id)} bpmnElement={_xq(proc_id)}>')

    # Pool shape (participant)
    parts.append(
        f'      <bpmndi:BPMNShape id={_xq("Shape_" + pool_id)}'
        f' bpmnElement={_xq(pool_id)} isHorizontal="true">'
    )
    parts.append(f'        <dc:Bounds x="{pool_x}" y="{pool_y}"'
                 f' width="{total_w}" height="{total_h}"/>')
    parts.append('      </bpmndi:BPMNShape>')

    # Lane shapes
    for i, role in enumerate(roles):
        lid   = lane_ids[role["id"]]
        lx    = pool_x + LANE_LABEL_W
        ly    = pool_y + i * LANE_H
        lw    = total_w - LANE_LABEL_W
        parts.append(
            f'      <bpmndi:BPMNShape id={_xq("Shape_" + lid)}'
            f' bpmnElement={_xq(lid)} isHorizontal="true">'
        )
        parts.append(f'        <dc:Bounds x="{lx}" y="{ly}" width="{lw}" height="{LANE_H}"/>')
        parts.append('      </bpmndi:BPMNShape>')

    # Node shapes
    for paso in pasos:
        pid  = paso["id"]
        tipo = paso.get("tipo", "tarea")
        nx, ny = pos.get(pid, (pool_x + LANE_LABEL_W + 20, pool_y + 20))

        if tipo in ("inicio", "fin"):
            nw, nh = 36, 36
        elif tipo == "decision":
            nw, nh = 50, 50
        else:
            nw, nh = CELL_W, CELL_H

        parts.append(
            f'      <bpmndi:BPMNShape id={_xq("Shape_" + pid)}'
            f' bpmnElement={_xq(pid)}>'
        )
        parts.append(f'        <dc:Bounds x="{nx}" y="{ny}" width="{nw}" height="{nh}"/>')
        parts.append('      </bpmndi:BPMNShape>')

    # Edge shapes
    for sf_id, src, tgt, _ in seq_flows:
        sx, sy = pos.get(src, (0, 0))
        tx, ty = pos.get(tgt, (0, 0))

        src_tipo = next((p.get("tipo","tarea") for p in pasos if p["id"] == src), "tarea")
        tgt_tipo = next((p.get("tipo","tarea") for p in pasos if p["id"] == tgt), "tarea")

        # Centro del borde derecho del nodo origen
        src_w = 36 if src_tipo in ("inicio","fin") else (50 if src_tipo=="decision" else CELL_W)
        src_h = 36 if src_tipo in ("inicio","fin") else (50 if src_tipo=="decision" else CELL_H)
        # Centro del borde izquierdo del nodo destino
        tgt_w = 36 if tgt_tipo in ("inicio","fin") else (50 if tgt_tipo=="decision" else CELL_W)
        tgt_h = 36 if tgt_tipo in ("inicio","fin") else (50 if tgt_tipo=="decision" else CELL_H)

        wp1x = sx + src_w
        wp1y = sy + src_h // 2
        wp2x = tx
        wp2y = ty + tgt_h // 2

        parts.append(f'      <bpmndi:BPMNEdge id={_xq("Edge_" + sf_id)} bpmnElement={_xq(sf_id)}>')
        parts.append(f'        <di:waypoint x="{wp1x}" y="{wp1y}"/>')
        parts.append(f'        <di:waypoint x="{wp2x}" y="{wp2y}"/>')
        parts.append('      </bpmndi:BPMNEdge>')

    parts.append('    </bpmndi:BPMNPlane>')
    parts.append('  </bpmndi:BPMNDiagram>')
    parts.append('</definitions>')

    raw = "\n".join(parts)
    # Pretty-print para legibilidad
    try:
        dom = minidom.parseString(raw.encode("utf-8"))
        return dom.toprettyxml(indent="  ", encoding=None)
    except Exception:
        return raw


# ── Helpers ───────────────────────────────────────────────────────────────────

def _xq(value: str) -> str:
    """Valor entre comillas dobles, caracteres XML escapados."""
    escaped = (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f'"{escaped}"'


def _xe(value: str) -> str:
    """Escapa caracteres XML para contenido de texto (no atributos)."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_step_doc(paso: dict) -> str:
    """Construye el texto de <documentation> para un paso."""
    lines = []
    if paso.get("descripcion"):
        lines.append(f"Descripción: {paso['descripcion']}")

    te = paso.get("tiempo_ejecucion", 0)
    ut = paso.get("unidad_tiempo", "minutos")
    if te and int(te) > 0:
        lines.append(f"Tiempo estimado: {te} {ut}")

    if paso.get("condicion") and paso.get("tipo") == "decision":
        lines.append(f"Criterio de decisión: {paso['condicion']}")

    if paso.get("documentacion"):
        lines.append(f"Instrucciones: {paso['documentacion']}")

    return "\n".join(lines)


def _build_process_doc(data: dict) -> str:
    """Construye el texto de <documentation> del proceso."""
    lines = []
    if data.get("descripcion"):
        lines.append(f"Descripción: {data['descripcion']}")
    if data.get("objetivo"):
        lines.append(f"Objetivo: {data['objetivo']}")
    if data.get("alcance"):
        lines.append(f"Alcance: {data['alcance']}")
    return "\n".join(lines)


def _layout(pasos: list, roles: list) -> dict[str, tuple[int, int]]:
    """BFS de izquierda a derecha; y centrado dentro del lane de su rol."""
    role_index = {r["id"]: i for i, r in enumerate(roles)}
    n_roles    = max(len(roles), 1)
    pos        = {}
    visited    = set()

    def lane_top(rid: str) -> int:
        i = role_index.get(rid, 0)
        return START_Y + i * LANE_H

    def traverse(pid: str, depth: int):
        if pid in visited:
            return
        visited.add(pid)
        paso = next((p for p in pasos if p["id"] == pid), None)
        if not paso:
            return
        rid = paso.get("rol_id", "")
        x   = START_X + LANE_LABEL_W + depth * (CELL_W + H_GAP) + H_GAP // 2

        tipo = paso.get("tipo", "tarea")
        if tipo in ("inicio", "fin"):
            nh = 36
        elif tipo == "decision":
            nh = 50
        else:
            nh = CELL_H

        y = lane_top(rid) + (LANE_H - nh) // 2
        pos[pid]     = (x, y)
        paso["_col"] = depth
        for nxt in paso.get("siguiente", []):
            traverse(nxt, depth + 1)

    starts = [p["id"] for p in pasos if p.get("tipo") == "inicio"]
    if not starts and pasos:
        starts = [pasos[0]["id"]]
    for s in starts:
        traverse(s, 0)

    # Nodos huérfanos
    extra_col = max((p.get("_col", 0) for p in pasos), default=0) + 1
    for paso in pasos:
        if paso["id"] not in pos:
            rid  = paso.get("rol_id", "")
            tipo = paso.get("tipo", "tarea")
            nh   = 36 if tipo in ("inicio","fin") else (50 if tipo=="decision" else CELL_H)
            pos[paso["id"]] = (
                START_X + LANE_LABEL_W + extra_col * (CELL_W + H_GAP),
                lane_top(rid) + (LANE_H - nh) // 2,
            )
            extra_col += 1

    return pos
