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

# --- HEADER ---
# 1. Main Title (Full width)
st.markdown('<p class="title-text">Durability and residual capacity platform</p>', unsafe_allow_html=True)

# 2. Global Inputs Row (Horizontal layout below the title)
# We use a 4-column layout [1, 1, 1, 1] to keep the inputs compact and aligned to the left
head_col1, head_col2, head_col3, head_col4 = st.columns([1, 1, 1, 1])

with head_col1:
    t_global = st.number_input(
        "Study time [years]", 
        value=250, 
        step=1, 
        key="global_time"
    )

with head_col2:
    icorr_val = st.number_input(
        "$I_{corr}$ [$\mu A/cm^2$]", 
        value=0.5, 
        step=0.1, 
        key="global_icorr"
    )

# head_col3 and head_col4 remain empty to prevent the inputs from stretching across the screen

# --- VARIABLES DE SESIÓN ---
if 't_ini_res' not in st.session_state: st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state: st.session_state['tipo_ataque'] = "Carbonatación"
if 'alpha' not in st.session_state: 
    st.session_state['alpha'] = 2.0  # Valor por defecto inicial
# Creamos las 3 pestañas
tab_ini, tab_mc, tab_pret = st.tabs(["Initation period", "Residual strength", "Prestressed"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
with tab_ini:
    attack_type = st.radio("Select analysis phenomenon:", ["Carbonation", "Chlorides"], horizontal=True)
    
    # 1. Guardamos el tipo de ataque para que otras pestañas lo sepan
    st.session_state['attack_type'] = attack_type

    # 2. Lógica para definir alpha automáticamente
    if attack_type == "Carbonation":
        st.session_state['alpha'] = 2.0
    else:
        st.session_state['alpha'] = 10.0

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
# ==========================================
# TAB: MECHANICAL CAPACITY
# ==========================================
# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL (FLEXIÓN)
# ==========================================
with tab_mc:
    # 1. Recuperamos valores de sesión (Tab 1) y Header
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type = st.session_state.get('attack_type', "Carbonation")
    
    st.caption(f"**Initiation:** {t_ini_session:.2f} yrs | **Type:** {atk_type} | **Alpha:** {current_alpha}")

    # --- BLOQUE 1: ENTRADA DE DATOS (Columnas compactas) ---
    c1, c2, c3, c4, c5, c_viz = st.columns([1, 1, 1, 1, 1, 2])

    with c1:
        h_val = st.number_input("$h$ [mm]", value=300, key="h_mc")
        b_val = st.number_input("$b$ [mm]", value=150, key="b_mc")
    
    with c2:
        rec_sup = st.number_input("$c_{top}$ [mm]", value=20, key="rs_mc")
        rec_inf = st.number_input("$c_{bot}$ [mm]", value=20, key="ri_mc")
        
    with c3:
        n_sup = st.number_input("$n_{top}$", value=2, min_value=0, key="ns_mc")
        p_sup = st.number_input("$\Phi_{top}$", value=10, key="ps_mc")

    with c4:
        n_inf = st.number_input("$n_{bot}$", value=2, min_value=0, key="ni_mc")
        phi_inf_0 = st.number_input("$\Phi_{bot}$", value=16, key="pi_mc")

    with c5:
        fyk = st.number_input("$f_{yk}$", value=500, key="fyk_mc")
        fck_val = st.number_input("$f_{ck}$ [MPa]", value=25, key="fck_mc")

    # --- BLOQUE 2: DIBUJO DE LA SECCIÓN (Visualización) ---
    # --- DIBUJO DE LA SECCIÓN (Actualizado con armadura superior) ---
    with c_viz:
        fig_sec = go.Figure()

        # 1. Rectángulo de hormigón
        fig_sec.add_shape(type="rect", x0=0, y0=0, x1=b_val, y1=h_val,
                          line=dict(color="Black", width=2), fillcolor="LightGrey", opacity=0.3)

        # 2. Armadura Superior (Rojo)
        if n_sup > 0:
            # Calculamos espaciado si hay más de una barra
            spacing_s = (b_val - 2*rec_sup) / (n_sup - 1) if n_sup > 1 else 0
            x_s = rec_sup if n_sup > 1 else b_val/2
            for i in range(n_sup):
                fig_sec.add_trace(go.Scatter(
                    x=[x_s + i*spacing_s], 
                    y=[h_val - rec_sup], # Posición arriba: canto total menos recubrimiento
                    mode='markers', 
                    marker=dict(size=p_sup*0.8, color="#FF0000"), # Color rojo
                    showlegend=False,
                    name="Top Rebar"
                ))

        # 3. Armadura Inferior (Verde)
        if n_inf > 0:
            spacing_i = (b_val - 2*rec_inf) / (n_inf - 1) if n_inf > 1 else 0
            x_i = rec_inf if n_inf > 1 else b_val/2
            for i in range(n_inf):
                fig_sec.add_trace(go.Scatter(
                    x=[x_i + i*spacing_i], 
                    y=[rec_inf], # Posición abajo: recubrimiento inferior
                    mode='markers', 
                    marker=dict(size=phi_inf_0*0.8, color="#228B22"), # Color verde
                    showlegend=False,
                    name="Bottom Rebar"
                ))

        # Configuración de ejes para que el dibujo no se deforme
        fig_sec.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False, scaleanchor="x", scaleratio=1,),
            height=180, 
            margin=dict(l=5, r=5, t=5, b=5),
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_sec, use_container_width=True)
    
    # --- BLOQUE 3: CÁLCULOS Y GRÁFICAS ---
    # --- EJECUCIÓN DE CÁLCULOS (Modelcode.py) ---
    # Llamamos a calc_mc que importaste como 'from calculos import Modelcode as calc_mc'
    t_mc, px_mc, phi_inf_mc, mu_std_mc, mu_cons_mc = calc_mc.calcular_capacidad_residual(
        t_global=t_global,
        b_val=b_val,
        h_val=h_val,
        rec_sup=rec_sup,
        rec_inf=rec_inf,
        n_sup=n_sup,
        phi_sup_0=p_sup,      # Usamos p_sup del input
        n_inf=n_inf,
        phi_inf_0=phi_inf_0,  # Usamos phi_inf_0 del input
        fyk=fyk,
        fck=fck_val,
        i_corr=icorr_val,
        current_alpha=current_alpha,
        t_ini=t_ini_session
    )
    # Llamada a la función del modelo Contevect
    t_cv, df_criticos, mu_cv = calc_cv.calcular_contevect(
        t_ana=t_global,
        b_val=b_val,
        h_val=h_val,
        rec_sup=rec_sup,
        rec_inf=rec_inf,
        n_inf=n_inf,
        phi_inf_0=phi_inf_0,
        fyk=fyk,
        fck_val=fck_val,
        i_corr=icorr_val,
        alpha=current_alpha,
        t_ini=t_ini_session
    )

    # Visualización de resultados
    # --- VISUALIZACIÓN DE RESULTADOS ---
    st.subheader("Residual Flexural Capacity Comparison")
    col_graph, col_table = st.columns([2, 1])

    with col_graph:
        fig_res = go.Figure()

        # Graficamos Contevect (Línea Verde Gruesa)
        fig_res.add_trace(go.Scatter(
            x=t_cv, y=mu_cv, 
            name="Contevect Model", 
            line=dict(color="#228B22", width=4)
        ))

        # Graficamos Model Code Standard (Línea Azul Discontinua)
        fig_res.add_trace(go.Scatter(
            x=t_mc, y=mu_std_mc, 
            name="MC Standard", 
            line=dict(color="#1f77b4", width=2, dash="dash")
        ))

        # Graficamos Model Code Conservative (Línea Roja Punteada)
        fig_res.add_trace(go.Scatter(
            x=t_mc, y=mu_cons_mc, 
            name="MC Conservative", 
            line=dict(color="#d62728", width=2, dash="dot")
        ))

        # Añadimos los diamantes del Contevect
        fig_res.add_trace(go.Scatter(
            x=df_criticos["Tiempo"], y=df_criticos["Mu"], 
            mode='markers',
            name='Critical Events (CV)', 
            marker=dict(color='FireBrick', size=10, symbol='diamond'),
            hovertemplate="Time: %{x:.2f} yrs<br>Mu: %{y:.2f} kNm<extra></extra>"
        ))

        fig_res.update_layout(
            xaxis_title="Time [years]", 
            yaxis_title="Moment Capacity [kNm]", 
            hovermode="x unified", 
            template="plotly_white", 
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Línea de tiempo de iniciación para referencia
        fig_res.add_vline(x=t_ini_session, line_dash="dash", line_color="orange", opacity=0.5)

        st.plotly_chart(fig_res, use_container_width=True)

    with col_table:
        st.write("**Key Degradation Steps (Contevect)**")
        st.dataframe(
            df_criticos[["Tiempo", "Px", "Mu"]],
            column_config={
                "Tiempo": st.column_config.NumberColumn("Time [y]", format="%.1f"),
                "Px": st.column_config.NumberColumn("Corr. [mm]", format="%.3f"),
                "Mu": st.column_config.NumberColumn("Mu [kNm]", format="%.2f")
            },
            hide_index=True, 
            use_container_width=True
        )
# ==========================================
# PESTAÑA 3: PRETENSADO (CORTANTE Y TENSIONES)
# ==========================================
with tab_pret:
    # 1. RECUPERACIÓN DE VALORES HEREDADOS (Session State)
    # Si el usuario no ha pasado por la Tab 2, usamos valores por defecto
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type = st.session_state.get('attack_type', "Carbonation")

    st.caption(f"**Heredado:** Iniciación {t_ini_session:.2f} yrs | Tipo: {atk_type}")

    # 2. INPUTS DE LA PESTAÑA (Divididos en 4 columnas para incluir Pretensado)
    # Usamos los valores de las variables de la Tab 2 como 'value' por defecto
    cp1, cp2, cp3, cp4, c_viz_p = st.columns([1, 1, 1, 1, 2])

    with cp1:
        st.markdown("**Geometría**")
        h_p = st.number_input("$h$ [mm]", value=h_val, key="h_pret") # h_val viene de tab_mc
        b_p = st.number_input("$b$ [mm]", value=b_val, key="b_pret")
    
    with cp2:
        st.markdown("**Recubrimientos**")
        rs_p = st.number_input("$c_{top}$ [mm]", value=rec_sup, key="rs_pret")
        ri_p = st.number_input("$c_{bot}$ [mm]", value=rec_inf, key="ri_pret")
        
    with cp3:
        st.markdown("**Armadura Activa**")
        phi_p0 = st.number_input("$\Phi_{p}$ [mm]", value=14.0, key="phi_p_pret")
        n_p = st.number_input("$N_{p}$ cordones", value=2, key="n_p_pret")
        ae_val = st.number_input("$A_e$ (Excent.) [mm]", value=92.0, key="ae_pret")

    with cp4:
        st.markdown("**Materiales P.**")
        fpy = st.number_input("$f_{py}$ [MPa]", value=1860, key="fpy_pret")
        fck_p = st.number_input("$f_{ck}$ [MPa]", value=fck_val, key="fck_pret")

    # --- DIBUJO DE LA SECCIÓN (Heredado y con cable de pretensado) ---
    with c_viz_p:
        fig_sec_p = go.Figure()
        # Hormigón
        fig_sec_p.add_shape(type="rect", x0=0, y0=0, x1=b_p, y1=h_p,
                          line=dict(color="Black", width=2), fillcolor="LightGrey", opacity=0.3)
        
        # Dibujar cable de pretensado (Punto naranja grande en la excentricidad Ae)
        # Nota: La posición Y suele ser h/2 - Ae o similar según convenio
        y_pret = (h_p / 2) - ae_val
        fig_sec_p.add_trace(go.Scatter(x=[b_p/2], y=[y_pret],
                    mode='markers+text', 
                    marker=dict(size=phi_p0*1.2, color="#FF8C00", symbol="diamond"), 
                    name="Prestressing", text=["Prestressing Cable"], textposition="top center", showlegend=False))

        # Dibujar también armadura pasiva heredada (pequeña, para referencia)
        if n_inf > 0:
            spacing_i = (b_p - 2*ri_p) / (n_inf - 1) if n_inf > 1 else 0
            for i in range(n_inf):
                fig_sec_p.add_trace(go.Scatter(x=[ri_p + i*spacing_i], y=[ri_p],
                    mode='markers', marker=dict(size=phi_inf_0*0.5, color="#228B22", opacity=0.4), showlegend=False))

        fig_sec_p.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                              height=220, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec_p, use_container_width=True)

    st.divider()

    # 3. PREPARACIÓN DE PARÁMETROS PARA CÁLCULOS ESPECÍFICOS
    # Creamos el diccionario que tus funciones de Cortante y Pretensado necesitan
    params_pret = {
        't_global': t_global,
        't_ini': t_ini_session,
        'h': h_p, 
        'bw': b_p, 
        'rec_inf': ri_p,
        'phi_inf_0': phi_inf_0, 
        'n_inf': n_inf,
        'Ae': ae_val, 
        'dg': 25.0, # Valor por defecto para árido
        'fck': fck_p, 
        'Es': 200000, # MPa
        'fpy': fpy, 
        'phi_p0': phi_p0, 
        'n_p': n_p,
        'Med': 0.0, # Solicitación por defecto
        'Ved': 30.0, 
        'icorr': icorr_val, 
        'alpha': current_alpha
    }

    # 4. LLAMADA A FUNCIONES DE CÁLCULO
    # (Asegúrate de que calc_cor y calc_pre acepten el diccionario params_pret)
    res_cortante = calc_cor.calcular_degradacion_cortante(params_pret)
    df_v = pd.DataFrame(res_cortante)

    res_tensiones = calc_pre.calcular_tensiones_pretensado(params_pret)
    df_t = pd.DataFrame(res_tensiones)

    # 5. GRÁFICAS DE RESULTADOS
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("### $V_{rd,c}$ - Shear Capacity Decay")
        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(x=df_v['t'], y=df_v['vrdc'], name="Shear Capacity", line=dict(color='red', width=3)))
        fig_v.add_vline(x=t_ini_session, line_dash="dash", line_color="orange")
        fig_v.update_layout(plot_bgcolor='white', xaxis_title="Time [years]", yaxis_title="Vrd,c [kN]", height=350)
        st.plotly_chart(fig_v, use_container_width=True)

    with col_g2:
        st.markdown("### Concrete Stresses (Top vs Bottom)")
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_inferior'], name="$\sigma$ Bottom", line=dict(color='#005293')))
        fig_t.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_superior'], name="$\sigma$ Top", line=dict(color='#A60628')))
        fig_t.update_layout(plot_bgcolor='white', xaxis_title="Time [years]", yaxis_title="Stress [MPa]", height=350)
        st.plotly_chart(fig_t, use_container_width=True)
