"""BPMN Tool â€” Interfaz principal Streamlit con branding Grupo CASSA."""

import base64
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import get_api_key, get_model, set_api_key, set_model, is_cloud
from file_readers import extract_text
from audio_input import render_audio_recorder, transcribe_audio_bytes
from analyzer import analyze_process, validate_process_json
try:
    from analyzer import analyze_process_stream
    _STREAMING = True
except ImportError:
    _STREAMING = False
from bpmn_generator import generate_bpmn
from diagram_renderer import render_diagram

# â”€â”€ Rutas de assets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ASSETS = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS / "logo_cassa.png"

# â”€â”€ Colores CASSA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CASSA_BLUE  = "#004B9A"
CASSA_GREEN = "#00A651"
CASSA_LIGHT = "#E8F0FA"
CASSA_DARK  = "#002D5F"

# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _inject_css():
    st.markdown(
        f"""
<style>
/* â”€â”€ Reset y tipografÃ­a â”€â”€ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* â”€â”€ Fondo principal â”€â”€ */
.stApp {{
    background-color: #F4F6F9;
}}

/* â”€â”€ Header corporativo â”€â”€ */
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

/* â”€â”€ Sidebar â”€â”€ */
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

/* â”€â”€ Tarjetas de secciÃ³n â”€â”€ */
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

/* â”€â”€ Step badges â”€â”€ */
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

/* â”€â”€ BotÃ³n primario â”€â”€ */
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

/* â”€â”€ Botones de descarga â”€â”€ */
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

/* â”€â”€ Tabs â”€â”€ */
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

/* â”€â”€ MÃ©tricas â”€â”€ */
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

/* â”€â”€ Alertas â”€â”€ */
[data-testid="stAlert"] {{
    border-radius: 8px !important;
}}

/* â”€â”€ DataEditor â”€â”€ */
[data-testid="stDataFrame"], [data-testid="data-grid-canvas"] {{
    border-radius: 8px !important;
}}

/* â”€â”€ Footer â”€â”€ */
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

/* â”€â”€ Ocultar elementos Streamlit por defecto â”€â”€ */
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
        <p>AnalÃ­tica & GestiÃ³n del Conocimiento â€” Grupo CASSA</p>
    </div>
    <div class="cassa-badge">âœ¦ BETA</div>
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

        # SecciÃ³n: ConfiguraciÃ³n API
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">âš™ ConfiguraciÃ³n</div>', unsafe_allow_html=True)

        if is_cloud():
            # En la nube la key viene de Streamlit Secrets â€” no se edita aquÃ­
            if api_key:
                st.markdown(
                    '<div style="background:rgba(0,166,81,0.2);border:1px solid #00A651;'
                    'border-radius:8px;padding:10px 12px;font-size:0.82rem;color:#b8f5d4">'
                    'ðŸ” <b>API Key configurada</b><br>'
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
            'âš¡ Modelo: <b style="color:white">Claude Sonnet</b></div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # SecciÃ³n: Estado
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">â—‰ Estado de sesiÃ³n</div>', unsafe_allow_html=True)
        if api_key:
            st.markdown("ðŸŸ¢ **API Key:** Configurada")
        else:
            st.markdown("ðŸ”´ **API Key:** No configurada")
        if st.session_state.get("process_data"):
            n_roles = len(st.session_state.process_data.get("roles", []))
            n_pasos = len(st.session_state.process_data.get("pasos", []))
            st.markdown(f"ðŸ”µ **Proceso cargado**")
            st.markdown(f"&nbsp;&nbsp;&nbsp;â€¢ {n_roles} roles Â· {n_pasos} pasos")
        else:
            st.markdown("âšª Sin proceso cargado")
        st.markdown("</div>", unsafe_allow_html=True)

        # SecciÃ³n: GuÃ­a rÃ¡pida
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section-title">ðŸ“– GuÃ­a rÃ¡pida</div>', unsafe_allow_html=True)
        st.markdown(
            """
<small style="color:rgba(255,255,255,0.75);line-height:1.7">
1. Configura tu API Key (una sola vez)<br>
2. Describe el proceso con texto, archivo o micrÃ³fono<br>
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
            "BPMN Tool v1.0 Â· AnalÃ­tica CASSA</div>",
            unsafe_allow_html=True,
        )

    return api_key, model


