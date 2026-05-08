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
st.markdown('<p class="title-text">Durability and residual capacity platform</p>', unsafe_allow_html=True)

head_col1, head_col2, head_col3, head_col4 = st.columns([1, 1, 1, 1])

with head_col1:
    t_global = st.number_input("Study time [years]", value=250, step=1, key="global_time")

with head_col2:
    icorr_val = st.number_input("$I_{corr}$ [$\mu A/cm^2$]", value=0.5, step=0.1, key="global_icorr")

if 't_ini_res' not in st.session_state: st.session_state['t_ini_res'] = 0.0
if 'tipo_ataque' not in st.session_state: st.session_state['tipo_ataque'] = "Carbonatación"
if 'alpha' not in st.session_state: st.session_state['alpha'] = 2.0 

tab_ini, tab_mc, tab_pret = st.tabs(["Initation period", "Residual strength", "Prestressed"])

# ==========================================
# PESTAÑA 1: TIEMPO DE INICIACIÓN
# ==========================================
with tab_ini:
    attack_type = st.radio("Select analysis phenomenon:", ["Carbonation", "Chlorides"], horizontal=True)
    st.session_state['attack_type'] = attack_type

    if attack_type == "Carbonation":
        st.session_state['alpha'] = 2.0
    else:
        st.session_state['alpha'] = 10.0

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
            with ca3: bw_ini = st.number_input("$b_{w}$ [-]", value=0.446)
            with ca4: t0_ini = st.number_input("$t_{0}$ [-]", value=0.0767)
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(d_mm, rh_real, hre, ge, fe, kcd, kt, csd, racc, psr, rain_days, bw_ini, t0_ini, t_global)
        y_label, limit_val = "Carbonation Depth [mm]", d_mm
    else:
        with c2: 
            c0 = st.number_input("$C_{0}$ [%]", value=0.1)
            cs = st.number_input("$C_{s}$ [%]", value=4.0)
        with c3:
            ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
            treal = st.number_input("$T_{real}$ [K]", value=289.6)
        with c4: 
            tref = st.number_input("$T_{ref}$ [K]", value=293.0)
            dcrm = st.number_input("$D_{app} 10**-12$ [$m^2/s$]", value=1.95, format="%.2e")
        with c5:
            a_age = st.number_input("$a$ (ageing) [-]", value=0.4902)
            b_cl = st.number_input("$b_{cl}$ [K]", value=4800.0)
        ke, t0_cl = 1.0, 0.0767
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(d_mm, c0, cs, ccrit, b_cl, tref, treal, ke, t0_cl, a_age, dcrm, t_global)
        y_label, limit_val = "Concentration [%]", ccrit

    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc is not None else 0.0

    st.divider()
    res1, res2 = st.columns([1, 2.5])
    with res1:
        if t_ini_calc and t_ini_calc > 0: st.metric("Initiation Time", f"{t_ini_calc:.2f} years")
        else: st.warning("No initiation detected")
    with res2:
        if t_i is not None:
            fig_ini = go.Figure()
            fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill='tozeroy', line=dict(color='#e17000', width=3), name="Progress"))
            fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i), line=dict(color='black', dash='dash'), name="Limit"))
            fig_ini.update_layout(height=280, plot_bgcolor='white', xaxis_title="Time [years]", yaxis_title=y_label, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_ini, use_container_width=True)

