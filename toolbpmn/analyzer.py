"""Análisis de texto de procesos usando Claude API → JSON estructurado."""

import json
import re
from typing import Any, Generator

import anthropic

# Límite de caracteres del texto de entrada antes de truncar
_MAX_INPUT_CHARS = 16_000

SYSTEM_PROMPT = """Eres un experto en modelado de procesos de negocio (BPM) y notación BPMN 2.0.
Analiza la descripción del proceso y devuelve ÚNICAMENTE un JSON válido con esta estructura, sin texto adicional:

{
  "nombre_proceso": "string corto",
  "descripcion": "string — máx 1 oración",
  "objetivo": "string — máx 1 oración",
  "alcance": "string — máx 1 oración",
  "roles": [{"id": "role_1", "nombre": "string", "descripcion": "string breve"}],
  "pasos": [{
    "id": "step_1",
    "nombre": "string — verbo + objeto, máx 4 palabras",
    "descripcion": "string — máx 15 palabras",
    "tipo": "tarea | decision | inicio | fin | subproceso | evento",
    "rol_id": "role_1",
    "tiempo_ejecucion": 0,
    "unidad_tiempo": "minutos | horas | dias",
    "documentacion": "string — máx 20 palabras con lo esencial",
    "condicion": "string breve — solo si tipo=decision",
    "siguiente": ["step_2"]
  }]
}

Reglas estrictas:
- Primer paso SIEMPRE tipo "inicio", último SIEMPRE tipo "fin"
- Decisiones tienen EXACTAMENTE 2 entradas en "siguiente": [paso_si, paso_no]
- IDs secuenciales: step_1, step_2… role_1, role_2…
- Sé MUY conciso en todos los textos para no exceder el límite de tokens
- Devuelve SOLO el JSON, sin markdown"""


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
) -> Generator[tuple[int, int, str | None, dict | None], None, None]:
    """
    Streaming de la respuesta de Claude.
    Yields: (chars_generados, total_estimado, json_final_o_None, usage_o_None)
    El último yield tiene json_final y usage distintos de None.
    usage = {"input_tokens": N, "output_tokens": N}
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Analiza este proceso y devuelve el JSON estructurado completo:\n\n"
        + _trim_text(text)
    )

    raw = ""
    estimated_total = 1500
    usage: dict | None = None

    with client.messages.stream(
        model=model,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for chunk in stream.text_stream:
            raw += chunk
            yield len(raw), estimated_total, None, None
        try:
            final_msg = stream.get_final_message()
            usage = {
                "input_tokens":  final_msg.usage.input_tokens,
                "output_tokens": final_msg.usage.output_tokens,
            }
        except Exception:
            usage = {"input_tokens": 0, "output_tokens": 0}

    yield len(raw), len(raw), _parse_raw(raw), usage


def analyze_process(
    text: str, api_key: str, model: str = "claude-sonnet-4-6"
) -> tuple[dict[str, Any], dict]:
    """
    Versión síncrona sin streaming.
    Retorna (data, usage) donde usage = {"input_tokens": N, "output_tokens": N}.
    """
    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        "Analiza este proceso y devuelve el JSON estructurado completo:\n\n"
        + _trim_text(text)
    )
    message = client.messages.create(
        model=model,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    usage = {
        "input_tokens":  message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    return _parse_raw(message.content[0].text), usage


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
