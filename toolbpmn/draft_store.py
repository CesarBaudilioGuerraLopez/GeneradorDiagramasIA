"""Borradores de proceso en localStorage del navegador (sobreviven recarga)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent / "draft_component"

_draft_component = components.declare_component(
    "bpmn_draft_store",
    path=str(_COMPONENT_DIR),
)


def draft_load(user: str, *, key: str = "draft_load") -> Any:
    return _draft_component(action="load", user=user, key=key, default=None)


def draft_save(user: str, payload: dict, *, key: str = "draft_save") -> Any:
    return _draft_component(
        action="save",
        user=user,
        payload=payload,
        key=key,
        default=None,
    )


def draft_clear(user: str, *, key: str = "draft_clear") -> Any:
    return _draft_component(action="clear", user=user, key=key, default=None)


def build_draft_payload(process_data: dict, bpmn_xml: Optional[str] = None) -> dict:
    from datetime import datetime

    return {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "nombre_proceso": (process_data or {}).get("nombre_proceso") or "Proceso sin nombre",
        "process_data": process_data,
        "bpmn_xml": bpmn_xml,
        "n_roles": len((process_data or {}).get("roles") or []),
        "n_pasos": len((process_data or {}).get("pasos") or []),
    }
