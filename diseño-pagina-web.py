import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from calculos import tiempoiniciacion as calc_ini
from calculos import diagrama_momento_curvatura as calc_mc
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
    st.markdown('<p class="title-text">Plataforma de Durabilidad y Capacidad Residual</p>', unsafe_allow_html=True)
with head_col2:
    t_global = st.number_input("Tiempo de estudio total [años]", value=100, step=1, key="global_time")

# --- VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state: st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state: st.session_state['tipo_ataque'] = "Carbonatación"

# Creamos las 3 pestañas (Añadida la de Pretensado/Cortante)
tab_ini, tab_mc, tab_pret = st.tabs([" Tiempo de Iniciación", " Capacidad Estructural", " Pretensado"])

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
    with res2:
        fig_ini = go.Figure()
        fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', line=dict(color='#e17000', width=3), name="Avance"))
        fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), line=dict(color='black', dash='dash'), name="Límite"))
        fig_ini.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title=y_label)
        st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL (FLEXIÓN)
# ==========================================
# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL (FLEXIÓN)
# ==========================================

with tab_mc:
    # 1. Recuperación de variables de sesión y parámetros de ataque
    t_ini = st.session_state['t_ini_res']
    atk_type = st.session_state['tipo_ataque']
    alpha_v = 2.0 if atk_type == "Carbonatación" else 10.0

    st.subheader("Geometría y Parámetros de Flexión")
    st.info(f"Fase de Iniciación actual: **{t_ini:.2f} años**")

    # 2. Columnas de Inputs
    c1, c2, c3 = st.columns(3)
    with c1: 
        h_val = st.number_input("Canto h [mm]", value=150, key="h_mc") # Ajustado a tus valores de prueba
        b_val = st.number_input("Ancho b [mm]", value=300, key="b_mc")
        icorr_val = st.number_input("Intensidad $i_{corr}$", value=0.5, key="icorr_mc")
    with c2: 
        rec_sup = st.number_input("Recubrimiento Sup. [mm]", value=50)
        rec_inf = st.number_input("Recubrimiento Inf. [mm]", value=50)
        fyk = st.number_input("fyk [MPa]", value=500)
    with c3: 
        fck_val = st.number_input("fck [MPa]", value=25, key="fck_mc")
        n_inf = st.number_input("Nº barras inf.", value=2)
        phi_inf_0 = st.number_input("Φ barras inf. [mm]", value=15)

    # Variables adicionales para el diagrama M-Chi
    Ec = 25000
    fct = 3.1
    esy = 0.0021
    ecy = 0.0035
    Es = 200000

    # --- EJECUCIÓN DE CÁLCULOS ---
    
    # A. Model Code y Diagramas M-Chi Evolutivos
    # Llamamos a tu nueva función que devuelve el diccionario de matrices
    dict_mchi = calc_mchi.calcular_capacidad_y_diagramas(
        t_global, b_val, h_val, rec_sup, rec_inf, 2, 15, n_inf, phi_inf_0, 
        fyk, fck_val, icorr_val, alpha_v, t_ini, Ec, fct, ecy, esy, Es
    )
    
    # Extraemos m_res (Mrd) para la gráfica temporal de la columna correspondiente
    t_v = np.array(list(dict_mchi.keys()))
    m_res = np.array([dict_mchi[t][5, 0] for t in t_v]) # El Mrd es el Punto 4 (fila 5)
    
    # B. Contevect (Mantenemos tu lógica anterior)
    t_cv, df_crit, m_vect = calc_cv.calcular_contevect(
        t_global, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0, fyk, fck_val, icorr_val, alpha_v, t_ini
    )

    # Correcciones para gráficas temporales
    m_max_ref = m_vect[0] 
    m_vect_plot = np.where(t_cv < t_ini, m_max_ref, m_vect)
    m_res_plot = np.where(t_v < t_ini, m_max_ref, m_res)

    st.divider()
    
    # --- VISUALIZACIÓN 1: Mrd vs TIEMPO ---
    st.write("### Comparativa: Momento Resistente vs Tiempo")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(x=t_cv, y=m_vect_plot, name="Contevect", line=dict(color='#005293', width=3)))
    fig_comp.add_trace(go.Scatter(x=t_v, y=m_res_plot, name="Model Code", line=dict(color='#e17000', width=2)))
    
    fig_comp.update_layout(xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]", hovermode="x unified", plot_bgcolor='white')
    st.plotly_chart(fig_comp, use_container_width=True)

    st.divider()

    # --- VISUALIZACIÓN 2: DIAGRAMA MOMENTO-CURVATURA ---
    st.write("### Diagrama Momento-Curvatura (M-χ)")
    st.write("Selecciona un año para ver el estado de la sección:")
    
    # Slider para elegir el tiempo a visualizar
    t_seleccionado = st.select_slider(
        "Año de análisis", 
        options=sorted(list(dict_mchi.keys())),
        value=0.0
    )

    # Obtenemos la matriz [M, Chi] para ese año
    matriz_mchi = dict_mchi[t_seleccionado]

    fig_mchi = go.Figure()
    
    # Dibujamos el diagrama (Curvatura en X, Momento en Y)
    fig_mchi.add_trace(go.Scatter(
        x=matriz_mchi[:, 1], 
        y=matriz_mchi[:, 0],
        mode='lines+markers',
        name=f"Año {t_seleccionado}",
        line=dict(color='firebrick', width=3),
        marker=dict(size=8)
    ))

    # Anotaciones de los puntos clave
    puntos_nombres = ["Origen", "Fisuración (Bruta)", "Fisuración (Fisurada)", "Fluencia", "Post-Plastificación", "Agotamiento (Mrd)"]
    for j, nombre in enumerate(puntos_nombres):
        fig_mchi.add_annotation(
            x=matriz_mchi[j, 1], y=matriz_mchi[j, 0],
            text=nombre, showarrow=True, arrowhead=1, ax=40, ay=-20
        )

    fig_mchi.update_layout(
        title=f"Estado de la sección al año {t_seleccionado}",
        xaxis_title="Curvatura χ [1/m]",
        yaxis_title="Momento M [kNm]",
        plot_bgcolor='white',
        xaxis=dict(gridcolor='#f5f5f5'),
        yaxis=dict(gridcolor='#f5f5f5')
    )

    st.plotly_chart(fig_mchi, use_container_width=True)

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
