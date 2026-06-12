"""Configuración persistente.

Prioridad de la API key:
  1. st.secrets (Streamlit Community Cloud)
  2. %APPDATA%\CASSA\BPMNTool\config.json (ejecución local)
  3. Variable de entorno ANTHROPIC_API_KEY
"""

import json
import os
from pathlib import Path

_CONFIG_DIR  = Path(os.environ.get("APPDATA", Path.home())) / "CASSA" / "BPMNTool"
CONFIG_FILE  = _CONFIG_DIR / "config.json"
_LEGACY_FILE = Path(__file__).parent / ".cassa_config.json"


def _is_cloud() -> bool:
    """True cuando corre en Streamlit Community Cloud."""
    return os.environ.get("STREAMLIT_SHARING_MODE") == "1" or \
           os.path.exists("/mount/src")


def _migrate_legacy():
    if _LEGACY_FILE.exists():
        try:
            old = json.loads(_LEGACY_FILE.read_text(encoding="utf-8"))
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            if not CONFIG_FILE.exists():
                CONFIG_FILE.write_text(json.dumps(old, indent=2), encoding="utf-8")
            _LEGACY_FILE.unlink()
        except Exception:
            pass


if not _is_cloud():
    _migrate_legacy()


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(data: dict) -> None:
    if _is_cloud():
        return  # en la nube la config es de solo lectura (se gestiona via secrets)
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_api_key() -> str:
    # 1. Streamlit Cloud secrets
    try:
        import streamlit as st
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # 2. Config local
    key = load_config().get("anthropic_api_key", "")
    if key:
        return key
    # 3. Variable de entorno
    return os.environ.get("ANTHROPIC_API_KEY", "")


def set_api_key(key: str) -> None:
    if _is_cloud():
        return
    cfg = load_config()
    cfg["anthropic_api_key"] = key.strip()
    save_config(cfg)


def get_model() -> str:
    try:
        import streamlit as st
        m = st.secrets.get("CLAUDE_MODEL", "")
        if m:
            return m
    except Exception:
        pass
    return load_config().get("model", "claude-sonnet-4-6")


def set_model(model: str) -> None:
    if _is_cloud():
        return
    cfg = load_config()
    cfg["model"] = model
    save_config(cfg)


def is_cloud() -> bool:
    return _is_cloud()
