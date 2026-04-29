import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# Importamos los módulos de la carpeta calculos
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Concrete Durability & Model Code Tool", layout="wide")

# --- CSS PARA ESTILO ETH / IBK ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main { background-color: #ffffff; }
    
    /* Cabecera con Título y Tiempo Global */
    .header-box {
        border-bottom: 2px solid #e17000;
        margin-bottom: 20px;
        padding-bottom: 10px;
    }
    .title-text { font-size: 30px; font-weight: 700; color: #000000; margin: 0; }
    
    h3 { color: #444; margin-top: 20px; border-left: 5px solid #e17000; padding-left: 10px; background-color: #f9f9f9; padding-top: 5px; padding-bottom: 5px;}
    
    /* Estilo de Pestañas (Tabs) tipo IBK */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; background-color: #ffffff; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #eeeeee;
        border-radius: 4px 4px 0px 0px;
        color: #666666;
        padding: 10px 20px;
        border: 1px solid #cccccc;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid white !important;
        color: #000000 !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA (Título + Input Global de Tiempo) ---
head_col1, head_col2 = st.columns([3, 1])

with head_col1:
    st.markdown('<p class="title-text">Plataforma de Durabilidad y Capacidad Residual</p>', unsafe_allow_html=True)

with head_col2:
    # Tiempo de estudio global para toda la aplicación
    t_global = st.number_input("Tiempo de estudio total [años]", value=100, step=1, key="global_time")

# --- INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state:
    st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state:
    st.session_state['tipo_ataque'] = "Carbonatación"

# --- CREACIÓN DE PESTAÑAS ---
tab_ini, tab_mc = st.tabs(["🕒 Tiempo de Iniciación", "🏗️ Model Code (Capacidad Residual)"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
with tab_ini:
    tipo_ataque = st.radio("Seleccione el fenómeno a analizar:", ["Carbonatación", "Cloruros"], horizontal=True)
    st.session_state['tipo_ataque'] = tipo_ataque

    st.subheader(f"Parámetros de Entrada - {tipo_ataque}")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        d_mm = st.number_input("Recubrimiento $c$ [mm]", value=30.0)
        st.caption(f"Análisis a {t_global} años")
    
    if tipo_ataque == "Carbonatación":
        with c2:
            rh_real = st.slider("Humedad $RH_{real}$ [%]", 0, 100, 50)
            rh_ref = st.number_input("$RH_{ref}$ [%]", value=65.0)
        with c3:
            dias_ll = st.number_input("Días de lluvia/año", value=50)
            psr = st.number_input("Prob. lluvia $p_{sR}$", value=0.1)
        with c4:
            racc = st.number_input("$R_{acc}$ [mm²/año/kg/m³]", value=4541.32)
            csd = st.number_input("$C_{s,d}$ [kg/m³]", value=0.00082)
        
        kcd, kt, ge, fe, bw, t0 = 0.67, 1.25, 2.5, 5.0, 0.446, 0.0767
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_global)
        y_label = "Profundidad [mm]"
        limit_val = d_mm
    
    else: # Cloruros
        with c2:
            c0 = st.number_input("$C_0$ [%]", value=0.1)
            cs = st.number_input("$C_s$ [%]", value=2.0)
            ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
        with c3:
            treal = st.number_input("$T_{real}$ [K]", value=289.6)
            tref = st.number_input("$T_{ref}$ [K]", value=293.0)
        with c4:
            dcrm = st.number_input("$D_{crm}$ [mm²/año]", value=224.53)
            a_age = st.number_input("Factor edad $a$", value=0.4288)
        
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, 4800, tref, treal, 1.0, 0.0767, a_age, dcrm, t_global)
        y_label = "Concentración [%]"
        limit_val = ccrit

    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2])
    with res1:
        st.write("### Resultados")
        if t_ini_calc:
            st.metric("Tiempo de Iniciación", f"{t_ini_calc:.2f} años")
        else:
            st.error(f"Sin iniciación en {t_global} años.")
        st.dataframe(pd.DataFrame({"Año": t_i, y_label: y_vals}).head(100))
    
    with res2:
        fig_ini = go.Figure()
        fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), line=dict(color='black', dash='dash'), name="Umbral"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title=y_label, 
                            xaxis=dict(range=[0, t_global], showgrid=True, gridcolor='#eee'),
                            yaxis=dict(range=[0, max(max(y_vals), limit_val)*1.2], showgrid=True, gridcolor='#eee'))
        st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: MODEL CODE
