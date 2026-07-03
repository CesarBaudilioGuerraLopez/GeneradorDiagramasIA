"""Motor de layout compartido para diagrama PNG y BPMN XML."""

from typing import Any


def compute_column_layout(pasos: list[dict[str, Any]]) -> dict[str, int]:
    """Asigna columnas por longest-path topológico; evita solapamiento en el mismo carril."""
    if not pasos:
        return {}

    id_map = {p["id"]: p for p in pasos}
    all_ids = list(id_map.keys())

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

    topo.extend(pid for pid in all_ids if pid not in topo)

    col_map: dict[str, int] = {}
    for pid in topo:
        preds = [p for p in pred.get(pid, []) if p in col_map]
        col_map[pid] = (max(col_map[p] for p in preds) + 1) if preds else 0

    role_of = {p["id"]: p.get("rol_id", "") for p in pasos}
    topo_pos = {pid: i for i, pid in enumerate(topo)}

    for _ in range(len(pasos) * 4):
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

    changed = True
    while changed:
        changed = False
        for p in pasos:
            src = p["id"]
            if src not in col_map:
                continue
            for nxt in p.get("siguiente", []):
                if nxt in col_map and col_map[nxt] <= col_map[src]:
                    col_map[nxt] = col_map[src] + 1
                    changed = True

    return col_map


def normalize_process_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Garantiza roles completos y rol_id válidos en cada paso.
    Crea carriles para roles referenciados y reasigna huérfanos al rol por defecto.
    """
    out = dict(data)
    roles: list[dict[str, Any]] = [dict(r) for r in (out.get("roles") or [])]
    pasos: list[dict[str, Any]] = [dict(p) for p in (out.get("pasos") or [])]

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

    out["roles"] = roles
    out["pasos"] = pasos
    return out


def role_name_map(roles: list[dict[str, Any]]) -> dict[str, str]:
    return {r["id"]: r.get("nombre", r["id"]) for r in roles}