def _step_title(n: int, icon: str, title: str):
    st.markdown(
        f'<div class="step-title"><span class="step-badge">{n}</span>{icon} {title}</div>',
        unsafe_allow_html=True,
    )


# â”€â”€ App principal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.set_page_config(
    page_title="BPMN Tool â€” Grupo CASSA",
    page_icon="ðŸ“Š",
    layout="wide",
    initial_sidebar_state="expanded",
)

_inject_css()
_render_header()

# Estado de sesiÃ³n
for key in ("process_data", "bpmn_xml", "diagram_png"):
    if key not in st.session_state:
        st.session_state[key] = None

# Sidebar (carga y persiste config)
api_key = get_api_key()
model = "claude-sonnet-4-6"   # fijo, no configurable por el usuario
api_key, model = _render_sidebar(api_key, model)

# â”€â”€ PASO 1: Entrada â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_step_title(1, "ðŸ“", "Describe tu proceso")

input_text = ""
input_tab, file_tab, audio_tab = st.tabs(["âœï¸  Texto libre", "ðŸ“  Cargar archivo", "ðŸŽ™ï¸  MicrÃ³fono"])

with input_tab:
    input_text_area = st.text_area(
        "Escribe el proceso con tus propias palabras:",
        height=180,
        placeholder=(
            "Ejemplo: El proceso inicia cuando el Ã¡rea solicitante envÃ­a una requisiciÃ³n de compra. "
            "El jefe de Ã¡rea la aprueba si el monto es menor a $5,000. Para montos mayores, "
            "pasa a revisiÃ³n de Finanzas. Luego Compras emite la orden de compra al proveedor..."
        ),
        label_visibility="collapsed",
    )
    if input_text_area:
        input_text = input_text_area

with file_tab:
    # â”€â”€ BotÃ³n descarga de plantilla â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    template_path = ASSETS / "Plantilla_Proceso_CASSA.xlsx"
    if template_path.exists():
        col_dl, col_hint = st.columns([2, 5])
        with col_dl:
            st.download_button(
                label="ðŸ“¥ Descargar plantilla Excel",
                data=template_path.read_bytes(),
                file_name="Plantilla_Proceso_CASSA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                help="Plantilla estandarizada con columnas pre-definidas para mejor reconocimiento",
            )
        with col_hint:
            st.info("Usa la plantilla para que la herramienta identifique automÃ¡ticamente "
                    "roles, responsables y tiempos sin ambigÃ¼edad.")

    st.markdown("---")
    uploaded_file = st.file_uploader(
        "Sube un archivo Word, Excel o texto:",
        type=["docx", "xlsx", "xls", "txt", "md"],
        help="Word, Excel (con o sin plantilla), TXT o Markdown.",
        label_visibility="collapsed",
    )
    if uploaded_file:
        try:
            extracted, meta = extract_text(uploaded_file, uploaded_file.name)

            # â”€â”€ Mostrar columnas detectadas si es Excel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if meta.get("modo") == "plantilla":
                cols_det = meta.get("columnas_detectadas", {})
                filas = meta.get("filas_detectadas", 0)
                st.success(
                    f"**{uploaded_file.name}** â€” Plantilla detectada con {filas} pasos"
                )
                if cols_det:
                    _FIELD_LABELS = {
                        "id": "ID del paso", "nombre": "Nombre actividad",
                        "tipo": "Tipo", "rol": "Responsable / Ãrea",
                        "descripcion": "DescripciÃ³n", "tiempo_ejecucion": "Tiempo",
                        "unidad_tiempo": "Unidad", "documentacion": "Instrucciones",
                        "condicion": "CondiciÃ³n decisiÃ³n", "siguiente": "Siguiente paso",
                    }
                    st.markdown("**Columnas identificadas en tu archivo:**")
                    badge_html = " ".join(
                        f'<span style="background:#E8F4FD;border:1px solid #AED6F1;'
                        f'border-radius:12px;padding:3px 10px;font-size:0.8rem;margin:2px;display:inline-block">'
                        f'âœ… <b>{_FIELD_LABELS.get(campo, campo)}</b> '
                        f'â† <code>{orig}</code></span>'
                        for campo, orig in cols_det.items()
                    )
                    st.markdown(badge_html, unsafe_allow_html=True)

                    # Columnas importantes que faltan
                    missing = [f for f in ("nombre", "rol", "siguiente")
                               if f not in cols_det]
                    if missing:
                        labels_miss = [_FIELD_LABELS.get(f, f) for f in missing]
                        st.warning(f"No se encontraron: **{', '.join(labels_miss)}**. "
                                   "Claude intentarÃ¡ inferirlas del contexto.")

            elif meta.get("modo") == "generico" and uploaded_file.name.endswith((".xlsx", ".xls")):
                st.warning(
                    "No se reconocieron encabezados estÃ¡ndar en el Excel. "
                    "Se enviarÃ¡ como texto plano. Para mejor reconocimiento, "
                    "descarga y usa la **plantilla CASSA**."
                )
                st.success(f"**{uploaded_file.name}** â€” {len(extracted):,} caracteres extraÃ­dos")
            else:
                st.success(
                    f"**{uploaded_file.name}** leÃ­do correctamente â€” {len(extracted):,} caracteres"
                )

            with st.expander("Ver texto que se enviarÃ¡ a Claude"):
                st.text(extracted[:3000] + ("â€¦" if len(extracted) > 3000 else ""))
            input_text = extracted
        except Exception as e:
            st.error(f"Error leyendo el archivo: {e}")

