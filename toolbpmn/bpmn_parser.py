"""Convierte XML BPMN 2.0 (editado en el modelador) de vuelta a process_data."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
}


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def parse_bpmn_to_process_data(
    xml: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Extrae roles, pasos y conexiones desde un XML BPMN 2.0.
    Conserva metadata de `existing` cuando el id del paso/rol coincide.
    """
    existing = existing or {}
    old_pasos = {p.get("id"): p for p in (existing.get("pasos") or []) if p.get("id")}
    old_roles = {r.get("id"): r for r in (existing.get("roles") or []) if r.get("id")}

    root = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)

    # Registrar namespaces por si vienen sin prefijo
    process = None
    for el in root.iter():
        if _local(el.tag) == "process":
            process = el
            break
    if process is None:
        raise ValueError("No se encontro elemento <process> en el BPMN.")

    proc_name = process.get("name") or existing.get("nombre_proceso") or "Proceso"

    # Lanes → roles
    roles: list[dict[str, Any]] = []
    node_to_role: dict[str, str] = {}
    role_idx = 0

    for el in process.iter():
        if _local(el.tag) != "lane":
            continue
        role_idx += 1
        lane_name = (el.get("name") or f"Rol {role_idx}").strip()
        # Reusar id de rol existente por nombre
        rid = None
        for oid, orole in old_roles.items():
            if (orole.get("nombre") or "").strip().lower() == lane_name.lower():
                rid = oid
                break
        if not rid:
            rid = f"role_{role_idx}"
            # evitar colisiones
            while rid in {r["id"] for r in roles}:
                role_idx += 1
                rid = f"role_{role_idx}"

        prev = old_roles.get(rid, {})
        roles.append({
            "id": rid,
            "nombre": lane_name,
            "descripcion": prev.get("descripcion", ""),
        })
        for ref in el:
            if _local(ref.tag) == "flowNodeRef" and (ref.text or "").strip():
                node_to_role[(ref.text or "").strip()] = rid

    # Nodos de flujo
    pasos: list[dict[str, Any]] = []
    node_ids: list[str] = []

    tipo_map = {
        "startEvent": "inicio",
        "endEvent": "fin",
        "exclusiveGateway": "decision",
        "inclusiveGateway": "decision",
        "parallelGateway": "decision",
        "task": "tarea",
        "userTask": "tarea",
        "serviceTask": "tarea",
        "scriptTask": "tarea",
        "manualTask": "tarea",
        "subProcess": "subproceso",
        "intermediateThrowEvent": "evento",
        "intermediateCatchEvent": "evento",
    }

    for el in list(process):
        local = _local(el.tag)
        if local not in tipo_map:
            continue
        pid = el.get("id")
        if not pid:
            continue
        node_ids.append(pid)
        tipo = tipo_map[local]
        nombre = (el.get("name") or pid).strip()
        prev = old_pasos.get(pid, {})
        rol_id = node_to_role.get(pid) or prev.get("rol_id") or (
            roles[0]["id"] if roles else "role_1"
        )
        pasos.append({
            "id": pid,
            "nombre": nombre,
            "tipo": tipo,
            "rol_id": rol_id,
            "tiempo_ejecucion": prev.get("tiempo_ejecucion", 0) or 0,
            "unidad_tiempo": prev.get("unidad_tiempo") or "minutos",
            "descripcion": prev.get("descripcion") or _doc_field(el, "Descripción"),
            "condicion": prev.get("condicion") or "",
            "documentacion": prev.get("documentacion") or _text(
                next((c for c in el if _local(c.tag) == "documentation"), None)
            ),
            "siguiente": [],
        })

    if not roles:
        roles = [{"id": "role_1", "nombre": "General", "descripcion": ""}]
        for p in pasos:
            p["rol_id"] = "role_1"

    # Sequence flows → siguiente
    out_map: dict[str, list[str]] = {p["id"]: [] for p in pasos}
    for el in process.iter():
        if _local(el.tag) != "sequenceFlow":
            continue
        src = el.get("sourceRef")
        tgt = el.get("targetRef")
        if not src or not tgt:
            continue
        if src in out_map and tgt not in out_map[src]:
            name = (el.get("name") or "").strip().lower()
            if name in ("sí", "si", "yes", "true"):
                out_map[src].insert(0, tgt)
            else:
                out_map[src].append(tgt)

    # Limpiar duplicados preservando orden
    for p in pasos:
        seen = set()
        ordered = []
        for nxt in out_map.get(p["id"], []):
            if nxt in {x["id"] for x in pasos} and nxt not in seen:
                seen.add(nxt)
                ordered.append(nxt)
        p["siguiente"] = ordered

    # Si un paso no tiene rol en lane, asignar default
    role_ids = {r["id"] for r in roles}
    default_role = roles[0]["id"]
    for p in pasos:
        if p.get("rol_id") not in role_ids:
            p["rol_id"] = default_role

    return {
        "nombre_proceso": proc_name,
        "descripcion": existing.get("descripcion") or "",
        "objetivo": existing.get("objetivo") or "",
        "alcance": existing.get("alcance") or "",
        "roles": roles,
        "pasos": pasos,
    }


def _doc_field(el: ET.Element, label: str) -> str:
    doc = next((c for c in el if _local(c.tag) == "documentation"), None)
    text = _text(doc)
    if not text:
        return ""
    for line in text.splitlines():
        if line.lower().startswith(label.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""
