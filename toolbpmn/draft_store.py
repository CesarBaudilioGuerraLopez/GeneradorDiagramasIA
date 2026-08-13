"""Borradores de proceso en localStorage del navegador (sobreviven recarga)."""

from __future__ import annotations

import hashlib
import json
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


def draft_content_hash(payload: dict) -> str:
    """Huella estable del borrador (ignora saved_at) para no re-guardar en bucle."""
    slim = {k: v for k, v in (payload or {}).items() if k != "saved_at"}
    raw = json.dumps(slim, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_draft_payload(
    process_data: dict | None = None,
    bpmn_xml: Optional[str] = None,
    *,
    input_text: str = "",
    audio_unified: str = "",
    audio_segments: Optional[list] = None,
) -> dict:
    from datetime import datetime

    pd = process_data or {}
    return {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "nombre_proceso": pd.get("nombre_proceso") or (
            "Borrador de texto" if input_text.strip() else "Proceso sin nombre"
        ),
        "process_data": process_data,
        "bpmn_xml": bpmn_xml,
        "input_text": input_text,
        "audio_unified": audio_unified,
        "audio_segments_meta": len(audio_segments or []),
        "n_roles": len(pd.get("roles") or []),
        "n_pasos": len(pd.get("pasos") or []),
    }