with audio_tab:
    st.info("Graba tu voz describiendo el proceso. El audio se transcribirÃ¡ automÃ¡ticamente con Google Speech.")

    # Inicializar estado
    for _k, _v in [("audio_transcription", ""), ("audio_recorded_bytes", None), ("audio_recorder_key", 0)]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # BotÃ³n limpiar ANTES del recorder para que al hacer rerun el widget se monte fresco
    if st.session_state.audio_recorded_bytes or st.session_state.audio_transcription:
        if st.button("ðŸ—‘ï¸ Nueva grabaciÃ³n", help="Borra el audio y la transcripciÃ³n para grabar de nuevo"):
            st.session_state.audio_transcription = ""
            st.session_state.audio_recorded_bytes = None
            st.session_state.audio_recorder_key += 1   # cambia la key â†’ React desmonta el widget
            st.rerun()

    # El key dinÃ¡mico fuerza reinicio del componente React al limpiar
    audio_bytes = render_audio_recorder()

    # Nueva grabaciÃ³n detectada
    if audio_bytes and audio_bytes != st.session_state.audio_recorded_bytes:
        st.session_state.audio_recorded_bytes = audio_bytes
        st.session_state.audio_transcription = ""
        with st.spinner("Transcribiendo audioâ€¦"):
            try:
                st.session_state.audio_transcription = transcribe_audio_bytes(audio_bytes)
                st.success("TranscripciÃ³n completada.")
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

# â”€â”€ PASO 2: Analizar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
col_btn, col_warn = st.columns([3, 7])

with col_btn:
    analyze_btn = st.button(
        "ðŸ”  Analizar con Claude",
        type="primary",
        disabled=(not input_text.strip() or not api_key),
        width="stretch",
    )
with col_warn:
    if not api_key:
        st.warning("Configura tu API Key de Anthropic en la barra lateral para continuar.")
    elif not input_text.strip():
        st.info("Ingresa la descripciÃ³n del proceso en cualquiera de las pestaÃ±as anteriores.")

