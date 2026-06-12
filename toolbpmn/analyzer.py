"""Análisis de texto de procesos usando Claude API → JSON estructurado."""

import json
import re
from typing import Any, Generator

import anthropic

# Límite de caracteres del texto de entrada antes de truncar
_MAX_INPUT_CHARS = 8_000

SYSTEM_PROMPT = """Eres un experto en modelado de procesos de negocio (BPM) y notación BPMN 2.0.
Analiza la descripción del proceso y devuelve ÚNICAMENTE un JSON válido con esta estructura exacta, sin texto adicional:

{
  "nombre_proceso": "string",
  "descripcion": "string — una oración",
  "objetivo": "string",
  "alcance": "string",
  "roles": [{"id": "role_1", "nombre": "string", "descripcion": "string"}],
  "pasos": [{
    "id": "step_1",
    "nombre": "string — verbo + objeto, máx 5 palabras",
    "descripcion": "string",
    "tipo": "tarea | decision | inicio | fin | subproceso | evento",
    "rol_id": "role_1",
    "tiempo_ejecucion": 0,
    "unidad_tiempo": "minutos | horas | dias",
    "documentacion": "string",
    "condicion": "string — solo si tipo=decision",
    "siguiente": ["step_2"]
  }]
}

Reglas: primer paso=inicio, último=fin, decisiones tienen exactamente 2 siguientes, ids secuenciales, devuelve SOLO el JSON."""


def _trim_text(text: str) -> str:
    """Trunca textos muy largos para no ralentizar la respuesta."""
    if len(text) > _MAX_INPUT_CHARS:
        return text[:_MAX_INPUT_CHARS] + "\n\n[Texto truncado por longitud]"
    return text


def _parse_raw(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude no devolvió JSON válido: {e}\n\nRespuesta:\n{raw[:500]}")

    for paso in data.get("pasos", []):
        paso.setdefault("tiempo_ejecucion", 0)
        paso.setdefault("unidad_tiempo", "minutos")
        paso.setdefault("documentacion", "")
        paso.setdefault("condicion", "")

    data.setdefault("objetivo", "")
    data.setdefault("alcance", "")
    return data


def analyze_process_stream(
    text: str, api_key: str, model: str = "claude-sonnet-4-6"
) -> Generator[tuple[int, int, str | None], None, None]:
    """
    Streaming de la respuesta de Claude.
    Yields: (chars_generados, total_estimado, json_final_o_None)
    El último yield tiene json_final distinto de None.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Analiza este proceso y devuelve el JSON estructurado completo:\n\n"
        + _trim_text(text)
    )

    raw = ""
    # Estimamos ~2000 tokens de salida = ~1500 chars como referencia de progreso
    estimated_total = 1500

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for chunk in stream.text_stream:
            raw += chunk
            yield len(raw), estimated_total, None

    yield len(raw), len(raw), _parse_raw(raw)


def analyze_process(text: str, api_key: str, model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    """Versión síncrona sin streaming (compatibilidad)."""
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Analiza este proceso y devuelve el JSON estructurado completo:\n\n"
        + _trim_text(text)
    )
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return _parse_raw(message.content[0].text)


def validate_process_json(data: dict) -> list[str]:
    errors = []
    for k in ("nombre_proceso", "descripcion", "roles", "pasos"):
        if k not in data:
            errors.append(f"Falta la clave: {k}")
    if "roles" in data and "pasos" in data:
        role_ids = {r["id"] for r in data["roles"]}
        for paso in data["pasos"]:
            rid = paso.get("rol_id", "")
            if rid and rid not in role_ids:
                errors.append(f"Paso '{paso.get('id')}' tiene rol_id '{rid}' que no existe en roles.")
    return errors
