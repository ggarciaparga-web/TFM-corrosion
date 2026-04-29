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
    h1 { color: #000000; font-weight: 700; border-bottom: 2px solid #e17000; padding-bottom: 10px; margin-bottom: 20px;}
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

st.title("Plataforma de Durabilidad y Capacidad Residual")

# --- INICIALIZACIÓN DE SESSION STATE ---
if 't_ini_res' not in st.session_state:
    st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state:
    st.session_state['tipo_ataque'] = "Carbonatación"

# --- CREACIÓN DE PESTAÑAS ---
tab_ini, tab_mc = st.tabs(["Tiempo de Iniciación", " Model Code (Capacidad Residual)"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
with tab_ini:
    tipo_ataque = st.radio("Seleccione el fenómeno a analizar:", ["Carbonatación", "Cloruros"], horizontal=True)
    st.session_state['tipo_ataque'] = tipo_ataque

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
        
        # Parámetros fijos según tu descripción inicial
        kcd, kt, ge, fe, bw, t0 = 0.67, 1.25, 2.5, 5.0, 0.446, 0.0767
        t_i, w_i, xcd, t_ini_calc = calc_ini.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_ana)
        y_plot = xcd
        y_label = "Profundidad [mm]"
        limit = d_mm
    
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
        
        t_i, dapp, z, conc, t_ini_calc = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, 4800, tref, treal, 1.0, 0.0767, a_age, dcrm, t_ana)
        y_plot = conc
        y_label = "Concentración [%]"
        limit = ccrit

    # Guardamos el t_ini calculado para la segunda pestaña
    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2])
    with res1:
        st.write("### Resultados")
        if t_ini_calc:
            st.metric("Tiempo de Iniciación", f"{t_ini_calc:.2f} años")
        else:
            st.error(f"No se alcanza el umbral en {t_ana} años.")
        st.dataframe(pd.DataFrame({"Año": t_i, y_label: y_plot}).head(50))
    
    with res2:
        fig_ini = go.Figure()
        fig_ini.add_trace(go.Scatter(x=t_i, y=y_plot, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t_i, y=[limit]*len(t_i), line=dict(color='black', dash='dash'), name="Límite"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title=y_label, title=f"Evolución de {tipo_ataque}")
        st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: MODEL CODE
# ==========================================
with tab_mc:
    t_ini_prev = st.session_state['t_ini_res']
    tipo_atk = st.session_state['tipo_ataque']
    alpha_v = 2.0 if tipo_atk == "Carbonatación" else 10.0
    px_limit = 0.05 if tipo_atk == "Carbonatación" else 0.5 # mm (50 y 500 micras)

    st.subheader("Geometría y Parámetros Estructurales")
    st.info(f"Análisis basado en $t_{{ini}}$ = **{t_ini_prev:.2f} años** | Alpha = **{alpha_v}** | Límite $p_x$ = **{px_limit} mm**")

    c1, c2, c3 = st.columns(3)
    with c1:
        h = st.number_input("Canto h [mm]", value=300)
        b = st.number_input("Ancho b [mm]", value=150)
        rec_sup = st.number_input("Recubrimiento Sup. [mm]", value=20)
        rec_inf = st.number_input("Recubrimiento Inf. [mm]", value=20)
        t_ana_mc = st.number_input("Tiempo análisis estructural [años]", value=100)
    with c2:
        fck = st.number_input("fck [MPa]", value=25)
        fyk = st.number_input("fyk [MPa]", value=500)
    with c3:
        icorr = st.number_input("Intensidad corrosión $i_{corr}$", value=0.5)
        n_sup=st.number_input("Nº barras sup.",value=2)
        phi_sup_0 = st.number_input("Φ barras sup. [mm]", value=16)
        n_inf = st.number_input("Nº barras inf.", value=2)
        phi_inf_0 = st.number_input("Φ barras inf. [mm]", value=16)

    # Cálculo (sección superior fija según descripción anterior)
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(
        t_ana_mc, b, h, rec_sup, rec_inf, 2, 16, n_inf, phi_inf_0, 
        fyk, fck, icorr, alpha_v, t_ini_prev
    )

    # Tiempo final normativo
    idx_lim = np.where(px_v >= px_limit)[0]
    t_final_norma = t_v[idx_lim[0]] if len(idx_lim) > 0 else None

    st.divider()
    g1, g2 = st.columns(2)

    with g1:
        st.write("### Momento Resistente vs Tiempo")
        fig_m_t = go.Figure()
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_res, name="Approach 1", line=dict(color='#e17000', width=3)))
        fig_m_t.add_trace(go.Scatter(x=t_v, y=m_cons, name="Approach 2 (Cons.)", line=dict(color='#333', dash='dash')))
        if t_final_norma:
            fig_m_t.add_vline(x=t_final_norma, line_dash="dot", line_color="red", annotation_text="Límite ELS")
        fig_m_t.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]",
                            xaxis=dict(range=[0, t_ana_mc]), yaxis=dict(range=[0, max(m_res)*1.1]))
        st.plotly_chart(fig_m_t, use_container_width=True)

    with g2:
        st.write("### Momento Resistente vs Profundidad $p_x$")
        fig_m_px = go.Figure()
        fig_m_px.add_trace(go.Scatter(x=px_v, y=m_res, name="Mrd vs px", line=dict(color='#8E6713', width=3)))
        fig_m_px.add_vline(x=px_limit, line_dash="dash", line_color="red", annotation_text=f"{px_limit}mm")
        fig_m_px.update_layout(plot_bgcolor='white', xaxis_title="px [mm]", yaxis_title="Mrd [kNm]",
                             xaxis=dict(range=[0, max(px_v)*1.1 if len(px_v)>0 else 1]), 
                             yaxis=dict(range=[0, max(m_res)*1.1]))
        st.plotly_chart(fig_m_px, use_container_width=True)

    if t_final_norma:
        st.success(f"**Vida Útil Normativa (p_x = {px_limit} mm):** Alcanzada a los {t_final_norma:.2f} años.")
    
    with st.expander("Ver Matriz de Resultados"):
        st.dataframe(pd.DataFrame({"Año": t_v, "px [mm]": px_v, "Mrd [kNm]": m_res}))