if analyze_btn and input_text.strip() and api_key:
    if _STREAMING:
        # â”€â”€ Modo streaming con barra de progreso â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with st.status("Analizando proceso con Claude...", expanded=True) as status:
            try:
                st.write("Conectando con Claude Sonnet...")
                bar  = st.progress(0, text="Generando estructura del procesoâ€¦")
                data = None

                for chars_done, chars_total, result in analyze_process_stream(
                    input_text, api_key, model
                ):
                    if result is not None:
                        data = result
                    else:
                        pct = min(int(chars_done / max(chars_total, 1) * 90), 90)
                        bar.progress(pct, text=f"Claude generandoâ€¦ {chars_done} caracteres")

                bar.progress(100, text="Listo.")
                errors = validate_process_json(data)
                if errors:
                    status.update(label="Advertencias en el anÃ¡lisis", state="error", expanded=True)
                    st.error("\n".join(f"- {e}" for e in errors))
                else:
                    st.session_state.process_data = data
                    st.session_state.bpmn_xml     = None
                    st.session_state.diagram_png  = None
                    n = len(data.get("pasos", []))
                    status.update(
                        label=f"âœ… '{data.get('nombre_proceso')}' â€” {n} pasos",
                        state="complete", expanded=False)
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(str(e))
    else:
        # â”€â”€ Modo simple (fallback sin streaming) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        with st.spinner("Claude estÃ¡ analizando el procesoâ€¦"):
            try:
                data   = analyze_process(input_text, api_key, model)
                errors = validate_process_json(data)
                if errors:
                    st.error("\n".join(f"- {e}" for e in errors))
                else:
                    st.session_state.process_data = data
                    st.session_state.bpmn_xml     = None
                    st.session_state.diagram_png  = None
                    st.success(f"Proceso **'{data.get('nombre_proceso')}'** analizado.")
            except Exception as e:
                st.error(str(e))

