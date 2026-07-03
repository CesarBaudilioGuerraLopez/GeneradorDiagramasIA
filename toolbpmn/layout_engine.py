"""Motor de layout compartido para diagrama PNG y BPMN XML."""

from typing import Any


def _sanitize_pasos(pasos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Limpia referencias inválidas y auto-ciclos en 'siguiente'."""
    valid_ids = {p.get("id") for p in pasos if p.get("id")}
    clean: list[dict[str, Any]] = []
    for p in pasos:
        pid = p.get("id")
        if not pid:
            continue
        nxt = []
        for s in p.get("siguiente") or []:
            s = str(s).strip()
            if s and s in valid_ids and s != pid and s not in nxt:
                nxt.append(s)
        q = dict(p)
        q["siguiente"] = nxt
        clean.append(q)
    return clean


def compute_column_layout(pasos: list[dict[str, Any]]) -> dict[str, int]:
    """Asigna columnas por longest-path topológico; evita solapamiento en el mismo carril.

    Seguro ante ciclos: las aristas de retroceso (loops) no empujan columnas.
    """
    pasos = _sanitize_pasos(pasos)
    if not pasos:
        return {}

    id_map = {p["id"]: p for p in pasos}
    all_ids = list(id_map.keys())
    n = len(all_ids)

    pred: dict[str, list[str]] = {pid: [] for pid in all_ids}
    for p in pasos:
        for nxt in p.get("siguiente", []):
            if nxt in pred:
                pred[nxt].append(p["id"])

    in_deg = {pid: len(pred[pid]) for pid in all_ids}
    ready = sorted(pid for pid, d in in_deg.items() if d == 0)
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

    # Nodos en ciclo o no alcanzados
    topo.extend(pid for pid in all_ids if pid not in topo)
    topo_pos = {pid: i for i, pid in enumerate(topo)}

    def is_forward(src: str, tgt: str) -> bool:
        """True si la arista avanza en el orden topológico (no es loop)."""
        return topo_pos.get(tgt, -1) > topo_pos.get(src, -1)

    col_map: dict[str, int] = {}
    for pid in topo:
        preds = [
            p for p in pred.get(pid, [])
            if p in col_map and is_forward(p, pid)
        ]
        col_map[pid] = (max(col_map[p] for p in preds) + 1) if preds else 0

    role_of = {p["id"]: p.get("rol_id", "") for p in pasos}

    for _ in range(max(n * 4, 1)):
        slot: dict[tuple, list[str]] = {}
        for pid, col in col_map.items():
            slot.setdefault((col, role_of.get(pid, "")), []).append(pid)

        conflict = False
        for nodes in slot.values():
            if len(nodes) > 1:
                nodes.sort(key=lambda x: topo_pos.get(x, 999))
                base = col_map[nodes[0]]
                for i, pid in enumerate(nodes[1:], 1):
                    if col_map[pid] < base + i:
                        col_map[pid] = base + i
                        conflict = True
        if not conflict:
            break

    # Solo propagar por aristas hacia adelante (máx n iteraciones)
    for _ in range(max(n, 1)):
        changed = False
        for p in pasos:
            src = p["id"]
            if src not in col_map:
                continue
            for nxt in p.get("siguiente", []):
                if nxt not in col_map or not is_forward(src, nxt):
                    continue
                need = col_map[src] + 1
                if col_map[nxt] < need:
                    col_map[nxt] = need
                    changed = True
        if not changed:
            break

    return col_map


def normalize_process_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Garantiza roles completos y rol_id válidos en cada paso.
    Crea carriles para roles referenciados y reasigna huérfanos al rol por defecto.
    """
    out = dict(data)
    roles: list[dict[str, Any]] = [dict(r) for r in (out.get("roles") or [])]
    pasos: list[dict[str, Any]] = [dict(p) for p in (out.get("pasos") or [])]
    pasos = _sanitize_pasos(pasos)

    role_ids = {r["id"] for r in roles if r.get("id")}

    for p in pasos:
        rid = (p.get("rol_id") or "").strip()
        if rid and rid not in role_ids:
            roles.append({
                "id": rid,
                "nombre": rid.replace("_", " ").replace("-", " ").title(),
                "descripcion": "",
            })
            role_ids.add(rid)

    if not roles:
        roles = [{"id": "role_1", "nombre": "General", "descripcion": ""}]
        role_ids.add("role_1")

    default_role = roles[0]["id"]
    roles_with_steps = {p.get("rol_id") for p in pasos if p.get("rol_id")}

    roles.sort(
        key=lambda r: (
            r["id"] not in roles_with_steps,
            r.get("nombre", "").lower(),
        )
    )

    for p in pasos:
        rid = (p.get("rol_id") or "").strip()
        if not rid or rid not in role_ids:
            p["rol_id"] = default_role

    used_ids = {p["id"] for p in pasos if p.get("id")}
    for i, p in enumerate(pasos):
        if not p.get("id"):
            nid = f"step_{i + 1}"
            while nid in used_ids:
                nid = f"step_{len(used_ids) + 1}"
            p["id"] = nid
            used_ids.add(nid)
        if not p.get("nombre"):
            p["nombre"] = p["id"]

    out["roles"] = roles
    out["pasos"] = pasos
    return out


def role_name_map(roles: list[dict[str, Any]]) -> dict[str, str]:
    return {r["id"]: r.get("nombre", r["id"]) for r in roles}