# ==========================================
# PESTAÑA 2: CAPACIDAD ESTRUCTURAL (FLEXIÓN)
# ==========================================
with tab_mc:
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type = st.session_state.get('attack_type', "Carbonation")
    st.caption(f"**Initiation:** {t_ini_session:.2f} yrs | **Type:** {atk_type} | **Alpha:** {current_alpha}")

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

    with c_viz:
        fig_sec = go.Figure()
        fig_sec.add_shape(type="rect", x0=0, y0=0, x1=b_val, y1=h_val, line=dict(color="Black", width=2), fillcolor="LightGrey", opacity=0.3)
        if n_sup > 0:
            spacing_s = (b_val - 2*rec_sup) / (n_sup - 1) if n_sup > 1 else 0
            x_s = rec_sup if n_sup > 1 else b_val/2
            for i in range(n_sup): fig_sec.add_trace(go.Scatter(x=[x_s + i*spacing_s], y=[h_val - rec_sup], mode='markers', marker=dict(size=p_sup*0.8, color="#FF0000"), showlegend=False))
        if n_inf > 0:
            spacing_i = (b_val - 2*rec_inf) / (n_inf - 1) if n_inf > 1 else 0
            x_i = rec_inf if n_inf > 1 else b_val/2
            for i in range(n_inf): fig_sec.add_trace(go.Scatter(x=[x_i + i*spacing_i], y=[rec_inf], mode='markers', marker=dict(size=phi_inf_0*0.8, color="#228B22"), showlegend=False))
        fig_sec.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1,), height=180, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec, use_container_width=True)

    st.divider()

    t_mc, px_mc, phi_inf_mc, mu_std_mc, mu_cons_mc = calc_mc.calcular_capacidad_residual(t_global, b_val, h_val, rec_sup, rec_inf, n_sup, p_sup, n_inf, phi_inf_0, fyk, fck_val, icorr_val, current_alpha, t_ini_session)
    t_cv, df_criticos, mu_cv = calc_cv.calcular_contevect(t_global, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0, fyk, fck_val, icorr_val, current_alpha, t_ini_session)

    # --- LÓGICA RECTAS FIN DE VIDA ÚTIL ---
    umbral_px = 0.05 if atk_type == "Carbonation" else 0.5
    idx_life = np.where(px_mc >= umbral_px)[0]
    t_life = t_mc[idx_life[0]] if len(idx_life) > 0 else None

    st.subheader("Residual Flexural Capacity Comparison")
    col_graph, col_table = st.columns([2, 1])

    with col_graph:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=t_cv, y=mu_cv, name="Contevect Model", line=dict(color="#228B22", width=4)))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_std_mc, name="MC Standard", line=dict(color="#1f77b4", width=2, dash="dash")))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_cons_mc, name="MC Conservative", line=dict(color="#d62728", width=2, dash="dot")))
        fig_res.add_trace(go.Scatter(x=df_criticos["Tiempo"], y=df_criticos["Mu"], mode='markers', name='Critical Events (CV)', marker=dict(color='FireBrick', size=10, symbol='diamond')))
        
        fig_res.add_vline(x=t_ini_session, line_dash="dash", line_color="orange", opacity=0.7, annotation_text="Start")
        if t_life: fig_res.add_vline(x=t_life, line_dash="dot", line_color="red", annotation_text=f"End of Life ({umbral_px}mm)")

        fig_res.update_layout(xaxis_title="Time [years]", yaxis_title="Moment Capacity [kNm]", hovermode="x unified", template="plotly_white", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_res, use_container_width=True)

    with col_table:
        st.write("**Key Degradation Steps (Contevect)**")
        st.dataframe(df_criticos[["Tiempo", "Px", "Mu"]], column_config={"Tiempo": st.column_config.NumberColumn("Time [y]", format="%.1f"), "Px": st.column_config.NumberColumn("Corr. [mm]", format="%.3f"), "Mu": st.column_config.NumberColumn("Mu [kNm]", format="%.2f")}, hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 3: PRETENSADO (CORTANTE Y TENSIONES)
# ==========================================
with tab_pret:
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type = st.session_state.get('attack_type', "Carbonation")
    st.caption(f"**Initiation:** {t_ini_session:.2f} yrs | **Type:** {atk_type}")

    c1, c2, c3, c4, c5, c6, c_viz = st.columns([1, 1, 1, 1, 1, 1, 2.5])
    with c1:
        h_p = st.number_input("$h$ [mm]", value=h_val, key="h_p3")
        b_p = st.number_input("$b$ [mm]", value=b_val, key="b_p3")
    with c2:
        rs_p = st.number_input("$c_{top}$ [mm]", value=rec_sup, key="rs_p3")
        ri_p = st.number_input("$c_{bot}$ [mm]", value=rec_inf, key="ri_p3")
    with c3:
        nt_p = st.number_input("$n_{top}$", value=n_sup, key="nt_p3")
        pt_p = st.number_input("$\Phi_{top}$", value=p_sup, key="pt_p3")
    with c4:
        np_p = st.number_input("$n_{bot}$ (Torones)", value=2, key="np_p3")
        phi_p_val = st.number_input("$\Phi_{p}$ [mm]", value=14.0, key="phip_p3")
    with c5:
        ae_p3_val = st.number_input("$A_e$ [mm]", value=92.0, key="ae_p3_key")
        fpy_p3_val = st.number_input("$f_{py}$ [MPa]", value=1860, key="fpy_p3_key")
    with c6:
        fyk_p = st.number_input("$f_{yk}$", value=fyk, key="fyk_p3")
        fck_p = st.number_input("$f_{ck}$ [MPa]", value=fck_val, key="fck_p3")

    with c_viz:
        fig_sec_p = go.Figure()
        fig_sec_p.add_shape(type="rect", x0=0, y0=0, x1=b_p, y1=h_p, line=dict(color="Black", width=2), fillcolor="LightGrey", opacity=0.3)
        if nt_p > 0:
            spacing_s = (b_p - 2*rs_p) / (nt_p - 1) if nt_p > 1 else 0
            x_s = rs_p if nt_p > 1 else b_p/2
            for i in range(nt_p): fig_sec_p.add_trace(go.Scatter(x=[x_s + i*spacing_s], y=[h_p - rs_p], mode='markers', marker=dict(size=pt_p*0.8, color="#FF0000"), showlegend=False))
        y_pretensado = (h_p / 2) - ae_p3_val
        if np_p > 0:
            spacing_p = (b_p - 2*ri_p) / (np_p - 1) if np_p > 1 else 0
            x_p = ri_p if np_p > 1 else b_p/2
            for i in range(np_p): fig_sec_p.add_trace(go.Scatter(x=[x_p + i*spacing_p], y=[y_pretensado], mode='markers', marker=dict(size=phi_p_val*1.1, color="#FFFF00", symbol="diamond"), showlegend=False))
        fig_sec_p.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=180, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec_p, use_container_width=True)

    st.divider()

    params_p3 = {'t_global': t_global, 't_ini': t_ini_session, 'h': h_p, 'bw': b_p, 'phi_p0': phi_p_val, 'n_p': np_p, 'fpy': fpy_p3_val, 'Ae': ae_p3_val, 'icorr': icorr_val, 'alpha': current_alpha}
    res_tensiones = calc_pre.calcular_tensiones_pretensado(params_p3)
    df_t = pd.DataFrame(res_tensiones)

    # --- LÓGICA RECTAS FIN DE VIDA ÚTIL ---
    umbral_px_p3 = 0.05 if atk_type == "Carbonation" else 0.5
    idx_life_p3 = df_t[df_t['px'] >= umbral_px_p3]
    t_life_p3 = idx_life_p3['t'].iloc[0] if not idx_life_p3.empty else None

    st.subheader("Prestressing stress evolution")
    fig_stresses = go.Figure()
    fig_stresses.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_inferior'], name="σ Bottom", line=dict(color='#228B22', width=3)))
    fig_stresses.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_superior'], name="σ Top", line=dict(color='#A60628', width=3)))
    
    fig_stresses.add_vline(x=t_ini_session, line_dash="dash", line_color="#FFD700", annotation_text="Start")
    if t_life_p3: fig_stresses.add_vline(x=t_life_p3, line_dash="dot", line_color="red", annotation_text=f"End of Life ({umbral_px_p3}mm)")

    fig_stresses.update_layout(xaxis_title="Time [years]", yaxis_title="Stress [MPa]", hovermode="x unified", template="plotly_white", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_stresses, use_container_width=True)
