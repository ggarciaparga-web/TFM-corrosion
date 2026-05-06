import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc
from calculos import Contevect as calc_cv
from calculos import Cortante as calc_cor  
from calculos import pretensado as calc_pre

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
    st.markdown('<p class="title-text">Durability and residual capacity platform</p>', unsafe_allow_html=True)
with head_col2:
    t_global = st.number_input("Study time [years]", value=250, step=1, key="global_time")

# --- VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state: st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state: st.session_state['tipo_ataque'] = "Carbonatación"

# Creamos las 3 pestañas
tab_ini, tab_mc, tab_pret = st.tabs(["Initation period", "Residual strength", "Prestressed"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
# ==========================================
# TAB 1: INITIATION TIME
# ==========================================
with tab_ini:
    # Radio for phenomenon selection
    attack_type = st.radio("Select analysis phenomenon:", ["Carbonation", "Chlorides"], horizontal=True)
    st.session_state['tipo_ataque'] = attack_type

    # 5 columns with custom widths for a condensed layout
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.5, 1.2])

    with c1:
        d_mm = st.number_input("Cover $c$ [mm]", value=30.0, help="Concrete cover thickness")

    if attack_type == "Carbonation":
        with c2: 
            rh_real = st.number_input("$RH_{real}$ [%]", 0, 100, 50)
            hre = st.number_input("$H_{re}$ [%]", value=65.0)
        
        with c3: 
            rain_days = st.number_input("Rain [d/y]", value=50)
            psr = st.number_input("$P_{sr}$ [-]", value=0.0)
        
        with c4: 
            racc = st.number_input("$R_{acc}$ [$mm^2/y / kg/m^3$]", value=4541.32)
            csd = st.number_input("$C_{s,d}$ [kg/m³]", value=0.00082, format="%.5f")
        
        with c5:
            kcd = st.number_input("$k_{cd}$ [-]", value=0.67)
            kt = st.number_input("$k_{t}$ [-]", value=1.0)

        with st.expander("Additional Calibration Parameters"):
            ca1, ca2, ca3, ca4 = st.columns(4)
            with ca1: ge = st.number_input("$g_{e}$ [-]", value=2.5)
            with ca2: fe = st.number_input("$f_{e}$ [-]", value=5.0)
            with ca3: bw = st.number_input("$b_{w}$ [-]", value=0.446)
            with ca4: t0 = st.number_input("$t_{0}$ [-]", value=0.0767)

        # Function call (Variable names kept for logic, labels changed for user)
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(
            d_mm, rh_real, hre, ge, fe, kcd, kt, csd, racc, psr, rain_days, bw, t0, t_global
        )
        y_label, limit_val = "Carbonation Depth [mm]", d_mm

    else:  # CHLORIDES SECTION
        with c2: 
            c0 = st.number_input("$C_{0}$ [%]", value=0.1)
            cs = st.number_input("$C_{s}$ [%]", value=4.0)
        with c3:
            ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
            treal = st.number_input("$T_{real}$ [K]", value=289.6)
        with c4: 
            tref = st.number_input("$T_{ref}$ [K]", value=293.0)
            dcrm = st.number_input("$D_{rcm}$ [$m^2/s$]", value=1.95e-12, format="%.2e")
        with c5:
            a_age = st.number_input("$a$ (ageing) [-]", value=0.4902)
            b_cl = st.number_input("$b_{cl}$ [K]", value=4800.0)

        ke, t0_cl = 1.0, 0.0767
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(
            d_mm, c0, cs, ccrit, b_cl, tref, treal, ke, t0_cl, a_age, dcrm, t_global
        )
        y_label, limit_val = "Concentration [%]", ccrit

    # --- Common Results Section ---
    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2.5])
    
    with res1:
        if t_ini_calc and t_ini_calc > 0: 
            st.metric("Initiation Time", f"{t_ini_calc:.2f} years")
        else: 
            st.warning("No initiation detected")
            
    with res2:
        if t_i is not None:
            fig_ini = go.Figure()
            fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', 
                                         line=dict(color='#e17000', width=3), name="Progress"))
            fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), 
                                         line=dict(color='black', dash='dash'), name="Limit"))
            fig_ini.update_layout(
                height=280,
                plot_bgcolor='white', 
                xaxis_title="Time [years]", 
                yaxis_title=y_label,
                margin=dict(l=0, r=0, t=10, b=0)
            )
            st.plotly_chart(fig_ini, use_container_width=True)
# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL (FLEXIÓN)
# ==========================================

with tab_mc:
    # 1. Recuperación de variables de sesión y parámetros de ataque
    t_ini = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0

    st.subheader("Geometría y Parámetros de Flexión")
    st.info(f"Fase de Iniciación actual: **{t_ini:.2f} años** (Periodo de resistencia máxima constante)")

    # 2. Columnas de Inputs
    c1, c2, c3 = st.columns(3)
    with c1: 
        h_val = st.number_input("Canto h [mm]", value=300, key="h_mc")
        b_val = st.number_input("Ancho b [mm]", value=150, key="b_mc")
        icorr_val = st.number_input("Intensidad $i_{corr}$", value=0.5, key="icorr_mc")
    with c2: 
        rec_sup = st.number_input("Recubrimiento Sup. [mm]", value=20)
        rec_inf = st.number_input("Recubrimiento Inf. [mm]", value=20)
        fyk = st.number_input("fyk [MPa]", value=500)
    with c3: 
        fck_val = st.number_input("fck [MPa]", value=25, key="fck_mc")
        n_inf = st.number_input("Nº barras inf.", value=2)
        phi_inf_0 = st.number_input("Φ barras inf. [mm]", value=16)

    # --- EJECUCIÓN DE CÁLCULOS ---
    
    # A. Model Code (Approach 1)
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(
        t_global, b_val, h_val, rec_sup, rec_inf, 2, 16, n_inf, phi_inf_0, fyk, fck_val, icorr_val, alpha_v, t_ini
    )
    
    # B. Contevect (Degradación geométrica con puntos críticos)
    t_cv, df_crit, m_vect = calc_cv.calcular_contevect(
        t_global, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0, fyk, fck_val, icorr_val, alpha_v, t_ini
    )

    # --- CORRECCIÓN ESTRATÉGICA DE LA GRÁFICA ---
    # Obtenemos el valor de capacidad máxima al inicio (t=0 o t=t_ini)
    m_max_ref = m_vect[0] 

    # Forzamos que Contevect sea constante hasta t_ini
    m_vect_plot = np.where(t_cv < t_ini, m_max_ref, m_vect)
    
    # Forzamos que Model Code sea constante hasta t_ini
    m_res_plot = np.where(t_v < t_ini, m_max_ref, m_res)

    st.divider()
    
    # --- VISUALIZACIÓN CON PLOTLY ---
    st.write("### Comparativa: Momento Resistente vs Tiempo")
    
    fig_comp = go.Figure()

    # Curva Contevect (Línea Azul Gruesa)
    fig_comp.add_trace(go.Scatter(
        x=t_cv, y=m_vect_plot, 
        name="Contevect (Degradación Geométrica)", 
        line=dict(color='#005293', width=3)
    ))

    # Curva Model Code (Línea Naranja Punteada para diferenciar)
    fig_comp.add_trace(go.Scatter(
        x=t_v, y=m_res_plot, 
        name="Model Code (Sección Constante)", 
        line=dict(color='#e17000', width=2, dash='solid')
    ))

    # Eventos Críticos (Diamantes rojos)
    # Filtramos para que solo muestre puntos a partir de t_ini
    df_puntos_vis = df_crit[df_crit["Tiempo"] >= t_ini - 0.1]
    
    fig_comp.add_trace(go.Scatter(
        x=df_puntos_vis["Tiempo"], y=df_puntos_vis["Mu"], 
        mode='markers',
        marker=dict(color='red', size=11, symbol='diamond', line=dict(width=1, color='black')),
        name="Eventos Críticos (Puntos de quiebre)"
    ))

    # Línea de Iniciación (Referencia Vertical)
    fig_comp.add_vline(
        x=t_ini, line_width=2, line_dash="dot", line_color="green", 
        annotation_text="FIN INICIACIÓN", annotation_position="top left"
    )

    # Ajustes finales del Layout
    fig_comp.update_layout(
        plot_bgcolor='white',
        xaxis_title="Tiempo [años]",
        yaxis_title="Mrd [kNm]",
        xaxis=dict(range=[0, t_global], gridcolor='#f5f5f5'),
        yaxis=dict(range=[0, m_max_ref * 1.15], gridcolor='#f5f5f5'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    st.plotly_chart(fig_comp, use_container_width=True)

    

# ==========================================
# PESTAÑA 3: PRETENSADO (CORTANTE)
# ==========================================
# ==========================================
# PESTAÑA 3: PRETENSADO (CORTANTE Y TENSIONES)
# ==========================================
with tab_pret:
    t_ini = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0

    st.subheader("Configuración de Pretensado y Cortante")
    st.info(f"Fase de Iniciación actual: **{t_ini:.2f} años**")

    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.markdown("**Armadura Activa**")
        phi_p0 = st.number_input("Φ cordones [mm]", value=14.0, key="phi_p0_p3")
        n_p = st.number_input("Nº cordones", value=2, key="n_p_p3")
        fpy = st.number_input("fpy [MPa]", value=1860, key="fpy_p3")
        ae_val = st.number_input("Excentricidad Ae [mm]", value=92.0, key="ae_p3")
    
    with col_p2:
        st.markdown("**Solicitaciones**")
        med_val = st.number_input("Med [kN·m]", value=0.0, key="med_p3") * 1e6
        ved_val = st.number_input("Ved [kN]", value=30.0, key="ved_p3") * 1e3
        dg_val = st.number_input("Tamaño árido $d_g$ [mm]", value=28.0, key="dg_p3")
    
    with col_p3:
        st.markdown("**Materiales**")
        es_val = st.number_input("Es (Acero) [MPa]", value=200000, key="es_p3")
        icorr_p = st.number_input("Intensidad $i_{corr}$ (pret)", value=2.0, key="icorr_p3")

    # Diccionario de parámetros (Asegúrate de que h_val, b_val, etc. vienen de la Tab 2)
    params_pret = {
        't_global': t_global,
        't_ini': t_ini,
        'h': h_val, 
        'bw': b_val, 
        'rec_inf': rec_inf,
        'phi_inf_0': phi_inf_0, 
        'n_inf': n_inf,
        'Ae': ae_val, 
        'dg': dg_val, 
        'fck': fck_val, 
        'Es': es_val,
        'fpy': fpy, 
        'phi_p0': phi_p0, 
        'n_p': n_p,
        'Med': med_val, 
        'Ved': ved_val,
        'icorr': icorr_p, 
        'alpha': alpha_v
    }

    # --- CÁLCULOS ---
    res_cortante = calc_cor.calcular_degradacion_cortante(params_pret)
    df_v = pd.DataFrame(res_cortante)

    res_tensiones = calc_pre.calcular_tensiones_pretensado(params_pret)
    df_t = pd.DataFrame(res_tensiones)

    st.divider()
    
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### Resistencia a Cortante")
        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(x=df_v['t'], y=df_v['vrdc'], name="Vrd,c", line=dict(color='red', width=3)))
        fig_v.add_vline(x=t_ini, line_dash="dash", line_color="green")
        
        # ELIMINADO 'bottom=0' que causaba el error y reemplazado por rangemode
        fig_v.update_layout(
            plot_bgcolor='white',
            xaxis_title="Tiempo [años]",
            yaxis_title="Vrd,c [kN]",
            xaxis=dict(range=[0, t_global], gridcolor='#eeeeee'),
            yaxis=dict(rangemode='tozero', gridcolor='#eeeeee'),
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig_v, use_container_width=True)

    with col_g2:
        st.markdown("### Tensiones en el Hormigón")
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_inferior'], name="σ Inf", line=dict(color='#005293', width=3)))
        fig_t.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_superior'], name="σ Sup", line=dict(color='#A60628', width=3)))
        fig_t.add_vline(x=t_ini, line_dash="dash", line_color="green")
        
        fig_t.update_layout(
            plot_bgcolor='white',
            xaxis_title="Tiempo [años]",
            yaxis_title="Tensión [MPa]",
            xaxis=dict(range=[0, t_global], gridcolor='#eeeeee'),
            yaxis=dict(gridcolor='#eeeeee'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_t, use_container_width=True)
