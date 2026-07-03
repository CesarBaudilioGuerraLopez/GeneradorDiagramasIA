"""Componente Streamlit: editor visual BPMN (bpmn-js) embebido."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent / "bpmn_component"

_bpmn_editor = components.declare_component(
    "bpmn_editor",
    path=str(_COMPONENT_DIR),
)


def render_bpmn_editor(
    xml: str,
    *,
    height: int = 620,
    key: Optional[str] = None,
) -> Any:
    """
    Muestra el modelador bpmn-js.
    Al pulsar "Guardar en el proceso" retorna dict {"xml": str, "ts": int}.
    """
    return _bpmn_editor(
        xml=xml or "",
        height=height,
        key=key,
        default=None,
    )