# ==========================================
with tab_mc:
    t_ini_ref = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0
    px_limit = 0.05 if atk_type == "Carbonatación" else 0.5 # mm (50 y 500 micras)

    st.subheader("Geometría y Parámetros Estructurales")
    st.info(f"Análisis vinculado a **t_ini = {t_ini_ref:.2f} años** | Límite normativo $p_x$ = {px_limit} mm")

    c1, c2, c3 = st.columns(3)
    with c1:
        h = st.number_input("Canto h [mm]", value=300)
        b = st.number_input("Ancho b [mm]", value=150)
        icorr = st.number_input("Intensidad corrosión $i_{corr}$", value=0.5)
    with c2:
        rec_sup = st.number_input("Recubrimiento Superior [mm]", value=20)
        rec_inf = st.number_input("Recubrimiento Inferior [mm]", value=20)
        fyk = st.number_input("Límite elástico fyk [MPa]", value=500)
    with c3:
        fck = st.number_input("Resistencia fck [MPa]", value=25)
        n_inf = st.number_input("Nº barras inferiores", value=2)
        phi_inf_0 = st.number_input("Diámetro Φ inferior [mm]", value=16)

    # Cálculo Model Code (usando t_global compartido)
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(
        t_global, b, h, rec_sup, rec_inf, 2, 16, n_inf, phi_inf_0, 
        fyk, fck, icorr, alpha_v, t_ini_ref
    )

    # Identificar tiempo donde se alcanza el px_límite
    idx_lim = np.where(px_v >= px_limit)[0]
    t_els = t_v[idx_lim[0]] if len(idx_lim) > 0 else None

    st.divider()
    g1, g2 = st.columns(2)

    with g1:
        st.write("### Capacidad Resistente $M_{Rd}$ vs Tiempo")
        fig_m_t = go.Figure()
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_res, name="Mrd (Approach 1)", line=dict(color='#e17000', width=3)))
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_cons, name="Mrd (Conservative)", line=dict(color='#333', dash='dash')))
        if t_els:
            fig_m_t.add_vline(x=t_els, line_dash="dot", line_color="red", annotation_text=f"ELS: {t_els:.1f} a")
        fig_m_t.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]",
                            xaxis=dict(range=[0, t_global], showgrid=True, gridcolor='#eee'),
                            yaxis=dict(range=[0, max(m_res)*1.1], showgrid=True, gridcolor='#eee'))
        st.plotly_chart(fig_m_t, use_container_width=True)

    with g2:
        st.write("### Capacidad Resistente $M_{Rd}$ vs Profundidad $p_x$")
        fig_m_px = go.Figure()
        fig_m_px.add_trace(go.Scatter(x=px_v, y=m_res, name="Mrd vs px", line=dict(color='#8E6713', width=3)))
        fig_m_px.add_vline(x=px_limit, line_dash="dash", line_color="red", annotation_text=f"Límite {px_limit}mm")
        fig_m_px.update_layout(plot_bgcolor='white', xaxis_title="px [mm]", yaxis_title="Mrd [kNm]",
                             xaxis=dict(range=[0, max(max(px_v), px_limit)*1.1 if len(px_v)>0 else 1], showgrid=True, gridcolor='#eee'), 
                             yaxis=dict(range=[0, max(m_res)*1.1], showgrid=True, gridcolor='#eee'))
        st.plotly_chart(fig_m_px, use_container_width=True)

    if t_els:
        st.success(f"**Vida Útil ELS (p_x = {px_limit} mm):** Alcanzada a los {t_els:.2f} años.")
