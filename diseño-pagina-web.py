import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# Importamos los módulos de la carpeta calculos
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc
from calculos import Contevect as calc_cv

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Concrete Durability & Structural Capacity Tool", layout="wide")

# --- CSS PARA ESTILO ETH / IBK ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main { background-color: #ffffff; }
    .header-box { border-bottom: 2px solid #e17000; margin-bottom: 20px; padding-bottom: 10px; }
    .title-text { font-size: 30px; font-weight: 700; color: #000000; margin: 0; }
    h3 { color: #444; margin-top: 20px; border-left: 5px solid #e17000; padding-left: 10px; background-color: #f9f9f9; padding-top: 5px; padding-bottom: 5px;}
    .stTabs [data-baseweb="tab-list"] { gap: 2px; background-color: #ffffff; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #eeeeee; border-radius: 4px 4px 0px 0px;
        color: #666666; padding: 10px 20px; border: 1px solid #cccccc;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important; border-bottom: 1px solid white !important;
        color: #000000 !important; font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown('<p class="title-text">Plataforma de Durabilidad y Capacidad Residual</p>', unsafe_allow_html=True)
with head_col2:
    t_global = st.number_input("Tiempo de estudio total [años]", value=100, step=1, key="global_time")

# --- VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state:
    st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state:
    st.session_state['tipo_ataque'] = "Carbonatación"

tab_ini, tab_mc = st.tabs(["🕒 Tiempo de Iniciación", "🏗️ Capacidad Estructural (Comparativa)"])

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
            racc = st.number_input("$R_{acc}$", value=4541.32)
            csd = st.number_input("$C_{s,d}$", value=0.00082)
        kcd, kt, ge, fe, bw, t0 = 0.67, 1.25, 2.5, 5.0, 0.446, 0.0767
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_global)
        y_label, limit_val = "Profundidad [mm]", d_mm
    else:
        with c2:
            c0, cs, ccrit = st.number_input("$C_0$ [%]", value=0.1), st.number_input("$C_s$ [%]", value=2.0), st.number_input("$C_{crit}$ [%]", value=0.6)
        with c3:
            treal, tref = st.number_input("$T_{real}$ [K]", value=289.6), st.number_input("$T_{ref}$ [K]", value=293.0)
        with c4:
            dcrm, a_age = st.number_input("$D_{crm}$", value=224.53), st.number_input("Factor edad $a$", value=0.4288)
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, 4800, tref, treal, 1.0, 0.0767, a_age, dcrm, t_global)
        y_label, limit_val = "Concentración [%]", ccrit

    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2])
    with res1:
        st.write("### Resultados")
        if t_ini_calc: st.metric("Tiempo de Iniciación", f"{t_ini_calc:.2f} años")
        else: st.error(f"Sin iniciación en {t_global} años.")
        st.dataframe(pd.DataFrame({"Año": t_i, y_label: y_vals}).head(100))
    with res2:
        fig_ini = go.Figure()
        fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), line=dict(color='black', dash='dash'), name="Umbral"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title=y_label, xaxis=dict(range=[0, t_global]))
        st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL
# ==========================================
with tab_mc:
    t_ini_ref = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0
    px_limit = 0.05 if atk_type == "Carbonatación" else 0.5 

    st.subheader("Geometría y Parámetros Estructurales")
    st.info(f"Análisis vinculado a **t_ini = {t_ini_ref:.2f} años**")

    c1, c2, c3 = st.columns(3)
    with c1:
        h, b, icorr = st.number_input("Canto h [mm]", value=300), st.number_input("Ancho b [mm]", value=150), st.number_input("Intensidad $i_{corr}$", value=0.5)
    with c2:
        rec_sup, rec_inf, fyk = st.number_input("Recubrimiento Sup. [mm]", value=20), st.number_input("Recubrimiento Inf. [mm]", value=20), st.number_input("fyk [MPa]", value=500)
    with c3:
        fck, n_inf, phi_inf_0 = st.number_input("fck [MPa]", value=25), st.number_input("Nº barras inf.", value=2), st.number_input("Φ barras inf. [mm]", value=16)

    # --- CÁLCULOS ---
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(t_global, b, h, rec_sup, rec_inf, 2, 16, n_inf, phi_inf_0, fyk, fck, icorr, alpha_v, t_ini_ref)
    t_cv, df_crit, m_vect = calc_cv.calcular_contevect(t_global, b, h, rec_sup, rec_inf, n_inf, phi_inf_0, fyk, fck, icorr, alpha_v, t_ini_ref)

    st.divider()
    g1, g2 = st.columns(2)

    with g1:
        st.write("### Momento Resistente $M_{Rd}$ vs Tiempo")
        fig_m_t = go.Figure()
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_res, name="MC Approach 1", line=dict(color='#e17000', width=2)))
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_cons, name="MC Conservative", line=dict(color='#333', dash='dash')))
        fig_m_t.add_trace(go.Scatter(x=t_cv, y=m_vect, name="Contevect (Interp)", line=dict(color='#005293', width=3)))
        
        # Puntos Clave Contevect
        fig_m_t.add_trace(go.Scatter(x=df_crit["Tiempo"], y=df_crit["Mu"], mode='markers+text', name="Eventos Contevect",
                                 marker=dict(color='red', size=10, symbol='diamond'),
                                 text=["P0", "P1", "P2", "P3", "P4"][:len(df_crit)], textposition="top left"))
        
        # Línea Vertical Iniciación
        fig_m_t.add_vline(x=t_ini_ref, line_width=2, line_dash="solid", line_color="green", annotation_text="Iniciación")
        
        fig_m_t.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]", xaxis=dict(range=[0, t_global]), yaxis=dict(range=[0, max(m_res)*1.1]))
        st.plotly_chart(fig_m_t, use_container_width=True)

    with g2:
        st.write("### Profundidad de Corrosión $P_x$ vs Tiempo")
        fig_px_t = go.Figure()
        fig_px_t.add_trace(go.Scatter(x=t_v, y=px_v, fill='tozeroy', name="Px", line=dict(color='#8E6713', width=3)))
        fig_px_t.add_vline(x=t_ini_ref, line_width=2, line_dash="solid", line_color="green", annotation_text="Iniciación")
        fig_px_t.add_hline(y=px_limit, line_dash="dash", line_color="red", annotation_text=f"Límite {px_limit}mm")
        fig_px_t.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Px [mm]", xaxis=dict(range=[0, t_global]))
        st.plotly_chart(fig_px_t, use_container_width=True)

    with st.expander("Ver Matriz de Eventos Críticos (Contevect)"):
        st.dataframe(df_crit[["Tiempo", "Px", "b", "d", "Mu"]].style.format({"Tiempo": "{:.1f}", "Px": "{:.4f}", "Mu": "{:.2f}"}))
