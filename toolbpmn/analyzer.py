"""Análisis de texto de procesos usando Claude API → JSON estructurado."""

import json
import re
from typing import Any

import anthropic

SYSTEM_PROMPT = """Eres un experto en modelado de procesos de negocio (BPM) y notación BPMN 2.0.
Analiza la descripción del proceso que te proporcione el usuario y devuelve ÚNICAMENTE un JSON válido
con la siguiente estructura, sin texto adicional antes ni después:

{
  "nombre_proceso": "string — nombre corto del proceso",
  "descripcion": "string — resumen del objetivo del proceso en una oración",
  "objetivo": "string — para qué sirve este proceso, qué valor aporta",
  "alcance": "string — qué cubre y qué queda fuera del proceso",
  "roles": [
    {
      "id": "role_1",
      "nombre": "string — nombre del rol o área organizacional",
      "descripcion": "string — responsabilidades principales de este rol en el proceso"
    }
  ],
  "pasos": [
    {
      "id": "step_1",
      "nombre": "string — nombre corto (verbo + objeto, máx 5 palabras)",
      "descripcion": "string — qué se hace exactamente en este paso, cómo se hace",
      "tipo": "tarea | decision | inicio | fin | subproceso | evento",
      "rol_id": "string — id del rol responsable (debe existir en roles)",
      "tiempo_ejecucion": 0,
      "unidad_tiempo": "minutos | horas | dias",
      "documentacion": "string — instrucciones detalladas, normas aplicables, sistemas usados, criterios de calidad",
      "condicion": "string — solo para tipo decision: criterio que determina el camino a tomar",
      "siguiente": ["step_2"]
    }
  ]
}

Reglas estrictas:
- El primer paso SIEMPRE es tipo "inicio".
- El último paso SIEMPRE es tipo "fin".
- Las decisiones (tipo "decision") tienen EXACTAMENTE dos entradas en "siguiente": [paso_si, paso_no].
- Los ids son secuenciales: step_1, step_2… / role_1, role_2…
- Todos los role_id referenciados en pasos deben existir en el arreglo roles.
- tiempo_ejecucion debe ser un número entero estimado realista (0 si no aplica, como inicio/fin).
- unidad_tiempo: "minutos" para tareas cortas, "horas" para tareas medias, "dias" para procesos largos.
- documentacion debe ser detallada, útil para quien ejecuta el paso por primera vez.
- Devuelve SOLO el JSON, sin bloques de código markdown, sin texto antes ni después."""


def analyze_process(text: str, api_key: str, model: str = "claude-sonnet-4-6") -> dict[str, Any]:
    """Envía el texto a Claude y retorna el JSON analizado. Lanza ValueError si falla."""
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Analiza el siguiente proceso de negocio y devuelve el JSON estructurado "
                    "con TODOS los campos requeridos, incluyendo tiempos estimados y documentación "
                    "detallada para cada paso:\n\n" + text
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude no devolvió JSON válido: {e}\n\nRespuesta:\n{raw}")

    # Asegurar campos nuevos con defaults si Claude los omitió
    for paso in data.get("pasos", []):
        paso.setdefault("tiempo_ejecucion", 0)
        paso.setdefault("unidad_tiempo", "minutos")
        paso.setdefault("documentacion", "")
        paso.setdefault("condicion", "")

    data.setdefault("objetivo", "")
    data.setdefault("alcance", "")

    return data


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
                errors.append(
                    f"Paso '{paso.get('id')}' tiene rol_id '{rid}' que no existe en roles."
                )

    return errors
