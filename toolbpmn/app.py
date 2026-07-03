"""BPMN Tool - Interfaz principal Streamlit con branding Grupo CASSA."""

# set_page_config DEBE ir antes de imports pesados (matplotlib, etc.)
# para que el health-check de Streamlit Cloud no falle.
import streamlit as st

st.set_page_config(
    page_title="BPMN Tool - Grupo CASSA",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import base64
import json
import time
import traceback
from pathlib import Path

try:
    import pandas as pd

    from config import get_api_key, set_api_key, is_cloud
    from file_readers import extract_text
    from audio_input import (
        render_audio_recorder,
        transcribe_audio_bytes,
        merge_segment_texts,
        new_segment,
    )
    from analyzer import analyze_process, validate_process_json
    from layout_engine import normalize_process_data
    from logger import log_analysis, log_export
except Exception as _boot_err:
    st.error("Error al iniciar la aplicacion.")
    st.code(traceback.format_exc())
    st.stop()

try:
    from analyzer import analyze_process_stream
    _HAS_STREAM = True
except Exception:
    _HAS_STREAM = False

ASSETS    = Path(__file__).parent / "assets"
LOGO_PATH = ASSETS / "logo_cassa.png"

CASSA_BLUE  = "#004B9A"
CASSA_GREEN = "#00A651"
CASSA_LIGHT = "#E8F0FA"
CASSA_DARK  = "#002D5F"
MODEL       = "claude-sonnet-4-6"


def _render_diagram(data):
    from diagram_renderer import render_diagram
    return render_diagram(data)


def _generate_bpmn(data):
    from bpmn_generator import generate_bpmn
    return generate_bpmn(data)


def _b64(path):
    return base64.b64encode(path.read_bytes()).decode()


def _css():
    st.markdown(f"""
<style>
html, body, [class*="css"] {{ font-family: 'Segoe UI', system-ui, sans-serif; }}
.stApp {{ background-color: #F4F6F9; }}
.cassa-hdr {{
  background: linear-gradient(135deg,{CASSA_DARK},{CASSA_BLUE} 60%,#1565C0);
  padding:16px 28px; border-radius:0 0 12px 12px;
  display:flex; align-items:center; gap:20px;
  margin:-1rem -1rem 1.5rem -1rem;
  box-shadow:0 4px 16px rgba(0,75,154,.25);
}}
.cassa-hdr img {{ height:48px; filter:brightness(0) invert(1); }}
.cassa-hdr-t h1 {{ color:white!important; font-size:1.35rem!important;
  font-weight:700!important; margin:0!important; padding:0!important; }}
.cassa-hdr-t p {{ color:rgba(255,255,255,.72)!important;
  font-size:.8rem!important; margin:2px 0 0!important; }}
.cassa-badge {{ margin-left:auto; background:rgba(0,166,81,.22);
  border:1px solid {CASSA_GREEN}; color:#b8f5d4;
  font-size:.72rem; font-weight:600; padding:3px 11px; border-radius:20px; }}
/* Barra lateral completamente oculta (sin panel ni boton para abrirla) */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] {{
  display:none!important; visibility:hidden!important;
  width:0!important; min-width:0!important; height:0!important;
  overflow:hidden!important; pointer-events:none!important;
}}
.step-badge {{ display:inline-flex; align-items:center; justify-content:center;
  width:26px; height:26px; background:{CASSA_BLUE}; color:white;
  border-radius:50%; font-size:.78rem; font-weight:700; margin-right:8px; }}
.step-title {{ color:{CASSA_DARK}; font-size:1rem; font-weight:700;
  display:flex; align-items:center; margin:22px 0 10px; }}
[data-testid="stButton"]>button[kind="primary"] {{
  background:linear-gradient(135deg,{CASSA_BLUE},{CASSA_DARK})!important;
  color:white!important; border:none!important; border-radius:8px!important;
  font-weight:600!important; box-shadow:0 2px 8px rgba(0,75,154,.3)!important; }}
[data-testid="stDownloadButton"]>button {{
  background:white!important; color:{CASSA_BLUE}!important;
  border:2px solid {CASSA_BLUE}!important; border-radius:8px!important;
  font-weight:600!important; }}
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  background:white; border-radius:10px 10px 0 0; padding:4px 4px 0;
  border:1px solid #e2e8f0; border-bottom:none; gap:2px; }}
[data-testid="stTabs"] [aria-selected="true"] {{
  background:{CASSA_BLUE}!important; color:white!important; font-weight:600!important; }}
[data-testid="stTabContent"] {{
  background:white; border:1px solid #e2e8f0; border-top:none;
  border-radius:0 0 10px 10px; padding:18px; }}
#MainMenu, footer, header {{ visibility:hidden; }}
.block-container {{ padding-top:0!important; max-width:1200px; }}
.cassa-footer {{ text-align:center; padding:18px 0 6px; color:#94a3b8;
  font-size:.73rem; border-top:1px solid #e2e8f0; margin-top:28px; }}
.cassa-footer span {{ color:{CASSA_BLUE}; font-weight:600; }}
</style>""", unsafe_allow_html=True)


def _header():
    logo_html = ""
    if LOGO_PATH.exists():
        logo_html = f'<img src="data:image/png;base64,{_b64(LOGO_PATH)}" alt="CASSA"/>'
    st.markdown(f"""
<div class="cassa-hdr">
  {logo_html}
  <div class="cassa-hdr-t">
    <h1>Generador de Procesos BPMN</h1>
    <p>Analitica &amp; Gestion del Conocimiento &mdash; Grupo CASSA</p>
  </div>
  <div class="cassa-badge">&#10022; BETA</div>
</div>""", unsafe_allow_html=True)


def _step(n, icon, title):
    st.markdown(
        f'<div class="step-title"><span class="step-badge">{n}</span>{icon} {title}</div>',
        unsafe_allow_html=True)


_css()
_header()

# Estado de sesion
for _k in ("process_data", "bpmn_xml", "diagram_png"):
    if _k not in st.session_state:
        st.session_state[_k] = None

for _k, _v in [
    ("audio_segments", []),
    ("audio_pending_bytes", None),
    ("audio_recorder_key", 0),
    ("audio_unified_text", ""),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

uploaded = None

api_key = get_api_key()

# Solo en local (no Cloud): pedir API key en el area principal si falta
if not is_cloud() and not api_key:
    with st.expander("Configurar API Key Anthropic", expanded=True):
        new_key = st.text_input("API Key", type="password", label_visibility="collapsed")
        if new_key:
            set_api_key(new_key)
            api_key = new_key
            st.rerun()
elif is_cloud() and not api_key:
    st.error("API Key no configurada en Streamlit Secrets.")

# Nombre obligatorio para registro de uso
st.markdown(
    f'<div style="font-size:.85rem;font-weight:600;color:{CASSA_DARK};'
    f'margin:4px 0 6px">Digita tu nombre <span style="color:#e74c3c">*</span></div>',
    unsafe_allow_html=True,
)
_name_col, _name_msg = st.columns([2, 5])
with _name_col:
    _uname = st.text_input(
        "Digita tu nombre",
        value=st.session_state.get("user_name", ""),
        placeholder="Ej: Juan Perez",
        label_visibility="collapsed",
        key="user_name_input",
    )
    st.session_state["user_name"] = _uname.strip()

_has_name = bool(st.session_state.get("user_name", "").strip())
with _name_msg:
    if _has_name:
        st.success(f"Usuario: **{st.session_state['user_name']}**")
    else:
        st.warning("Digita tu nombre para continuar.")

if not _has_name:
    st.markdown(
        f'<div style="background:#FFF3CD;border:1px solid #FFECB5;border-left:4px solid #f39c12;'
        f'border-radius:8px;padding:10px 14px;margin:4px 0 12px;color:#856404;font-size:.9rem">'
        f'<b>Nombre obligatorio.</b> Escribe tu nombre arriba para poder describir el proceso '
        f'y analizarlo con Claude.</div>',
        unsafe_allow_html=True,
    )

# ── PASO 1: Entrada ───────────────────────────────────────────────────────────
_step(1, "", "Describe tu proceso")

input_text = ""
tab_txt, tab_file, tab_mic = st.tabs(["Texto libre", "Cargar archivo", "Microfono"])

with tab_txt:
    txt = st.text_area(
        "Escribe el proceso:",
        height=175,
        placeholder=(
            "Ejemplo: El proceso inicia cuando el cliente solicita una cotizacion. "
            "El vendedor la revisa; si es menor a $5,000 la aprueba directamente, "
            "si es mayor la envia a Finanzas..."
        ),
        label_visibility="collapsed",
        disabled=not _has_name,
    )
    if txt and _has_name:
        input_text = txt

with tab_file:
    TEMPLATE_PATH = ASSETS / "Plantilla_Proceso_CASSA.xlsx"
    if TEMPLATE_PATH.exists():
        col_dl, col_info = st.columns([2, 5])
        with col_dl:
            st.download_button(
                label="Descargar plantilla Excel",
                data=TEMPLATE_PATH.read_bytes(),
                file_name="Plantilla_Proceso_CASSA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col_info:
            st.info("Usa la plantilla para que la herramienta identifique "
                    "automaticamente roles, responsables y tiempos.")
    st.markdown("---")
    uploaded = st.file_uploader(
        "Sube un archivo:",
        type=["docx", "xlsx", "xls", "txt", "md"],
        label_visibility="collapsed",
        disabled=not _has_name,
    )
    if uploaded and _has_name:
        try:
            extracted, meta = extract_text(uploaded, uploaded.name)
            if meta.get("modo") == "plantilla":
                cols_det = meta.get("columnas_detectadas", {})
                filas    = meta.get("filas_detectadas", 0)
                st.success(f"**{uploaded.name}** - Plantilla detectada: {filas} pasos")
                if cols_det:
                    LABELS = {
                        "id": "ID paso", "nombre": "Nombre actividad",
                        "tipo": "Tipo", "rol": "Responsable",
                        "descripcion": "Descripcion", "tiempo_ejecucion": "Tiempo",
                        "unidad_tiempo": "Unidad", "documentacion": "Instrucciones",
                        "condicion": "Condicion", "siguiente": "Siguiente paso",
                    }
                    badges = " ".join(
                        f'<span style="background:#E8F4FD;border:1px solid #AED6F1;'
                        f'border-radius:12px;padding:2px 9px;font-size:.78rem;'
                        f'margin:2px;display:inline-block">'
                        f'OK <b>{LABELS.get(c,c)}</b> &larr; <code>{o}</code></span>'
                        for c, o in cols_det.items()
                    )
                    st.markdown(badges, unsafe_allow_html=True)
            elif meta.get("modo") == "generico" and uploaded.name.endswith((".xlsx",".xls")):
                st.warning("Sin encabezados estandar - se envia como texto plano.")
            else:
                st.success(f"**{uploaded.name}** - {len(extracted):,} caracteres")
            with st.expander("Ver texto extraido"):
                st.text(extracted[:2500] + ("..." if len(extracted) > 2500 else ""))
            input_text = extracted
        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")

with tab_mic:
    if not _has_name:
        st.warning("Digita tu nombre arriba para habilitar el microfono.")
    st.info(
        "Graba tu voz por segmentos. Detén la grabación, "
        "pulsa **Guardar segmento y continuar**, y graba el siguiente bloque."
    )

    if _has_name and (st.session_state.audio_segments or st.session_state.audio_pending_bytes):
        if st.button("Limpiar todo el audio", help="Borra todos los segmentos grabados"):
            st.session_state.audio_segments = []
            st.session_state.audio_pending_bytes = None
            st.session_state.audio_unified_text = ""
            st.session_state.audio_recorder_key += 1
            st.rerun()

    audio = None
    if _has_name:
        try:
            audio = render_audio_recorder(key=st.session_state.audio_recorder_key)
        except Exception as _audio_err:
            st.warning(f"Micrófono no disponible: {_audio_err}")
            audio = None
    if _has_name and audio and audio != st.session_state.audio_pending_bytes:
        st.session_state.audio_pending_bytes = audio

    pending = st.session_state.audio_pending_bytes if _has_name else None
    if pending:
        st.audio(pending, format="audio/wav")
        if st.button("Guardar segmento y continuar", type="primary"):
            seg_id = len(st.session_state.audio_segments) + 1
            with st.spinner(f"Transcribiendo segmento {seg_id}..."):
                try:
                    text = transcribe_audio_bytes(pending)
                    st.session_state.audio_segments.append(
                        new_segment(seg_id, text=text, audio_bytes=pending)
                    )
                    st.session_state.audio_pending_bytes = None
                    st.session_state.audio_recorder_key += 1
                    st.session_state.audio_unified_text = merge_segment_texts(
                        st.session_state.audio_segments
                    )
                    st.success(f"Segmento {seg_id} guardado.")
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

    segments = st.session_state.audio_segments
    if segments:
        st.markdown(f"**{len(segments)} segmento(s) guardado(s)**")
        for idx, seg in enumerate(segments):
            with st.expander(f"Segmento {seg['id']}", expanded=(idx == len(segments) - 1)):
                c_up, c_dn, c_del, c_re = st.columns([1, 1, 1, 2])
                with c_up:
                    if st.button("Subir", key=f"seg_up_{idx}", disabled=(idx == 0)):
                        segments[idx], segments[idx - 1] = segments[idx - 1], segments[idx]
                        st.session_state.audio_unified_text = merge_segment_texts(segments)
                        st.rerun()
                with c_dn:
                    if st.button("Bajar", key=f"seg_dn_{idx}", disabled=(idx == len(segments) - 1)):
                        segments[idx], segments[idx + 1] = segments[idx + 1], segments[idx]
                        st.session_state.audio_unified_text = merge_segment_texts(segments)
                        st.rerun()
                with c_del:
                    if st.button("Eliminar", key=f"seg_del_{idx}"):
                        segments.pop(idx)
                        for i, s in enumerate(segments, 1):
                            s["id"] = i
                        st.session_state.audio_unified_text = merge_segment_texts(segments)
                        st.rerun()
                with c_re:
                    if seg.get("audio_bytes") and st.button(
                        "Re-transcribir", key=f"seg_re_{idx}"
                    ):
                        with st.spinner("Re-transcribiendo..."):
                            try:
                                seg["text"] = transcribe_audio_bytes(seg["audio_bytes"])
                                st.session_state.audio_unified_text = merge_segment_texts(segments)
                                st.rerun()
                            except RuntimeError as e:
                                st.error(str(e))

                if seg.get("audio_bytes"):
                    st.audio(seg["audio_bytes"], format="audio/wav")

                new_text = st.text_area(
                    "Texto del segmento:",
                    value=seg.get("text", ""),
                    height=100,
                    key=f"seg_text_{idx}_{st.session_state.audio_recorder_key}",
                    label_visibility="collapsed",
                )
                if new_text != seg.get("text", ""):
                    seg["text"] = new_text
                    st.session_state.audio_unified_text = merge_segment_texts(segments)

        st.session_state.audio_unified_text = merge_segment_texts(segments)

        if st.button("Unificar todo", use_container_width=True):
            st.session_state.audio_unified_text = merge_segment_texts(segments)
            st.success("Texto unificado listo para analizar.")

        unified = st.session_state.audio_unified_text
        if unified:
            st.text_area(
                "Texto unificado del proceso:",
                value=unified,
                height=130,
                key="mic_unified_preview",
                label_visibility="collapsed",
            )
            input_text = unified

# ── PASO 2: Analizar ──────────────────────────────────────────────────────────
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
c1, c2 = st.columns([3, 7])
with c1:
    btn_analyze = st.button(
        "Analizar con Claude",
        type="primary",
        disabled=(not _has_name or not input_text.strip() or not api_key),
        use_container_width=True,
    )
with c2:
    if not _has_name:
        st.warning("Digita tu nombre para continuar.")
    elif not api_key:
        st.warning("API Key no configurada.")
    elif not input_text.strip():
        st.info("Ingresa la descripcion del proceso.")

if btn_analyze and _has_name and input_text.strip() and api_key:
    _usuario = st.session_state.get("user_name", "").strip()
    if not _usuario:
        st.error("Digita tu nombre para continuar.")
        st.stop()
    _metodo  = (
        "archivo" if uploaded
        else "microfono" if st.session_state.get("audio_segments")
        else "texto"
    )
    if _HAS_STREAM:
        with st.status("Analizando proceso con Claude...", expanded=True) as _status:
            _t0 = time.time()
            _ok = False
            try:
                st.write("Conectando con Claude Sonnet...")
                _bar   = st.progress(0, text="Generando estructura...")
                _data  = None
                _usage = None
                for _c, _t, _res, _u in analyze_process_stream(input_text, api_key, MODEL):
                    if _res is not None:
                        _data  = _res
                        _usage = _u
                    else:
                        _bar.progress(min(int(_c / max(_t,1) * 90), 90),
                                      text=f"Claude generando... {_c} chars")
                _bar.progress(100, text="Listo.")
                _errs = validate_process_json(_data)
                if _errs:
                    _status.update(label="Advertencias", state="error", expanded=True)
                    st.error("\n".join(f"- {e}" for e in _errs))
                else:
                    st.session_state.process_data = normalize_process_data(_data)
                    st.session_state.bpmn_xml     = None
                    st.session_state.diagram_png  = None
                    _ok = True
                    _status.update(
                        label=f"'{_data.get('nombre_proceso')}' - {len(_data.get('pasos',[]))} pasos",
                        state="complete", expanded=False)
            except Exception as _e:
                _status.update(label="Error", state="error")
                st.error(str(_e))
                _usage = None
            finally:
                log_analysis(
                    usuario=_usuario,
                    proceso=(_data or {}).get("nombre_proceso", ""),
                    metodo=_metodo,
                    chars=len(input_text),
                    tok_in=(_usage or {}).get("input_tokens", 0),
                    tok_out=(_usage or {}).get("output_tokens", 0),
                    modelo=MODEL,
                    dur_seg=time.time() - _t0,
                    exito=_ok,
                )
    else:
        with st.spinner("Claude esta analizando el proceso..."):
            _t0 = time.time()
            _ok = False
            try:
                _data, _usage = analyze_process(input_text, api_key, MODEL)
                _errs = validate_process_json(_data)
                if _errs:
                    st.error("\n".join(f"- {e}" for e in _errs))
                else:
                    st.session_state.process_data = normalize_process_data(_data)
                    st.session_state.bpmn_xml     = None
                    st.session_state.diagram_png  = None
                    _ok = True
                    st.success(f"Proceso '{_data.get('nombre_proceso')}' analizado.")
            except Exception as _e:
                st.error(str(_e))
                _usage = {}
            finally:
                log_analysis(
                    usuario=_usuario,
                    proceso=(_data or {}).get("nombre_proceso", ""),
                    metodo=_metodo,
                    chars=len(input_text),
                    tok_in=(_usage or {}).get("input_tokens", 0),
                    tok_out=(_usage or {}).get("output_tokens", 0),
                    modelo=MODEL,
                    dur_seg=time.time() - _t0,
                    exito=_ok,
                )

# ── PASO 3: Editar ────────────────────────────────────────────────────────────
if st.session_state.process_data and not _has_name:
    st.warning("Digita tu nombre para continuar editando el proceso.")
elif st.session_state.process_data and _has_name:
    data      = st.session_state.process_data
    nombre    = data.get("nombre_proceso", "")
    decisions = sum(1 for p in data.get("pasos",[]) if p.get("tipo") == "decision")

    _step(2, "", "Revisa y edita el proceso")

    st.markdown(f"""
<div style="display:flex;gap:11px;margin-bottom:14px;flex-wrap:wrap">
  <div style="flex:2;min-width:180px;background:white;border-radius:10px;
    padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);
    border-top:3px solid {CASSA_BLUE}">
    <div style="font-size:.7rem;color:#64748b;font-weight:600;text-transform:uppercase;
      letter-spacing:.5px;margin-bottom:3px">Proceso</div>
    <div style="font-size:1.1rem;font-weight:700;color:{CASSA_DARK};line-height:1.3">{nombre}</div>
  </div>
  <div style="flex:1;min-width:100px;background:white;border-radius:10px;
    padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);
    border-top:3px solid {CASSA_GREEN}">
    <div style="font-size:.7rem;color:#64748b;font-weight:600;text-transform:uppercase;
      letter-spacing:.5px;margin-bottom:3px">Roles</div>
    <div style="font-size:1.75rem;font-weight:700;color:{CASSA_DARK}">{len(data.get("roles",[]))}</div>
  </div>
  <div style="flex:1;min-width:100px;background:white;border-radius:10px;
    padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);
    border-top:3px solid {CASSA_GREEN}">
    <div style="font-size:.7rem;color:#64748b;font-weight:600;text-transform:uppercase;
      letter-spacing:.5px;margin-bottom:3px">Pasos</div>
    <div style="font-size:1.75rem;font-weight:700;color:{CASSA_DARK}">{len(data.get("pasos",[]))}</div>
  </div>
  <div style="flex:1;min-width:100px;background:white;border-radius:10px;
    padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07);
    border-top:3px solid #f39c12">
    <div style="font-size:.7rem;color:#64748b;font-weight:600;text-transform:uppercase;
      letter-spacing:.5px;margin-bottom:3px">Decisiones</div>
    <div style="font-size:1.75rem;font-weight:700;color:{CASSA_DARK}">{decisions}</div>
  </div>
</div>""", unsafe_allow_html=True)

    def _str(v, default=""):
        """Streamlit text_input/text_area no aceptan None."""
        if v is None:
            return default
        return str(v)

    ca, cb = st.columns([2, 4])
    with ca:
        nn = st.text_input("Nombre del proceso", value=_str(data.get("nombre_proceso")))
        if nn != _str(data.get("nombre_proceso")):
            st.session_state.process_data["nombre_proceso"] = nn
    with cb:
        nd = st.text_area("Descripcion / Objetivo", value=_str(data.get("descripcion")), height=80)
        if nd != _str(data.get("descripcion")):
            st.session_state.process_data["descripcion"] = nd

    cc, cd = st.columns(2)
    with cc:
        no = st.text_area("Objetivo", value=_str(data.get("objetivo")), height=80)
        if no != _str(data.get("objetivo")):
            st.session_state.process_data["objetivo"] = no
    with cd:
        na = st.text_area("Alcance", value=_str(data.get("alcance")), height=80)
        if na != _str(data.get("alcance")):
            st.session_state.process_data["alcance"] = na

    # ── Helpers para leer celdas del DataFrame con seguridad ─────────────────
    def _sv(v, default=""):
        if v is None:
            return default
        try:
            if pd.isna(v):
                return default
        except (TypeError, ValueError):
            pass
        return str(v)

    def _iv(v, default=0):
        if v is None:
            return default
        try:
            if pd.isna(v):
                return default
        except (TypeError, ValueError):
            pass
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return default

    # ── Roles y responsabilidades ─────────────────────────────────────────────
    with st.expander("Roles y responsabilidades", expanded=True):
        st.caption("Doble clic para editar un campo. Usa el boton + para agregar roles nuevos.")
        roles_raw = data.get("roles", [])
        roles_df  = pd.DataFrame([{
            "id":          _str(r.get("id"), f"role_{i+1}"),
            "nombre":      _str(r.get("nombre")),
            "descripcion": _str(r.get("descripcion")),
        } for i, r in enumerate(roles_raw)])
        if roles_df.empty:
            roles_df = pd.DataFrame(columns=["id", "nombre", "descripcion"])

        edited_roles = st.data_editor(
            roles_df, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={
                "id":          st.column_config.TextColumn("ID (clave)", width="small"),
                "nombre":      st.column_config.TextColumn("Nombre del rol", width="medium"),
                "descripcion": st.column_config.TextColumn("Responsabilidades", width="large"),
            }, key="roles_ed")

        roles_clean = []
        for i, row in edited_roles.iterrows():
            nombre_r = _sv(row.get("nombre"))
            if not nombre_r.strip():
                continue
            rid = _sv(row.get("id")).strip() or f"role_{len(roles_clean)+1}"
            roles_clean.append({
                "id":          rid,
                "nombre":      nombre_r.strip(),
                "descripcion": _sv(row.get("descripcion")),
            })
        st.session_state.process_data["roles"] = roles_clean
        _norm = normalize_process_data(st.session_state.process_data)
        st.session_state.process_data["roles"] = _norm["roles"]
        st.session_state.process_data["pasos"] = _norm["pasos"]
        rol_opts = [r["id"] for r in _norm["roles"]]
        if len(_norm["roles"]) > len(roles_clean):
            st.info("Se agregaron carriles para roles referenciados en los pasos.")

    # ── Pasos del proceso ─────────────────────────────────────────────────────
    st.markdown("**Pasos del proceso**")
    st.caption("Doble clic en cualquier celda para editar.")
    pasos_raw = st.session_state.process_data.get("pasos", [])
    rol_opts_set = set(rol_opts)
    for p in pasos_raw:
        rid = p.get("rol_id")
        if rid and rid not in rol_opts_set:
            rol_opts.append(rid)
            rol_opts_set.add(rid)
    pasos_df  = pd.DataFrame([{
        "id":               _str(p.get("id")),
        "nombre":           _str(p.get("nombre")),
        "tipo":             _str(p.get("tipo"), "tarea") or "tarea",
        "rol_id":           _str(p.get("rol_id")),
        "tiempo_ejecucion": int(p.get("tiempo_ejecucion", 0) or 0),
        "unidad_tiempo":    _str(p.get("unidad_tiempo"), "minutos") or "minutos",
        "descripcion":      _str(p.get("descripcion")),
        "condicion":        _str(p.get("condicion")),
        "documentacion":    _str(p.get("documentacion")),
        "siguiente":        ", ".join(p.get("siguiente") or []),
    } for p in pasos_raw])

    tipo_opts   = ["tarea", "decision", "inicio", "fin", "subproceso", "evento"]
    unidad_opts = ["minutos", "horas", "dias"]

    edited_pasos = st.data_editor(
        pasos_df, use_container_width=True, num_rows="dynamic", hide_index=True,
        column_config={
            "id":               st.column_config.TextColumn("ID", disabled=True, width="small"),
            "nombre":           st.column_config.TextColumn("Actividad", width="medium"),
            "tipo":             st.column_config.SelectboxColumn("Tipo", options=tipo_opts, width="small"),
            "rol_id":           st.column_config.SelectboxColumn("Rol", options=rol_opts, width="small"),
            "tiempo_ejecucion": st.column_config.NumberColumn("Tiempo", min_value=0, max_value=9999, step=1, width="small"),
            "unidad_tiempo":    st.column_config.SelectboxColumn("Unidad", options=unidad_opts, width="small"),
            "descripcion":      st.column_config.TextColumn("Descripcion", width="large"),
            "condicion":        st.column_config.TextColumn("Criterio decision", width="medium"),
            "documentacion":    st.column_config.TextColumn("Instrucciones", width="large"),
            "siguiente":        st.column_config.TextColumn("Siguiente(s) (separar coma)", width="medium"),
        }, key="pasos_ed")

    pasos_up = []
    for _, row in edited_pasos.iterrows():
        sig = [s.strip() for s in _sv(row.get("siguiente")).split(",") if s.strip()]
        pasos_up.append({
            "id":               _sv(row.get("id")),
            "nombre":           _sv(row.get("nombre")),
            "tipo":             _sv(row.get("tipo"), "tarea"),
            "rol_id":           _sv(row.get("rol_id")),
            "tiempo_ejecucion": _iv(row.get("tiempo_ejecucion")),
            "unidad_tiempo":    _sv(row.get("unidad_tiempo"), "minutos"),
            "descripcion":      _sv(row.get("descripcion")),
            "condicion":        _sv(row.get("condicion")),
            "documentacion":    _sv(row.get("documentacion")),
            "siguiente":        sig,
        })
    st.session_state.process_data["pasos"] = pasos_up
    st.session_state.process_data = normalize_process_data(st.session_state.process_data)

    # ── PASO 4: Diagrama ──────────────────────────────────────────────────────
    _step(3, "", "Diagrama y editor visual")
    st.caption(
        "Genera el diagrama y editalo en el modelador: agrega tareas, carriles (lanes) "
        "y conexiones. Pulsa **Guardar en el proceso** dentro del editor para aplicar."
    )
    c_gen, c_hint = st.columns([3, 7])
    with c_gen:
        if st.button("Generar / actualizar diagrama", type="primary", use_container_width=True):
            with st.spinner("Renderizando diagrama..."):
                try:
                    st.session_state.diagram_png = _render_diagram(st.session_state.process_data)
                    st.session_state.bpmn_xml = _generate_bpmn(st.session_state.process_data)
                    st.session_state.bpmn_editor_key = st.session_state.get("bpmn_editor_key", 0) + 1
                    st.success("Diagrama generado.")
                except Exception as e:
                    st.error(f"Error al generar diagrama: {e}")
                    with st.expander("Detalle del error"):
                        st.code(traceback.format_exc())
    with c_hint:
        st.info(
            "En el editor: usa la paleta a la izquierda del lienzo. "
            "Clic derecho en un carril para **Append Lane**. "
            "Arrastra flechas entre actividades para conectar."
        )

    # Asegurar XML aunque solo exista process_data
    if st.session_state.process_data and not st.session_state.bpmn_xml:
        try:
            st.session_state.bpmn_xml = _generate_bpmn(st.session_state.process_data)
        except Exception:
            pass

    if st.session_state.bpmn_xml:
        try:
            from bpmn_editor_ui import render_bpmn_editor
            from bpmn_parser import parse_bpmn_to_process_data

            editor_key = f"bpmn_ed_{st.session_state.get('bpmn_editor_key', 0)}"
            result = render_bpmn_editor(
                st.session_state.bpmn_xml,
                height=640,
                key=editor_key,
            )
            if result and isinstance(result, dict) and result.get("xml"):
                new_xml = result["xml"]
                # Evitar reaplicar el mismo guardado en cada rerun
                if new_xml != st.session_state.get("_last_saved_bpmn_xml"):
                    try:
                        updated = parse_bpmn_to_process_data(
                            new_xml, st.session_state.process_data
                        )
                        updated = normalize_process_data(updated)
                        st.session_state.process_data = updated
                        st.session_state.bpmn_xml = new_xml
                        st.session_state._last_saved_bpmn_xml = new_xml
                        st.session_state.diagram_png = _render_diagram(updated)
                        st.success(
                            "Proceso actualizado desde el editor visual "
                            f"({len(updated.get('roles', []))} roles, "
                            f"{len(updated.get('pasos', []))} pasos)."
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo aplicar el BPMN editado: {e}")
                        with st.expander("Detalle"):
                            st.code(traceback.format_exc())
        except Exception as e:
            st.warning(f"Editor visual no disponible: {e}")

    if st.session_state.diagram_png:
        with st.expander("Vista previa PNG", expanded=False):
            st.image(st.session_state.diagram_png, use_container_width=True)

    # ── PASO 5: Exportar ──────────────────────────────────────────────────────
    _step(4, "", "Exportar")
    if not st.session_state.bpmn_xml and not st.session_state.diagram_png:
        st.caption("Genera el diagrama para habilitar la descarga .bpmn y .png.")

    slug = (data.get("nombre_proceso","proceso")
            .lower().replace(" ","_").replace("/","-")[:38])
    _usuario_exp = st.session_state.get("user_name", "Anonimo")
    _proc_exp    = data.get("nombre_proceso", "")
    e1, e2, e3 = st.columns(3)
    with e1:
        if st.session_state.bpmn_xml:
            if st.download_button(
                "Descargar .bpmn - Bizagi",
                data=st.session_state.bpmn_xml.encode("utf-8"),
                file_name=f"{slug}.bpmn", mime="application/xml",
                use_container_width=True,
                help="Archivo > Importar > BPMN 2.0 en Bizagi Modeler"):
                log_export(_usuario_exp, _proc_exp, "bpmn")
    with e2:
        if st.session_state.diagram_png:
            if st.download_button(
                "Descargar .png",
                data=st.session_state.diagram_png,
                file_name=f"{slug}.png", mime="image/png",
                use_container_width=True):
                log_export(_usuario_exp, _proc_exp, "png")
    with e3:
        if st.session_state.process_data:
            if st.download_button(
                "Descargar .json",
                data=json.dumps(st.session_state.process_data,
                                ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{slug}.json", mime="application/json",
                use_container_width=True):
                log_export(_usuario_exp, _proc_exp, "json")

    if st.session_state.bpmn_xml:
        with st.expander("Vista previa del XML BPMN"):
            prev = st.session_state.bpmn_xml[:3500]
            if len(st.session_state.bpmn_xml) > 3500:
                prev += "\n\n... (archivo completo al descargar)"
            st.code(prev, language="xml")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="cassa-footer">'
    '&copy; 2026 <span>Grupo CASSA</span> &middot; '
    'Gerencia de Analitica &middot; v1.0'
    "</div>", unsafe_allow_html=True)
