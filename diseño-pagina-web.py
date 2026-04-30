import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc
from calculos import Contevect as calc_cv

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Concrete Durability & Structural Capacity Tool", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333333; }
    .main { background-color: #ffffff; }
    .title-text { font-size: 30px; font-weight: 700; color: #000000; border-bottom: 2px solid #e17000; padding-bottom: 10px; margin-bottom: 20px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: #eeeeee; border-radius: 4px 4px 0px 0px; color: #666666; padding: 10px 20px; border: 1px solid #cccccc; }
    .stTabs [aria-selected="true"] { background-color: #ffffff !important; border-bottom: 1px solid white !important; color: #000000 !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown('<p class="title-text">Plataforma de Durabilidad y Capacidad Residual</p>', unsafe_allow_html=True)
with head_col2:
    t_global = st.number_input("Tiempo de estudio total [años]", value=100, step=1, key="global_time")

# --- VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state: st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state: st.session_state['tipo_ataque'] = "Carbonatación"

tab_ini, tab_mc = st.tabs(["🕒 Tiempo de Iniciación", "🏗️ Capacidad Estructural (Comparativa)"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
with tab_ini:
    tipo_ataque = st.radio("Seleccione el fenómeno a analizar:", ["Carbonatación", "Cloruros"], horizontal=True)
    st.session_state['tipo_ataque'] = tipo_ataque

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        d_mm = st.number_input("Recubrimiento $c$ [mm]", value=30.0)
    
    if tipo_ataque == "Carbonatación":
        with c2: rh_real = st.slider("Humedad $RH_{real}$ [%]", 0, 100, 50); rh_ref = 65.0
        with c3: dias_ll = st.number_input("Días de lluvia/año", value=50); psr = 0.1
        with c4: racc = st.number_input("$R_{acc}$", value=4541.32); csd = 0.00082
        kcd, kt, ge, fe, bw, t0 = 0.67, 1.25, 2.5, 5.0, 0.446, 0.0767
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_global)
        y_label, limit_val = "Profundidad [mm]", d_mm
    else:
        with c2: c0 = 0.1; cs = 2.0; ccrit = 0.6
        with c3: treal = 289.6; tref = 293.0
        with c4: dcrm = 224.53; a_age = 0.4288
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, 4800, tref, treal, 1.0, 0.0767, a_age, dcrm, t_global)
        y_label, limit_val = "Concentración [%]", ccrit

    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2])
    with res1:
        if t_ini_calc: st.metric("Tiempo de Iniciación", f"{t_ini_calc:.2f} años")
        else: st.error(f"Sin iniciación en {t_global} años.")
        st.dataframe(pd.DataFrame({"Año": t_i, y_label: y_vals}).head(50))
    with res2:
        fig_ini = go.Figure()
        fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), line=dict(color='black', dash='dash'), name="Límite"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title=y_label, xaxis=dict(range=[0, t_global]))
        st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL
# ==========================================
with tab_mc:
    t_ini = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0
    px_limit = 0.05 if atk_type == "Carbonatación" else 0.5 

    st.subheader("Geometría y Parámetros Estructurales")
    st.info(f"Fase de Iniciación: **{t_ini:.2f} años** (Periodo sin pérdida de capacidad)")

    c1, c2, c3 = st.columns(3)
    with c1: h = st.number_input("Canto h [mm]", value=300); b = st.number_input("Ancho b [mm]", value=150); icorr = st.number_input("Intensidad $i_{corr}$", value=0.5)
    with c2: rec_sup = st.number_input("Recubrimiento Sup. [mm]", value=20); rec_inf = st.number_input("Recubrimiento Inf. [mm]", value=20); fyk = st.number_input("fyk [MPa]", value=500)
    with c3: fck = st.number_input("fck [MPa]", value=25); n_inf = st.number_input("Nº barras inf.", value=2); phi_inf_0 = st.number_input("Φ barras inf. [mm]", value=16)

    # --- CÁLCULOS ---
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(t_global, b, h, rec_sup, rec_inf, 2, 16, n_inf, phi_inf_0, fyk, fck, icorr, alpha_v, t_ini)
    t_cv, df_crit, m_vect = calc_cv.calcular_contevect(t_global, b, h, rec_sup, rec_inf, n_inf, phi_inf_0, fyk, fck, icorr, alpha_v, t_ini)

    st.divider()
    g1, g2 = st.columns(2)

    with g1:
        st.write("### Momento Resistente vs Tiempo")
        fig1 = go.Figure()
        
        # Líneas horizontales de capacidad inicial (0 a t_ini)
        m_inicial = m_res[0] 
        t_pre = np.linspace(0, t_ini, 20)
        m_pre = [m_inicial] * len(t_pre)

        # MC Approach 1
        fig1.add_trace(go.Scatter(x=np.concatenate([t_pre, t_v[t_v > t_ini]]), 
                                 y=np.concatenate([m_pre, m_res[t_v > t_ini]]), 
                                 name="MC Approach 1", line=dict(color='#e17000', width=2)))
        
        # Contevect (Añadimos tramo horizontal inicial)
        fig1.add_trace(go.Scatter(x=np.concatenate([t_pre, t_cv[t_cv > t_ini]]), 
                                 y=np.concatenate([m_pre, m_vect[t_cv > t_ini]]), 
                                 name="Contevect (Interp)", line=dict(color='#005293', width=3)))
        
        # Puntos Clave
        fig1.add_trace(go.Scatter(x=df_crit["Tiempo"], y=df_crit["Mu"], mode='markers',
                                 marker=dict(color='red', size=12, symbol='diamond'), name="Puntos Clave"))

        # Línea de Iniciación
        fig1.add_vline(x=t_ini, line_width=2, line_dash="solid", line_color="green", annotation_text="Iniciación")

        fig1.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]",
                          xaxis=dict(range=[0, t_global]), yaxis=dict(range=[0, m_inicial*1.1]))
        st.plotly_chart(fig1, use_container_width=True)

    with g2:
        st.write("### Profundidad de Corrosión $P_x$ vs Tiempo")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=t_v, y=px_v, fill='tozeroy', name="px [mm]", line=dict(color='#8E6713', width=3)))
        fig2.add_vline(x=t_ini, line_width=2, line_dash="solid", line_color="green", annotation_text="Iniciación")
        fig2.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="px [mm]",
                          xaxis=dict(range=[0, t_global]), yaxis=dict(range=[0, max(px_v)*1.2 if len(px_v)>0 else 1]))
        st.plotly_chart(fig2, use_container_width=True)
