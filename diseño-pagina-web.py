import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# Importamos los dos módulos de la carpeta calculos
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Concrete Durability & Model Code Tool", layout="wide")

# --- CSS PARA ESTILO ETH / IBK (Pestañas grises y líneas naranjas) ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main { background-color: #ffffff; }
    h1 { color: #000000; font-weight: 700; border-bottom: 2px solid #e17000; padding-bottom: 10px; margin-bottom: 20px;}
    h3 { color: #444; margin-top: 20px; border-left: 5px solid #e17000; padding-left: 10px; background-color: #f9f9f9; padding-top: 5px; padding-bottom: 5px;}
    
    /* Estilo de Pestañas (Tabs) tipo IBK */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: #ffffff;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #eeeeee;
        border-radius: 4px 4px 0px 0px;
        color: #666666;
        font-weight: 400;
        padding: 10px 20px;
        border: 1px solid #cccccc;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid white !important;
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Inputs compactos */
    .stNumberInput, .stSlider { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("Plataforma de Durabilidad y Capacidad Residual")

# --- CREACIÓN DE PESTAÑAS (Tabs) ---
tab_ini, tab_mc = st.tabs(["🕒 Tiempo de Iniciación", "🏗️ Model Code (Capacidad Residual)"])

# --- PESTAÑA 1: TIEMPO DE INICIACIÓN ---
with tab_ini:
    tipo_ataque = st.radio("Seleccione el fenómeno a analizar:", ["Carbonatación", "Cloruros"], horizontal=True)
    
    # Asignar ALPHA según el ataque (se usará en la segunda pestaña también)
    alpha = 2.0 if tipo_ataque == "Carbonatación" else 10.0
    st.session_state['alpha_global'] = alpha

    st.subheader(f"Parámetros de Entrada - {tipo_ataque}")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        d_mm = st.number_input("Recubrimiento $c$ [mm]", value=30.0, key="c_ini")
        t_ana = st.number_input("Tiempo análisis [años]", value=100, key="t_ini_val")
    
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
        t, w, xcd, t_ini_res = calc_ini.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_ana)
    
    else: # Cloruros
        with c2:
            c0 = st.number_input("$C_0$ [%]", value=0.1)
            cs = st.number_input("$C_s$ [%]", value=2.0)
            ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
        with c3:
            treal = st.number_input("$T_{real}$ [K]", value=289.6)
            tref = st.number_input("$T_{ref}$ [K]", value=293.0)
        with c4:
            dcrm = st.number_input("$D_{crm}$", value=224.53)
            a_age = st.number_input("Factor edad $a$", value=0.4288)
        
        t, dapp, z, conc, t_ini_res = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, 4800, tref, treal, 1.0, 0.0767, a_age, dcrm, t_ana)

    st.divider()
    res1, res2 = st.columns([1, 2])
    with res1:
        st.write("### Resultados")
        if t_ini_res: st.metric("Iniciación estimada", f"{t_ini_res:.2f} años")
        else: st.error("No se alcanza el recubrimiento.")
        st.dataframe(pd.DataFrame({"Año": t, "Xcd/C(t)": (xcd if tipo_ataque=="Carbonatación" else conc)}).head(50))
    with res2:
        fig_ini = go.Figure()
        y_val = xcd if tipo_ataque=="Carbonatación" else conc
        limit = d_mm if tipo_ataque=="Carbonatación" else ccrit
        fig_ini.add_trace(go.Scatter(x=t, y=y_val, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t, y=[limit]*len(t), line=dict(color='black', dash='dash'), name="Límite"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Años", title=f"Evolución {tipo_ataque}")
        st.plotly_chart(fig_ini, use_container_width=True)

# --- PESTAÑA 2: MODEL CODE ---
with tab_mc:
    st.subheader("Geometría y Parámetros de Corrosión")
    
    # Siguiendo el diseño de la imagen del usuario: Inputs en columnas
    row1_c1, row1_c2, row1_c3 = st.columns(3)
    
    with row1_c1:
        h = st.number_input("Canto [mm]", value=300)
        b = st.number_input("Ancho [mm]", value=150)
        t_ana_mc = st.number_input("Tiempo análisis [años]", value=100, key="t_mc")
    
    with row1_c2:
        rec_sup = st.number_input("Recubrimiento superior [mm]", value=20)
        rec_inf = st.number_input("Recubrimiento inferior [mm]", value=20)
        fyk = st.number_input("fyk [MPa]", value=500)
    
    with row1_c3:
        fck = st.number_input("fck [MPa]", value=25)
        icorr = st.number_input("Intensidad corrosión ($i_{corr}$)", value=0.5)
        alpha_val = st.write(f"**Factor Alpha aplicado:** {st.session_state.get('alpha_global', 2.0)} (de pestaña Iniciación)")

    st.write("---")
    st.write("**Armaduras**")
    arm_c1, arm_c2 = st.columns(2)
    with arm_c1:
        n_sup = st.number_input("Nº barras superiores", value=2)
        phi_sup_0 = st.number_input("Φ superior inicial [mm]", value=16)
    with arm_c2:
        n_inf = st.number_input("Nº barras inferiores", value=2)
        phi_inf_0 = st.number_input("Φ inferior inicial [mm]", value=16)

    # Cálculo Model Code
    t_mc_v, px, phi_sup_t, phi_inf_t, mu_res, mu_cons = calc_mc.calcular_capacidad_residual(
        t_ana_mc, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
        fyk, fck, icorr, st.session_state.get('alpha_global', 2.0)
    )

    st.divider()
    
    # Gráficos
    g_c1, g_c2 = st.columns(2)
    
    with g_c1:
        st.write("### Momento Resistente $M_{Rd}$")
        fig_m = go.Figure()
        fig_m.add_trace(go.Scatter(x=t_mc_v, y=mu_res, name="Approach 1 (Standard)", line=dict(color='#e17000', width=3)))
        fig_m.add_trace(go.Scatter(x=t_mc_v, y=mu_cons, name="Approach 2 (Conservative)", line=dict(color='#333', dash='dash')))
        fig_m.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="kNm",
                          xaxis=dict(range=[0, t_ana_mc], showgrid=True, gridcolor='#eee'),
                          yaxis=dict(range=[0, max(mu_res)*1.1], showgrid=True, gridcolor='#eee'))
        st.plotly_chart(fig_m, use_container_width=True)

    with g_c2:
        st.write("### Profundidad de Corrosión $p_x$")
        fig_px = go.Figure()
        fig_px.add_trace(go.Scatter(x=t_mc_v, y=px, fill='tozeroy', name="px", line=dict(color='#8E6713')))
        fig_px.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="mm",
                            xaxis=dict(range=[0, t_ana_mc]))
        st.plotly_chart(fig_px, use_container_width=True)

    # Matriz
    with st.expander("Ver Matriz de Datos Estructurales"):
        df_mc = pd.DataFrame({
            "Tiempo": t_mc_v,
            "Φ Inf Corroido": phi_inf_t,
            "Mu_Res": mu_res,
            "Mu_Cons": mu_cons
        })
        st.dataframe(df_mc)
