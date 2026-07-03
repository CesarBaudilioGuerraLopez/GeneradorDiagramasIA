"""Panel de administración — uso de la herramienta BPMN Tool."""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from config import get_admin_password

# ── Protección por contraseña ─────────────────────────────────────────────────
ADMIN_PASSWORD = get_admin_password()

st.set_page_config(page_title="Admin — BPMN Tool", page_icon="📊", layout="wide")

CASSA_BLUE = "#004B9A"
CASSA_DARK = "#002D5F"

st.markdown(f"""
<style>
html,body,[class*="css"]{{font-family:'Segoe UI',sans-serif;}}
.stApp{{background:#F4F6F9;}}
.kpi{{background:white;border-radius:10px;padding:16px 20px;
      box-shadow:0 1px 4px rgba(0,0,0,.08);border-top:3px solid {CASSA_BLUE};
      margin-bottom:4px;}}
.kpi-label{{font-size:.7rem;color:#64748b;font-weight:600;
            text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;}}
.kpi-value{{font-size:2rem;font-weight:700;color:{CASSA_DARK};line-height:1;}}
.kpi-sub{{font-size:.78rem;color:#94a3b8;margin-top:4px;}}
h1{{color:{CASSA_DARK}!important;}}
</style>""", unsafe_allow_html=True)

# ── Autenticación ─────────────────────────────────────────────────────────────
if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    st.title("📊 Panel de Administración")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar", type="primary"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# ── Datos ─────────────────────────────────────────────────────────────────────
try:
    from logger import get_analyses, get_exports, summary_stats
except ImportError:
    st.error("No se pudo importar logger.py. Asegúrate de estar en la carpeta bpmn_tool.")
    st.stop()

df_an  = get_analyses()
df_exp = get_exports()
stats  = summary_stats()

# ── Encabezado ────────────────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='margin-bottom:4px'>📊 Panel de Administración</h1>
<p style='color:#64748b;margin-top:0'>BPMN Tool — Grupo CASSA &nbsp;|&nbsp;
Control de uso y consumo</p>
""", unsafe_allow_html=True)

c_logout, _ = st.columns([1, 9])
with c_logout:
    if st.button("Cerrar sesión"):
        st.session_state.admin_ok = False
        st.rerun()

st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Análisis totales</div>
    <div class="kpi-value">{stats['total_analisis']}</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Usuarios únicos</div>
    <div class="kpi-value">{stats['usuarios_unicos']}</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Tokens totales</div>
    <div class="kpi-value">{stats['tokens_totales']:,}</div>
    <div class="kpi-sub">entrada + salida</div>
    </div>""", unsafe_allow_html=True)

with k4:
    costo = stats['costo_total_usd']
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Costo estimado</div>
    <div class="kpi-value">${costo:.4f}</div>
    <div class="kpi-sub">USD (Claude Sonnet)</div>
    </div>""", unsafe_allow_html=True)

with k5:
    dur = stats['duracion_promedio']
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Duración promedio</div>
    <div class="kpi-value">{dur:.1f}s</div>
    <div class="kpi-sub">por análisis</div>
    </div>""", unsafe_allow_html=True)

with k6:
    st.markdown(f"""<div class="kpi">
    <div class="kpi-label">Exportaciones</div>
    <div class="kpi-value">{stats['total_exports']}</div>
    <div class="kpi-sub">bpmn · png · json</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Gráficas ──────────────────────────────────────────────────────────────────
if not df_an.empty:
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("**Análisis por usuario**")
        u_counts = df_an.groupby("usuario").size().reset_index(name="analisis")
        u_counts = u_counts.sort_values("analisis", ascending=False)
        st.bar_chart(u_counts.set_index("usuario")["analisis"], height=220)

    with g2:
        st.markdown("**Tokens por usuario**")
        tok_u = df_an.groupby("usuario")["tokens_total"].sum().reset_index()
        tok_u = tok_u.sort_values("tokens_total", ascending=False)
        st.bar_chart(tok_u.set_index("usuario")["tokens_total"], height=220)

    g3, g4 = st.columns(2)

    with g3:
        st.markdown("**Análisis por método de entrada**")
        m_counts = df_an.groupby("metodo_entrada").size().reset_index(name="n")
        st.bar_chart(m_counts.set_index("metodo_entrada")["n"], height=200)

    with g4:
        st.markdown("**Procesos más analizados**")
        p_counts = (
            df_an[df_an["proceso"].str.strip() != ""]
            .groupby("proceso")
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
            .head(8)
        )
        if not p_counts.empty:
            st.bar_chart(p_counts.set_index("proceso")["n"], height=200)
        else:
            st.info("Sin datos de proceso aún.")

    # Evolución temporal
    st.markdown("**Análisis a lo largo del tiempo**")
    df_an["fecha"] = df_an["ts"].dt.date
    daily = df_an.groupby("fecha").size().reset_index(name="analisis")
    st.line_chart(daily.set_index("fecha")["analisis"], height=180)

else:
    st.info("Aún no hay análisis registrados. Los datos aparecerán aquí después del primer uso.")

st.divider()

# ── Tablas detalle ────────────────────────────────────────────────────────────
tab_an, tab_exp = st.tabs(["Historial de análisis", "Historial de exportaciones"])

with tab_an:
    if not df_an.empty:
        cols_show = ["ts", "usuario", "proceso", "metodo_entrada",
                     "tokens_entrada", "tokens_salida", "tokens_total",
                     "costo_usd", "duracion_seg", "modelo", "exito"]
        df_show = df_an[cols_show].copy()
        df_show["ts"]        = df_show["ts"].dt.strftime("%Y-%m-%d %H:%M")
        df_show["costo_usd"] = df_show["costo_usd"].map("${:.5f}".format)
        df_show["exito"]     = df_show["exito"].map({1: "✅", 0: "❌"})
        df_show.columns      = ["Fecha/Hora", "Usuario", "Proceso", "Método",
                                 "Tok. entrada", "Tok. salida", "Tok. total",
                                 "Costo USD", "Duración (s)", "Modelo", "Éxito"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        # Exportar a Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            df_an.drop(columns=["ts"], errors="ignore").to_excel(
                xw, sheet_name="Análisis", index=False)
            if not df_exp.empty:
                df_exp.drop(columns=["ts"], errors="ignore").to_excel(
                    xw, sheet_name="Exportaciones", index=False)
        st.download_button(
            "⬇ Exportar todo a Excel",
            data=buf.getvalue(),
            file_name="bpmn_tool_uso.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Sin registros aún.")

with tab_exp:
    if not df_exp.empty:
        df_es = df_exp.copy()
        df_es["ts"] = df_es["ts"].dt.strftime("%Y-%m-%d %H:%M")
        df_es.columns = ["ID", "Fecha/Hora", "Usuario", "Proceso", "Tipo"]
        st.dataframe(df_es, use_container_width=True, hide_index=True)

        exp_counts = df_exp.groupby("tipo_export").size().reset_index(name="n")
        st.markdown("**Exportaciones por tipo**")
        st.bar_chart(exp_counts.set_index("tipo_export")["n"], height=180)
    else:
        st.info("Sin exportaciones registradas aún.")

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:.72rem;padding:16px 0'>"
    "BPMN Tool Admin · Grupo CASSA · Analitica</div>",
    unsafe_allow_html=True,
)
