"""BPMN Tool — Interfaz principal Streamlit con branding Grupo CASSA."""

import base64
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import get_api_key, get_model, set_api_key, set_model, is_cloud
from file_readers import extract_text
from audio_input import render_audio_recorder, transcribe_audio_bytes
from analyzer import analyze_process, validate_process_json
from bpmn_generator import generate_bpmn
from diagram_renderer import render_diagram

# ── Rutas de assets ──────────────────────────────────────────────────────────
ASSETS = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS / "logo_cassa.png"

# ── Colores CASSA ─────────────────────────────────────────────────────────────
CASSA_BLUE  = "#004B9A"
CASSA_GREEN = "#00A651"
CASSA_LIGHT = "#E8F0FA"
CASSA_DARK  = "#002D5F"

# ── Helpers ───────────────────────────────────────────────────────────────────
def _img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _inject_css():
    st.markdown(
        f"""
<style>
/* ── Reset y tipografía ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* ── Fondo principal ── */
.stApp {{
    background-color: #F4F6F9;
}}

/* ── Header corporativo ── */
.cassa-header {{
    background: linear-gradient(135deg, {CASSA_DARK} 0%, {CASSA_BLUE} 60%, #1565C0 100%);
    padding: 18px 32px;
    border-radius: 0 0 12px 12px;
    display: flex;
    align-items: center;
    gap: 24px;
    margin: -1rem -1rem 1.5rem -1rem;
    box-shadow: 0 4px 16px rgba(0,75,154,0.25);
}}
.cassa-header img {{
    height: 52px;
    filter: brightness(0) invert(1);
}}
.cassa-header-text h1 {{
    color: white !important;
    font-size: 1.45rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    padding: 0 !important;
    letter-spacing: 0.3px;
}}
.cassa-header-text p {{
    color: rgba(255,255,255,0.75) !important;
    font-size: 0.82rem !important;
    margin: 2px 0 0 0 !important;
    padding: 0 !important;
}}
.cassa-badge {{
    margin-left: auto;
    background: rgba(0,166,81,0.25);
    border: 1px solid {CASSA_GREEN};
    color: #b8f5d4;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {CASSA_DARK} 0%, {CASSA_BLUE} 100%) !important;
}}
[data-testid="stSidebar"] * {{
    color: white !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: white !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stTextInput > div > div > input {{
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: white !important;
    border-radius: 8px !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.2) !important;
}}
.sidebar-logo {{
    text-align: center;
    padding: 16px 0 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    margin-bottom: 16px;
}}
.sidebar-logo img {{
    width: 130px;
    filter: brightness(0) invert(1);
}}
.sidebar-section {{
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 12px;
}}
.sidebar-section-title {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255,255,255,0.55) !important;
    font-weight: 600;
    margin-bottom: 8px;
}}

/* ── Tarjetas de sección ── */
.section-card {{
    background: white;
    border-radius: 12px;
    padding: 24px 28px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    margin-bottom: 20px;
    border-left: 4px solid {CASSA_BLUE};
}}
.section-card.green {{
    border-left-color: {CASSA_GREEN};
}}
.section-card h3 {{
    color: {CASSA_BLUE} !important;
    font-size: 1rem;
    font-weight: 700;
    margin: 0 0 16px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}}

/* ── Step badges ── */
.step-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: {CASSA_BLUE};
    color: white;
    border-radius: 50%;
    font-size: 0.8rem;
    font-weight: 700;
    margin-right: 8px;
    flex-shrink: 0;
}}
.step-title {{
    color: {CASSA_DARK};
    font-size: 1.05rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    margin: 24px 0 12px 0;
}}

/* ── Botón primario ── */
[data-testid="stButton"] > button[kind="primary"] {{
    background: linear-gradient(135deg, {CASSA_BLUE}, {CASSA_DARK}) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.2rem !important;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0,75,154,0.3) !important;
}}
[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, {CASSA_DARK}, #001a3d) !important;
    box-shadow: 0 4px 14px rgba(0,75,154,0.4) !important;
    transform: translateY(-1px);
}}

/* ── Botones de descarga ── */
[data-testid="stDownloadButton"] > button {{
    background: white !important;
    color: {CASSA_BLUE} !important;
    border: 2px solid {CASSA_BLUE} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
}}
[data-testid="stDownloadButton"] > button:hover {{
    background: {CASSA_LIGHT} !important;
    transform: translateY(-1px);
}}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: white;
    border-radius: 10px 10px 0 0;
    padding: 4px 4px 0;
    border: 1px solid #e2e8f0;
    border-bottom: none;
    gap: 2px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    border-radius: 8px 8px 0 0 !important;
    font-weight: 500;
    color: #64748b;
    padding: 8px 20px;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {CASSA_BLUE} !important;
    color: white !important;
    font-weight: 600 !important;
}}
[data-testid="stTabContent"] {{
    background: white;
    border: 1px solid #e2e8f0;
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 20px;
}}

/* ── Métricas ── */
[data-testid="stMetric"] {{
    background: white;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    border-top: 3px solid {CASSA_GREEN};
}}
[data-testid="stMetricLabel"] {{
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
[data-testid="stMetricValue"] {{
    color: {CASSA_DARK} !important;
    font-weight: 700 !important;
}}

/* ── Alertas ── */
[data-testid="stAlert"] {{
    border-radius: 8px !important;
}}

/* ── DataEditor ── */
[data-testid="stDataFrame"], [data-testid="data-grid-canvas"] {{
    border-radius: 8px !important;
}}

/* ── Footer ── */
.cassa-footer {{
    text-align: center;
    padding: 20px 0 8px 0;
    color: #94a3b8;
    font-size: 0.75rem;
    border-top: 1px solid #e2e8f0;
    margin-top: 32px;
}}
.cassa-footer span {{
    color: {CASSA_BLUE};
    font-weight: 600;
}}

/* ── Ocultar elementos Streamlit por defecto ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 0 !important; max-width: 1200px; }}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_header():
    logo_b64 = _img_b64(LOGO_PATH) if LOGO_PATH.exists() else ""
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" alt="CASSA"/>' if logo_b64 else ""
    st.markdown(
        f"""
<div class="cassa-header">
    {logo_html}
    <div class="cassa-header-text">
        <h1>Generador de Procesos BPMN</h1>
        <p>Analítica & Gestión del Conocimiento — Grupo CASSA</p>
    </div>
    <div class="cassa-badge">✦ BETA</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_sidebar(api_key: str, model: str) -> tuple[str, str]:
    """Renderiza la sidebar y retorna (api_key, model). Model es siempre fijo."""
    with st.sidebar:
        # Logo
        if LOGO_PATH.exists():
            logo_b64 = _img_b64(LOGO_PATH)
            st.markdown(
                f'<div class="sidebar-logo"><img src="data:image/png;base64,{logo_b64}"/></div>',
                unsafe_allow_html=True,
            )

        # Sección: Configuración API
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">⚙ Configuración</div>', unsafe_allow_html=True)

        if is_cloud():
            # En la nube la key viene de Streamlit Secrets — no se edita aquí
            if api_key:
                st.markdown(
                    '<div style="background:rgba(0,166,81,0.2);border:1px solid #00A651;'
                    'border-radius:8px;padding:10px 12px;font-size:0.82rem;color:#b8f5d4">'
                    '🔐 <b>API Key configurada</b><br>'
                    '<span style="opacity:0.75">Gestionada via Streamlit Secrets</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.error("API Key no configurada en Secrets.")
        else:
            new_key = st.text_input(
                "API Key Anthropic",
                value=api_key,
                type="password",
                help="Se guarda localmente en %APPDATA%\\CASSA\\BPMNTool\\",
                label_visibility="visible",
            )
            if new_key != api_key:
                set_api_key(new_key)
                api_key = new_key
                st.success("API Key guardada")

        st.markdown(
            '<div style="font-size:0.78rem;color:rgba(255,255,255,0.6);margin-top:6px">'
            '⚡ Modelo: <b style="color:white">Claude Sonnet</b></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Sección: Estado
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">◉ Estado de sesión</div>', unsafe_allow_html=True)
        if api_key:
            st.markdown("🟢 **API Key:** Configurada")
        else:
            st.markdown("🔴 **API Key:** No configurada")
        if st.session_state.get("process_data"):
            n_roles = len(st.session_state.process_data.get("roles", []))
            n_pasos = len(st.session_state.process_data.get("pasos", []))
            st.markdown(f"🔵 **Proceso cargado**")
            st.markdown(f"&nbsp;&nbsp;&nbsp;• {n_roles} roles · {n_pasos} pasos")
        else:
            st.markdown("⚪ Sin proceso cargado")
        st.markdown("</div>", unsafe_allow_html=True)

        # Sección: Guía rápida
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">📖 Guía rápida</div>', unsafe_allow_html=True)
        st.markdown(
            """
<small style="color:rgba(255,255,255,0.75);line-height:1.7">
1. Configura tu API Key (una sola vez)<br>
2. Describe el proceso con texto, archivo o micrófono<br>
3. Haz clic en <b>Analizar</b><br>
4. Edita roles y pasos si es necesario<br>
5. Genera el diagrama visual<br>
6. Exporta <b>.bpmn</b> para Bizagi o <b>.png</b>
</small>
""",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            '<div style="text-align:center;padding-top:8px;color:rgba(255,255,255,0.35);font-size:0.7rem">'
            "BPMN Tool v1.0 · Analítica CASSA</div>",
            unsafe_allow_html=True,
        )

    return api_key, model


def _step_title(n: int, icon: str, title: str):
    st.markdown(
        f'<div class="step-title"><span class="step-badge">{n}</span>{icon} {title}</div>',
        unsafe_allow_html=True,
    )


# ── App principal ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BPMN Tool — Grupo CASSA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

_inject_css()
_render_header()

# Estado de sesión
for key in ("process_data", "bpmn_xml", "diagram_png"):
    if key not in st.session_state:
        st.session_state[key] = None

# Sidebar (carga y persiste config)
api_key = get_api_key()
model = "claude-sonnet-4-6"   # fijo, no configurable por el usuario
api_key, model = _render_sidebar(api_key, model)

# ── PASO 1: Entrada ───────────────────────────────────────────────────────────
_step_title(1, "📝", "Describe tu proceso")

input_text = ""
input_tab, file_tab, audio_tab = st.tabs(["✏️  Texto libre", "📁  Cargar archivo", "🎙️  Micrófono"])

with input_tab:
    input_text_area = st.text_area(
        "Escribe el proceso con tus propias palabras:",
        height=180,
        placeholder=(
            "Ejemplo: El proceso inicia cuando el área solicitante envía una requisición de compra. "
            "El jefe de área la aprueba si el monto es menor a $5,000. Para montos mayores, "
            "pasa a revisión de Finanzas. Luego Compras emite la orden de compra al proveedor..."
        ),
        label_visibility="collapsed",
    )
    if input_text_area:
        input_text = input_text_area

with file_tab:
    uploaded_file = st.file_uploader(
        "Sube un archivo Word, Excel o texto:",
        type=["docx", "xlsx", "xls", "txt", "md"],
        help="Se extraerá automáticamente el texto del archivo.",
        label_visibility="collapsed",
    )
    if uploaded_file:
        try:
            extracted = extract_text(uploaded_file, uploaded_file.name)
            st.success(f"**{uploaded_file.name}** leído correctamente — {len(extracted):,} caracteres extraídos")
            with st.expander("Ver texto extraído"):
                st.text(extracted[:3000] + ("…" if len(extracted) > 3000 else ""))
            input_text = extracted
        except Exception as e:
            st.error(f"Error leyendo el archivo: {e}")

with audio_tab:
    st.info("Graba tu voz describiendo el proceso. El audio se transcribirá automáticamente con Google Speech.")

    # Inicializar estado
    for _k, _v in [("audio_transcription", ""), ("audio_recorded_bytes", None), ("audio_recorder_key", 0)]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # Botón limpiar ANTES del recorder para que al hacer rerun el widget se monte fresco
    if st.session_state.audio_recorded_bytes or st.session_state.audio_transcription:
        if st.button("🗑️ Nueva grabación", help="Borra el audio y la transcripción para grabar de nuevo"):
            st.session_state.audio_transcription = ""
            st.session_state.audio_recorded_bytes = None
            st.session_state.audio_recorder_key += 1   # cambia la key → React desmonta el widget
            st.rerun()

    # El key dinámico fuerza reinicio del componente React al limpiar
    audio_bytes = render_audio_recorder()

    # Nueva grabación detectada
    if audio_bytes and audio_bytes != st.session_state.audio_recorded_bytes:
        st.session_state.audio_recorded_bytes = audio_bytes
        st.session_state.audio_transcription = ""
        with st.spinner("Transcribiendo audio…"):
            try:
                st.session_state.audio_transcription = transcribe_audio_bytes(audio_bytes)
                st.success("Transcripción completada.")
            except RuntimeError as e:
                st.error(str(e))

    if st.session_state.audio_recorded_bytes:
        st.audio(st.session_state.audio_recorded_bytes, format="audio/wav")

    if st.session_state.audio_transcription:
        edited = st.text_area(
            "Texto reconocido (editable):",
            value=st.session_state.audio_transcription,
            height=140,
            key=f"transcribed_edit_{st.session_state.audio_recorder_key}",
            label_visibility="collapsed",
        )
        st.session_state.audio_transcription = edited
        input_text = edited

# ── PASO 2: Analizar ──────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
col_btn, col_warn = st.columns([3, 7])

with col_btn:
    analyze_btn = st.button(
        "🔍  Analizar con Claude",
        type="primary",
        disabled=(not input_text.strip() or not api_key),
        use_container_width=True,
    )
with col_warn:
    if not api_key:
        st.warning("Configura tu API Key de Anthropic en la barra lateral para continuar.")
    elif not input_text.strip():
        st.info("Ingresa la descripción del proceso en cualquiera de las pestañas anteriores.")

if analyze_btn and input_text.strip() and api_key:
    with st.spinner("Claude está analizando el proceso… esto tarda algunos segundos."):
        try:
            data = analyze_process(input_text, api_key, model)
            errors = validate_process_json(data)
            if errors:
                st.error("El análisis devolvió inconsistencias:\n" + "\n".join(f"- {e}" for e in errors))
            else:
                st.session_state.process_data = data
                st.session_state.bpmn_xml = None
                st.session_state.diagram_png = None
                st.success(f"Proceso **'{data.get('nombre_proceso')}'** analizado correctamente.")
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Error inesperado: {e}")

# ── PASO 3: Editar ────────────────────────────────────────────────────────────
if st.session_state.process_data:
    data = st.session_state.process_data

    _step_title(2, "✏️", "Revisa y edita el proceso")

    # Métricas resumen
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Proceso", data.get("nombre_proceso", "—")[:28])
    m2.metric("Roles identificados", len(data.get("roles", [])))
    m3.metric("Pasos del proceso", len(data.get("pasos", [])))
    decisions = sum(1 for p in data.get("pasos", []) if p.get("tipo") == "decision")
    m4.metric("Puntos de decisión", decisions)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Ficha del proceso ──
    col_name, col_desc = st.columns([2, 4])
    with col_name:
        new_name = st.text_input("Nombre del proceso", value=data.get("nombre_proceso", ""))
        if new_name != data.get("nombre_proceso"):
            st.session_state.process_data["nombre_proceso"] = new_name
    with col_desc:
        new_desc = st.text_area("Descripción / Objetivo", value=data.get("descripcion", ""), height=74)
        if new_desc != data.get("descripcion"):
            st.session_state.process_data["descripcion"] = new_desc

    col_obj, col_alc = st.columns(2)
    with col_obj:
        new_obj = st.text_area("Objetivo del proceso", value=data.get("objetivo", ""), height=68)
        if new_obj != data.get("objetivo"):
            st.session_state.process_data["objetivo"] = new_obj
    with col_alc:
        new_alc = st.text_area("Alcance", value=data.get("alcance", ""), height=68)
        if new_alc != data.get("alcance"):
            st.session_state.process_data["alcance"] = new_alc

    # ── Roles ──
    st.markdown("**👥 Roles y responsabilidades**")
    roles_df = pd.DataFrame(data.get("roles", []))[["id", "nombre", "descripcion"]]
    edited_roles = st.data_editor(
        roles_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "id":          st.column_config.TextColumn("ID", disabled=True, width="small"),
            "nombre":      st.column_config.TextColumn("Nombre del rol / Área", width="medium"),
            "descripcion": st.column_config.TextColumn("Responsabilidades en el proceso", width="large"),
        },
        key="roles_editor",
        hide_index=True,
    )
    st.session_state.process_data["roles"] = edited_roles.to_dict("records")

    # ── Pasos ──
    st.markdown("**📋 Pasos del proceso** — incluye tiempo y documentación para el .bpmn")
    st.caption("Tip: doble clic en cualquier celda para editar. Los campos se guardan en el BPMN exportado.")

    pasos_raw = data.get("pasos", [])
    pasos_df = pd.DataFrame([
        {
            "id":               p["id"],
            "nombre":           p.get("nombre", ""),
            "tipo":             p.get("tipo", "tarea"),
            "rol_id":           p.get("rol_id", ""),
            "tiempo_ejecucion": int(p.get("tiempo_ejecucion", 0)),
            "unidad_tiempo":    p.get("unidad_tiempo", "minutos"),
            "descripcion":      p.get("descripcion", ""),
            "condicion":        p.get("condicion", ""),
            "documentacion":    p.get("documentacion", ""),
            "siguiente":        ", ".join(p.get("siguiente", [])),
        }
        for p in pasos_raw
    ])

    tipo_options      = ["tarea", "decision", "inicio", "fin", "subproceso", "evento"]
    unidad_options    = ["minutos", "horas", "dias"]
    role_id_options   = [r["id"] for r in data.get("roles", [])]

    edited_pasos = st.data_editor(
        pasos_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "id":               st.column_config.TextColumn("ID", disabled=True, width="small"),
            "nombre":           st.column_config.TextColumn("Nombre de la actividad", width="medium"),
            "tipo":             st.column_config.SelectboxColumn("Tipo", options=tipo_options, width="small"),
            "rol_id":           st.column_config.SelectboxColumn("Rol responsable", options=role_id_options, width="small"),
            "tiempo_ejecucion": st.column_config.NumberColumn(
                "Tiempo", min_value=0, max_value=9999, step=1,
                help="Tiempo estimado de ejecución", width="small"
            ),
            "unidad_tiempo":    st.column_config.SelectboxColumn(
                "Unidad", options=unidad_options, width="small"
            ),
            "descripcion":      st.column_config.TextColumn("Descripción (qué se hace)", width="large"),
            "condicion":        st.column_config.TextColumn(
                "Criterio decisión", width="medium",
                help="Solo para tipo 'decision': qué condición evalúa"
            ),
            "documentacion":    st.column_config.TextColumn(
                "Instrucciones / Documentación", width="large",
                help="Instrucciones detalladas, sistemas, normas aplicables"
            ),
            "siguiente":        st.column_config.TextColumn("Siguiente(s) — separar con coma", width="medium"),
        },
        key="pasos_editor",
        hide_index=True,
    )

    pasos_updated = []
    for _, row in edited_pasos.iterrows():
        siguiente = [s.strip() for s in str(row["siguiente"]).split(",") if s.strip()]
        pasos_updated.append({
            "id":               row["id"],
            "nombre":           row["nombre"],
            "tipo":             row["tipo"],
            "rol_id":           row["rol_id"],
            "tiempo_ejecucion": int(row.get("tiempo_ejecucion", 0) or 0),
            "unidad_tiempo":    row.get("unidad_tiempo", "minutos"),
            "descripcion":      row.get("descripcion", ""),
            "condicion":        row.get("condicion", ""),
            "documentacion":    row.get("documentacion", ""),
            "siguiente":        siguiente,
        })
    st.session_state.process_data["pasos"] = pasos_updated

    # ── PASO 4: Diagrama ──────────────────────────────────────────────────────
    _step_title(3, "🖼️", "Diagrama preliminar")

    col_gen, _ = st.columns([3, 7])
    with col_gen:
        if st.button("⚡  Generar diagrama", type="primary", use_container_width=True):
            with st.spinner("Renderizando diagrama…"):
                try:
                    st.session_state.diagram_png = render_diagram(st.session_state.process_data)
                    st.session_state.bpmn_xml = generate_bpmn(st.session_state.process_data)
                    st.success("Diagrama generado.")
                except Exception as e:
                    st.error(f"Error al generar diagrama: {e}")

    if st.session_state.diagram_png:
        st.image(st.session_state.diagram_png, use_container_width=True)

    # ── PASO 5: Exportar ──────────────────────────────────────────────────────
    _step_title(4, "💾", "Exportar")

    if not st.session_state.bpmn_xml:
        try:
            st.session_state.bpmn_xml = generate_bpmn(st.session_state.process_data)
        except Exception:
            pass

    process_slug = (
        data.get("nombre_proceso", "proceso")
        .lower().replace(" ", "_")
        .replace("/", "-")[:40]
    )

    ec1, ec2, ec3 = st.columns(3)

    with ec1:
        if st.session_state.bpmn_xml:
            st.download_button(
                label="⬇️  Descargar .bpmn — Bizagi",
                data=st.session_state.bpmn_xml.encode("utf-8"),
                file_name=f"{process_slug}.bpmn",
                mime="application/xml",
                use_container_width=True,
                help="Importa este archivo en Bizagi Modeler: Archivo > Importar > BPMN 2.0",
            )
    with ec2:
        if st.session_state.diagram_png:
            st.download_button(
                label="⬇️  Descargar .png",
                data=st.session_state.diagram_png,
                file_name=f"{process_slug}.png",
                mime="image/png",
                use_container_width=True,
            )
    with ec3:
        if st.session_state.process_data:
            st.download_button(
                label="⬇️  Descargar .json",
                data=json.dumps(st.session_state.process_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{process_slug}.json",
                mime="application/json",
                use_container_width=True,
                help="JSON estructurado del proceso para reutilizar o auditar",
            )

    if st.session_state.bpmn_xml:
        with st.expander("🔍 Vista previa del XML BPMN"):
            preview = st.session_state.bpmn_xml[:4000]
            if len(st.session_state.bpmn_xml) > 4000:
                preview += "\n\n… (archivo completo al descargar)"
            st.code(preview, language="xml")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="cassa-footer">'
    '© 2026 <span>Grupo CASSA</span> · Gerencia de Analítica · '
    'Herramienta de uso interno — v1.0'
    "</div>",
    unsafe_allow_html=True,
)