# â”€â”€ PASO 3: Editar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if st.session_state.process_data:
    data = st.session_state.process_data

    _step_title(2, "âœï¸", "Revisa y edita el proceso")

    # MÃ©tricas resumen
    nombre = data.get("nombre_proceso", "â€”")
    decisions = sum(1 for p in data.get("pasos", []) if p.get("tipo") == "decision")
    n_roles = len(data.get("roles", []))
    n_pasos = len(data.get("pasos", []))

    st.markdown(
        f"""
<div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap">
  <div style="flex:2;min-width:180px;background:white;border-radius:10px;padding:16px 18px;
              box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid {CASSA_BLUE}">
    <div style="font-size:0.72rem;color:#64748b;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:4px">Proceso</div>
    <div style="font-size:1.15rem;font-weight:700;color:{CASSA_DARK};line-height:1.3">{nombre}</div>
  </div>
  <div style="flex:1;min-width:110px;background:white;border-radius:10px;padding:16px 18px;
              box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid {CASSA_GREEN}">
    <div style="font-size:0.72rem;color:#64748b;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:4px">Roles</div>
    <div style="font-size:1.8rem;font-weight:700;color:{CASSA_DARK}">{n_roles}</div>
  </div>
  <div style="flex:1;min-width:110px;background:white;border-radius:10px;padding:16px 18px;
              box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid {CASSA_GREEN}">
    <div style="font-size:0.72rem;color:#64748b;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:4px">Pasos</div>
    <div style="font-size:1.8rem;font-weight:700;color:{CASSA_DARK}">{n_pasos}</div>
  </div>
  <div style="flex:1;min-width:110px;background:white;border-radius:10px;padding:16px 18px;
              box-shadow:0 1px 4px rgba(0,0,0,0.07);border-top:3px solid #f39c12">
    <div style="font-size:0.72rem;color:#64748b;font-weight:600;text-transform:uppercase;
                letter-spacing:.5px;margin-bottom:4px">Decisiones</div>
    <div style="font-size:1.8rem;font-weight:700;color:{CASSA_DARK}">{decisions}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # â”€â”€ Ficha del proceso â”€â”€
    col_name, col_desc = st.columns([2, 4])
    with col_name:
        new_name = st.text_input("Nombre del proceso", value=data.get("nombre_proceso", ""))
        if new_name != data.get("nombre_proceso"):
            st.session_state.process_data["nombre_proceso"] = new_name
    with col_desc:
        new_desc = st.text_area("DescripciÃ³n / Objetivo", value=data.get("descripcion", ""), height=74)
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

    # â”€â”€ Roles â”€â”€
    st.markdown("**ðŸ‘¥ Roles y responsabilidades**")
    roles_df = pd.DataFrame(data.get("roles", []))[["id", "nombre", "descripcion"]]
    edited_roles = st.data_editor(
        roles_df,
        width="stretch",
        num_rows="dynamic",
        column_config={
            "id":          st.column_config.TextColumn("ID", disabled=True, width="small"),
            "nombre":      st.column_config.TextColumn("Nombre del rol / Ãrea", width="medium"),
            "descripcion": st.column_config.TextColumn("Responsabilidades en el proceso", width="large"),
        },
        key="roles_editor",
        hide_index=True,
    )
    st.session_state.process_data["roles"] = edited_roles.to_dict("records")

    # â”€â”€ Pasos â”€â”€
    st.markdown("**ðŸ“‹ Pasos del proceso** â€” incluye tiempo y documentaciÃ³n para el .bpmn")
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
        width="stretch",
        num_rows="dynamic",
        column_config={
            "id":               st.column_config.TextColumn("ID", disabled=True, width="small"),
            "nombre":           st.column_config.TextColumn("Nombre de la actividad", width="medium"),
            "tipo":             st.column_config.SelectboxColumn("Tipo", options=tipo_options, width="small"),
            "rol_id":           st.column_config.SelectboxColumn("Rol responsable", options=role_id_options, width="small"),
            "tiempo_ejecucion": st.column_config.NumberColumn(
                "Tiempo", min_value=0, max_value=9999, step=1,
                help="Tiempo estimado de ejecuciÃ³n", width="small"
            ),
            "unidad_tiempo":    st.column_config.SelectboxColumn(
                "Unidad", options=unidad_options, width="small"
            ),
            "descripcion":      st.column_config.TextColumn("DescripciÃ³n (quÃ© se hace)", width="large"),
            "condicion":        st.column_config.TextColumn(
                "Criterio decisiÃ³n", width="medium",
                help="Solo para tipo 'decision': quÃ© condiciÃ³n evalÃºa"
            ),
            "documentacion":    st.column_config.TextColumn(
                "Instrucciones / DocumentaciÃ³n", width="large",
                help="Instrucciones detalladas, sistemas, normas aplicables"
            ),
            "siguiente":        st.column_config.TextColumn("Siguiente(s) â€” separar con coma", width="medium"),
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

    # â”€â”€ PASO 4: Diagrama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _step_title(3, "ðŸ–¼ï¸", "Diagrama preliminar")

    col_gen, _ = st.columns([3, 7])
    with col_gen:
        if st.button("âš¡  Generar diagrama", type="primary", width="stretch"):
            with st.spinner("Renderizando diagramaâ€¦"):
                try:
                    st.session_state.diagram_png = render_diagram(st.session_state.process_data)
                    st.session_state.bpmn_xml = generate_bpmn(st.session_state.process_data)
                    st.success("Diagrama generado.")
                except Exception as e:
                    st.error(f"Error al generar diagrama: {e}")

    if st.session_state.diagram_png:
        st.image(st.session_state.diagram_png, width="stretch")

    # â”€â”€ PASO 5: Exportar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _step_title(4, "ðŸ’¾", "Exportar")

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
                label="â¬‡ï¸  Descargar .bpmn â€” Bizagi",
                data=st.session_state.bpmn_xml.encode("utf-8"),
                file_name=f"{process_slug}.bpmn",
                mime="application/xml",
                width="stretch",
                help="Importa este archivo en Bizagi Modeler: Archivo > Importar > BPMN 2.0",
            )
    with ec2:
        if st.session_state.diagram_png:
            st.download_button(
                label="â¬‡ï¸  Descargar .png",
                data=st.session_state.diagram_png,
                file_name=f"{process_slug}.png",
                mime="image/png",
                width="stretch",
            )
    with ec3:
        if st.session_state.process_data:
            st.download_button(
                label="â¬‡ï¸  Descargar .json",
                data=json.dumps(st.session_state.process_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{process_slug}.json",
                mime="application/json",
                width="stretch",
                help="JSON estructurado del proceso para reutilizar o auditar",
            )

    if st.session_state.bpmn_xml:
        with st.expander("ðŸ” Vista previa del XML BPMN"):
            preview = st.session_state.bpmn_xml[:4000]
            if len(st.session_state.bpmn_xml) > 4000:
                preview += "\n\nâ€¦ (archivo completo al descargar)"
            st.code(preview, language="xml")

# â”€â”€ Footer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
st.markdown(
    '<div class="cassa-footer">'
    'Â© 2026 <span>Grupo CASSA</span> Â· Gerencia de AnalÃ­tica Â· '
    'Herramienta de uso interno â€” v1.0'
    "</div>",
    unsafe_allow_html=True,
)

