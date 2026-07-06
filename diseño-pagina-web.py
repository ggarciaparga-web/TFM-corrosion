import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc
from calculos import Contevect as calc_cv
from calculos import Cortante as calc_cor
from calculos import pretensado as calc_pre
from calculos import Cortantee as calc_cor
from pdf_report import render_pdf_button

# ── Configuración ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Residual Capacity Platform",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS profesional ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; color:#1A1A1A; }
.main .block-container { background:#f8f9fa; padding-top:0!important; padding-bottom:2rem; max-width:1400px; }
.rcp-header { background:linear-gradient(135deg,#1A2B3C 0%,#1f4e79 100%); padding:26px 36px 20px 36px; margin:-1rem -1rem 0 -1rem; border-bottom:4px solid #e17000; display:flex; align-items:center; justify-content:space-between; }
.rcp-header-title { font-size:24px; font-weight:700; color:#fff; letter-spacing:1.5px; text-transform:uppercase; margin:0; }
.rcp-header-sub { font-size:11px; color:#aac4e0; letter-spacing:2px; text-transform:uppercase; margin-top:4px; }
.rcp-header-badge { background:#e17000; color:white; font-size:11px; font-weight:600; padding:4px 12px; border-radius:20px; }
.global-bar { background:#fff; border:1px solid #e0e0e0; border-left:4px solid #e17000; border-radius:0 6px 6px 0; padding:14px 20px; margin:16px 0 20px 0; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.info-banner { background:#f0f6ff; border-left:4px solid #1f4e79; padding:8px 14px; border-radius:0 4px 4px 0; font-size:12px; color:#1f4e79; margin-bottom:12px; }
.section-title { font-size:13px; font-weight:700; color:#1f4e79; text-transform:uppercase; letter-spacing:1px; border-bottom:2px solid #e17000; padding-bottom:6px; margin-bottom:14px; }
.eol-badge { margin-top:10px; background:#fff3e0; border-left:3px solid #e17000; padding:8px 12px; border-radius:0 4px 4px 0; font-size:12px; }
.stTabs [data-baseweb="tab-list"] { background:#fff; border-bottom:2px solid #e0e0e0; gap:0; padding:0; }
.stTabs [data-baseweb="tab"] { height:46px; background:transparent; border-radius:0; color:#666; padding:0 28px; font-size:13px; font-weight:500; border:none; border-bottom:3px solid transparent; margin-bottom:-2px; }
.stTabs [aria-selected="true"] { background:transparent!important; border-bottom:3px solid #e17000!important; color:#1A2B3C!important; font-weight:700!important; }
.stTabs [data-baseweb="tab"]:hover { color:#e17000!important; background:#fff8f3!important; }
.stTabs [data-baseweb="tab-panel"] { background:#f8f9fa; padding-top:20px; }
[data-testid="stMetric"] { background:#fff; border:1px solid #e8e8e8; border-top:3px solid #e17000; border-radius:6px; padding:14px 18px; box-shadow:0 1px 4px rgba(0,0,0,.05); }
[data-testid="stMetricLabel"] { font-size:11px!important; font-weight:600!important; color:#888!important; text-transform:uppercase; letter-spacing:.8px; }
[data-testid="stMetricValue"] { font-size:22px!important; font-weight:700!important; color:#1A2B3C!important; }
[data-testid="stNumberInput"] label { font-size:11px; font-weight:600; color:#555; text-transform:uppercase; letter-spacing:.5px; }
[data-testid="stNumberInput"] input { border-radius:4px; border:1px solid #d0d0d0; font-size:13px; background:#fff; }
[data-testid="stNumberInput"] input:focus { border-color:#e17000; box-shadow:0 0 0 2px rgba(225,112,0,.15); }
[data-testid="stExpander"] { border:1px solid #e0e0e0; border-radius:6px; background:#fff; }
[data-testid="stExpander"] summary { font-size:12px; font-weight:600; color:#1f4e79; text-transform:uppercase; letter-spacing:.5px; }
[data-testid="stDataFrame"] { border-radius:6px; overflow:hidden; border:1px solid #e0e0e0; }
div[data-testid="stDownloadButton"] > button { position:fixed; top:60px; right:24px; z-index:9999; background:#e17000; color:white; border:none; border-radius:6px; padding:10px 22px; font-size:13px; font-weight:600; box-shadow:0 4px 14px rgba(225,112,0,.35); cursor:pointer; transition:background .2s,box-shadow .2s; }
div[data-testid="stDownloadButton"] > button:hover { background:#c45e00; box-shadow:0 6px 18px rgba(225,112,0,.45); }
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:#f1f1f1; }
::-webkit-scrollbar-thumb { background:#ccc; border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#e17000; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rcp-header">
  <div>
    <div class="rcp-header-title">Residual Capacity Platform</div>
    <div class="rcp-header-sub">Concrete Durability &amp; Structural Capacity Tool</div>
  </div>
  <div class="rcp-header-badge">v2.0</div>
</div>
<div style='height:16px'></div>
""", unsafe_allow_html=True)

# ── Parámetros globales ───────────────────────────────────────────────────────
st.markdown('<div class="global-bar">', unsafe_allow_html=True)
gc1, gc2, gc3 = st.columns([1, 1, 4])
with gc1:
    t_global  = st.number_input("Study time [years]", value=250, step=1, key="global_time")
with gc2:
    icorr_val = st.number_input("I_corr [µA/cm²]", value=0.5, step=0.1, key="global_icorr")
with gc3:
    st.markdown("<div style='padding-top:28px;font-size:11px;color:#888;font-style:italic;'>Set global parameters before running any analysis tab.</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

if "t_ini_res"   not in st.session_state: st.session_state["t_ini_res"]   = 0.0
if "tipo_ataque" not in st.session_state: st.session_state["tipo_ataque"] = "Carbonation"
if "alpha"       not in st.session_state: st.session_state["alpha"]       = 2.0

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_ini, tab_mc, tab_pret = st.tabs([
    "📐  Initiation Period",
    "📊  Residual Capacity",
    "🔩  Prestressed Section",
])

# ── Helpers de estilo para gráficas ──────────────────────────────────────────
_FONT = dict(family="Inter, Helvetica Neue, Arial", size=11)
_GRID = dict(showgrid=True, gridcolor="#f0f0f0")

def _vline_ini(fig, x):
    fig.add_vline(x=x, line_dash="dash", line_color="#888", line_width=1.5, opacity=0.8,
        annotation=dict(text=f"<b>{x:.1f} yrs</b>", font=dict(size=11, color="#555"),
            bgcolor="rgba(255,255,255,0.8)", borderpad=3, yref="paper", y=0, yanchor="top"))

def _vline_eol(fig, x, color="#e17000"):
    fig.add_vline(x=x, line_dash="dot", line_color=color, line_width=1.5,
        annotation=dict(text=f"<b>End of Life<br>{x:.1f} yrs</b>",
            font=dict(size=11, color=color), bgcolor="rgba(255,255,255,0.8)",
            borderpad=3, yref="paper", y=0, yanchor="top"))

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 1 — INITIATION PERIOD
# ══════════════════════════════════════════════════════════════════════════════
with tab_ini:
    attack_type = st.radio("Select analysis phenomenon:", ["Carbonation", "Chlorides"], horizontal=True)
    st.session_state["attack_type"] = attack_type
    st.session_state["alpha"] = 2.0 if attack_type == "Carbonation" else 10.0
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.5, 1.2])
    with c1:
        d_mm = st.number_input("Cover c [mm]", value=30.0, help="Concrete cover thickness")

    if attack_type == "Carbonation":
        with c2:
            rh_real = st.number_input("RH_real [%]", 0, 100, 50)
            hre     = st.number_input("H_re [%]", value=65.0)
        with c3:
            rain_days = st.number_input("Rain [d/y]", value=50)
            psr       = st.number_input("P_sr [-]", value=0.0)
        with c4:
            racc = st.number_input("R_acc [mm²/y·kg/m³]", value=4541.32)
            csd  = st.number_input("C_s,d [kg/m³]", value=0.00082, format="%.5f")
        with c5:
            kcd = st.number_input("k_cd [-]", value=0.67)
            kt  = st.number_input("k_t [-]", value=1.0)
        with st.expander("Additional Calibration Parameters", expanded=False):
            ca1, ca2, ca3, ca4 = st.columns(4)
            with ca1: ge     = st.number_input("g_e [-]", value=2.5)
            with ca2: fe     = st.number_input("f_e [-]", value=5.0)
            with ca3: bw_ini = st.number_input("b_w [-]", value=0.446)
            with ca4: t0_ini = st.number_input("t_0 [-]", value=0.0767)
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(
            d_mm, rh_real, hre, ge, fe, kcd, kt, csd, racc, psr, rain_days, bw_ini, t0_ini, t_global)
        y_label, limit_val = "Carbonation Depth [mm]", d_mm
    else:
        with c2:
            c0 = st.number_input("C_0 [%]", value=0.1)
            cs = st.number_input("C_s [%]", value=4.0)
        with c3:
            ccrit = st.number_input("C_crit [%]", value=0.6)
            treal = st.number_input("T_real [K]", value=289.6)
        with c4:
            tref = st.number_input("T_ref [K]", value=293.0)
            dcrm = st.number_input("D_app·10⁻¹² [m²/s]", value=1.95, format="%.2e")
        with c5:
            a_age = st.number_input("a (ageing) [-]", value=0.4902)
            b_cl  = st.number_input("b_cl [K]", value=4800.0)
        ke, t0_cl = 1.0, 0.0767
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(
            d_mm, c0, cs, ccrit, b_cl, tref, treal, ke, t0_cl, a_age, dcrm, t_global)
        y_label, limit_val = "Concentration [%]", ccrit

    st.session_state["t_ini_res"] = t_ini_calc if t_ini_calc is not None else 0.0
    st.divider()

    col_m, col_tuutti, col_prog = st.columns([0.8, 2, 2])
    with col_m:
        if t_ini_calc and t_ini_calc > 0:
            st.metric("Initiation Time", f"{t_ini_calc:.2f} yrs")
            st.metric("Attack Type", attack_type)
        else:
            st.warning("⚠️ No initiation detected within study period.")

    with col_tuutti:
        if t_i is not None:
            t_ini_eff = st.session_state["t_ini_res"]
            px_vals   = 0.0116 * icorr_val * np.maximum(0, t_i - t_ini_eff)
            fig_tuutti = go.Figure()
            fig_tuutti.add_trace(go.Scatter(x=t_i, y=px_vals,
                line=dict(color="#e17000", width=2.5),
                fill="tozeroy", fillcolor="rgba(225,112,0,0.08)", name="Pₓ"))
            fig_tuutti.update_layout(
                title=dict(text="Tuutti's Model — Pₓ", font=dict(size=13, color="#1f4e79")),
                height=280, plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(title=dict(text="Time [years]"), **_GRID),
                yaxis=dict(title=dict(text="Pₓ [mm]"), **_GRID),
                margin=dict(l=0, r=0, t=40, b=0), font=_FONT)
            st.plotly_chart(fig_tuutti, use_container_width=True)

    with col_prog:
        if t_i is not None:
            fig_ini = go.Figure()
            fig_ini.add_trace(go.Scatter(x=t_i, y=y_vals, fill="tozeroy",
                fillcolor="rgba(31,78,121,0.08)",
                line=dict(color="#1f4e79", width=2.5), name="Progress"))
            fig_ini.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i),
                line=dict(color="#e17000", dash="dash", width=1.5), name="Limit"))
            fig_ini.update_layout(
                title=dict(text="Initiation Progress", font=dict(size=13, color="#1f4e79")),
                height=280, plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(title=dict(text="Time [years]"), **_GRID),
                yaxis=dict(title=dict(text=y_label), **_GRID),
                margin=dict(l=0, r=0, t=40, b=0), font=_FONT,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_ini, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 2 — RESIDUAL CAPACITY
# ══════════════════════════════════════════════════════════════════════════════
with tab_mc:
    t_ini_session = st.session_state.get("t_ini_res", 0.0)
    current_alpha = st.session_state.get("alpha", 2.0)
    atk_type      = st.session_state.get("attack_type", "Carbonation")

    st.markdown(
        f"<div class='info-banner'><b>Initiation:</b> {t_ini_session:.2f} yrs &nbsp;|&nbsp; "
        f"<b>Type:</b> {atk_type} &nbsp;|&nbsp; <b>α:</b> {current_alpha}</div>",
        unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c_viz = st.columns([1, 1, 1, 1, 1, 2])
    with c1:
        h_val = st.number_input("h [mm]", value=300, key="h_mc")
        b_val = st.number_input("b [mm]", value=150, key="b_mc")
    with c2:
        rec_sup = st.number_input("c_top [mm]", value=20, key="rs_mc")
        rec_inf = st.number_input("c_bot [mm]", value=20, key="ri_mc")
    with c3:
        n_sup = st.number_input("n_top", value=2, min_value=0, key="ns_mc")
        p_sup = st.number_input("Φ_top [mm]", value=10, key="ps_mc")
    with c4:
        n_inf     = st.number_input("n_bot", value=2, min_value=0, key="ni_mc")
        phi_inf_0 = st.number_input("Φ_bot [mm]", value=16, key="pi_mc")
    with c5:
        fyk     = st.number_input("f_yk [MPa]", value=500, key="fyk_mc")
        fck_val = st.number_input("f_ck [MPa]", value=25,  key="fck_mc")

    with c_viz:
        fig_sec = go.Figure()
        fig_sec.add_shape(type="rect", x0=0, y0=0, x1=b_val, y1=h_val,
            line=dict(color="#1f4e79", width=2), fillcolor="rgba(31,78,121,0.08)")
        if n_sup > 0:
            sp_s = (b_val - 2*rec_sup)/(n_sup-1) if n_sup > 1 else 0
            xs   = rec_sup if n_sup > 1 else b_val/2
            for i in range(n_sup):
                fig_sec.add_trace(go.Scatter(x=[xs+i*sp_s], y=[h_val-rec_sup],
                    mode="markers", marker=dict(size=p_sup*0.8, color="#2C2C2C"), showlegend=False))
        if n_inf > 0:
            sp_i = (b_val - 2*rec_inf)/(n_inf-1) if n_inf > 1 else 0
            xi   = rec_inf if n_inf > 1 else b_val/2
            for i in range(n_inf):
                fig_sec.add_trace(go.Scatter(x=[xi+i*sp_i], y=[rec_inf],
                    mode="markers", marker=dict(size=phi_inf_0*0.8, color="#e17000"), showlegend=False))
        fig_sec.update_layout(xaxis=dict(visible=False),
            yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            height=180, margin=dict(l=5,r=5,t=5,b=5),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sec, use_container_width=True)

    st.divider()

    t_mc, px_mc, phi_inf_mc, mu_std_mc, mu_cons_mc = calc_mc.calcular_capacidad_residual(
        t_global, b_val, h_val, rec_sup, rec_inf, n_sup, p_sup, n_inf, phi_inf_0,
        fyk, fck_val, icorr_val, current_alpha, t_ini_session)
    t_cv, df_criticos, mu_cv = calc_cv.calcular_contevect(
        t_global, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0,
        fyk, fck_val, icorr_val, current_alpha, t_ini_session)

    umbral_px = 0.05 if atk_type == "Carbonation" else 0.5
    idx_life  = np.where(px_mc >= umbral_px)[0]
    t_life    = t_mc[idx_life[0]] if len(idx_life) > 0 else None

    st.markdown("<div class='section-title'>Residual Flexural Capacity Comparison</div>", unsafe_allow_html=True)
    col_graph, col_table = st.columns([2, 1])

    with col_graph:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=t_cv, y=mu_cv, name="Contevect Model",
            line=dict(color="#1f4e79", width=2.5)))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_std_mc, name="MC Standard",
            line=dict(color="#e17000", width=2.5, dash="dash")))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_cons_mc, name="MC Conservative",
            line=dict(color="#2c2c2a", width=2.5, dash="dot")))
        fig_res.add_trace(go.Scatter(x=df_criticos["Tiempo"], y=df_criticos["Mu"],
            mode="markers", name="Critical Events (CV)",
            marker=dict(color="#1f4e79", size=9, symbol="diamond")))
        _vline_ini(fig_res, t_ini_session)
        if t_life: _vline_eol(fig_res, t_life)
        fig_res.update_layout(
            xaxis=dict(title=dict(text="Time [years]"), rangemode="tozero", **_GRID),
            yaxis=dict(title=dict(text="Moment Capacity [kNm]"), rangemode="tozero", **_GRID),
            hovermode="x unified", template="plotly_white", height=450,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=_FONT, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_res, use_container_width=True)

    with col_table:
        st.markdown("<div style='font-size:11px;font-weight:700;color:#1f4e79;text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px;'>Key Degradation Steps</div>", unsafe_allow_html=True)
        st.dataframe(df_criticos[["Tiempo","Px","Mu"]],
            column_config={
                "Tiempo": st.column_config.NumberColumn("Time [y]",   format="%.1f"),
                "Px":     st.column_config.NumberColumn("Corr. [mm]", format="%.3f"),
                "Mu":     st.column_config.NumberColumn("Mu [kNm]",   format="%.2f"),
            }, hide_index=True, use_container_width=True)
        if t_life:
            st.markdown(f"<div class='eol-badge'>⚠️ <b>End of service life:</b> {t_life:.1f} years</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA 3 — PRESTRESSED SECTION
# ══════════════════════════════════════════════════════════════════════════════
with tab_pret:
    t_ini_session = st.session_state.get("t_ini_res", 0.0)
    current_alpha = st.session_state.get("alpha", 2.0)
    atk_type      = st.session_state.get("attack_type", "Carbonation")

    st.markdown(
        f"<div class='info-banner'><b>Initiation:</b> {t_ini_session:.2f} yrs &nbsp;|&nbsp; "
        f"<b>Type:</b> {atk_type}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6, c_viz = st.columns([1, 1, 1, 1, 1, 1, 2.5])
    with c1:
        h_p = st.number_input("h [mm]", value=h_val, key="h_p3")
        b_p = st.number_input("b [mm]", value=b_val, key="b_p3")
    with c2:
        rs_p = st.number_input("c_top [mm]", value=rec_sup, key="rs_p3")
        ri_p = st.number_input("c_bot [mm]", value=rec_inf, key="ri_p3")
    with c3:
        nt_p = st.number_input("n_top", value=n_sup, key="nt_p3")
        pt_p = st.number_input("Φ_top [mm]", value=p_sup, key="pt_p3")
    with c4:
        np_p      = st.number_input("n_bot", value=2, key="np_p3")
        phi_p_val = st.number_input("Φ_p [mm]", value=14.0, key="phip_p3")
    with c5:
        ae_p3_val  = st.number_input("A_e [mm²]", value=92.0, key="ae_p3_key")
        fpy_p3_val = st.number_input("f_py [MPa]", value=1860, key="fpy_p3_key")
    with c6:
        fyk_p = st.number_input("f_yk [MPa]", value=fyk,     key="fyk_p3")
        fck_p = st.number_input("f_ck [MPa]", value=fck_val, key="fck_p3")

    with st.expander("Shear inputs", expanded=False):
        cv1, cv2, cv3 = st.columns([1, 1, 1])
        with cv1:
            v_ed_val   = st.number_input("V_Ed [kN]",   value=0.0, key="ved_p3")
            m_ed_val   = st.number_input("M_Ed [kNm]",  value=0.0, key="med_p3")
        with cv2:
            gamma_v_val = st.number_input("gamma_V",         value=1.4,  key="gv_p3")
            d_lower_val = st.number_input("d_lower [mm]",    value=12.0, key="dl_p3")

    with c_viz:
        fig_sec_p = go.Figure()
        fig_sec_p.add_shape(type="rect", x0=0, y0=0, x1=b_p, y1=h_p,
            line=dict(color="#1f4e79", width=2), fillcolor="rgba(31,78,121,0.08)")
        if nt_p > 0:
            sp_s = (b_p - 2*rs_p)/(nt_p-1) if nt_p > 1 else 0
            xs   = rs_p if nt_p > 1 else b_p/2
            for i in range(nt_p):
                fig_sec_p.add_trace(go.Scatter(x=[xs+i*sp_s], y=[h_p-rs_p],
                    mode="markers", marker=dict(size=pt_p*0.8, color="#2C2C2C"), showlegend=False))
        y_pre = (h_p/2) - ae_p3_val
        if np_p > 0:
            sp_p = (b_p - 2*ri_p)/(np_p-1) if np_p > 1 else 0
            xp   = ri_p if np_p > 1 else b_p/2
            for i in range(np_p):
                fig_sec_p.add_trace(go.Scatter(x=[xp+i*sp_p], y=[y_pre],
                    mode="markers", marker=dict(size=phi_p_val*1.1, color="#1f4e79"), showlegend=False))
        fig_sec_p.update_layout(xaxis=dict(visible=False),
            yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            height=180, margin=dict(l=5,r=5,t=5,b=5),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sec_p, use_container_width=True)

    st.divider()

    # ── Cálculos ──────────────────────────────────────────────────────────────
    params_p3 = dict(t_global=t_global, t_ini=t_ini_session, h=h_p, bw=b_p,
        phi_p0=phi_p_val, n_p=np_p, fpy=fpy_p3_val, Ae=ae_p3_val,
        icorr=icorr_val, alpha=current_alpha)
    res_tensiones = calc_pre.calcular_tensiones_pretensado(params_p3)
    df_t = pd.DataFrame(res_tensiones)

    params_cor = dict(t_global=t_global, t_ini=t_ini_session, h=h_p, bw=b_p,
        c_bot=ri_p, n_p=np_p, phi_p0=phi_p_val, fpy=fpy_p3_val, Ae=ae_p3_val,
        fck=fck_p, icorr=icorr_val, alpha=current_alpha,
        v_ed=v_ed_val, m_ed=m_ed_val, gamma_v=gamma_v_val, d_lower=d_lower_val)
    res_cor = calc_cor.calcular_cortante_pretensado(params_cor)
    df_cor  = pd.DataFrame(res_cor)

    umbral_px_p3 = 0.05 if atk_type == "Carbonation" else 0.5
    idx_life_p3  = df_t[df_t["px"] >= umbral_px_p3]
    t_life_p3    = idx_life_p3["t"].iloc[0] if not idx_life_p3.empty else None

    # ── Gráficas ──────────────────────────────────────────────────────────────
    col_stress, col_shear = st.columns(2)

    with col_stress:
        st.markdown("<div class='section-title'>Prestress Evolution</div>", unsafe_allow_html=True)
        fig_stresses = go.Figure()
        fig_stresses.add_trace(go.Scatter(x=df_t["t"], y=df_t["sigma_inferior"],
            name="σ Bottom", line=dict(color="#e17000", width=2.5),
            hovertemplate="%{y:.1f} MPa"))
        fig_stresses.add_trace(go.Scatter(x=df_t["t"], y=df_t["sigma_superior"],
            name="σ Top", line=dict(color="#1f4e79", width=2.5),
            hovertemplate="%{y:.1f} MPa"))
        _vline_ini(fig_stresses, t_ini_session)
        if t_life_p3: _vline_eol(fig_stresses, t_life_p3)
        fig_stresses.update_layout(
            xaxis=dict(title=dict(text="Time [years]"), rangemode="tozero", **_GRID),
            yaxis=dict(title=dict(text="Stress [MPa]"), rangemode="tozero", **_GRID),
            hovermode="x unified", template="plotly_white", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=_FONT, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_stresses, use_container_width=True)

    with col_shear:
        st.markdown("<div class='section-title'>Shear Capacity V<sub>Rd</sub></div>", unsafe_allow_html=True)
        fig_shear = go.Figure()
        fig_shear.add_trace(go.Scatter(x=df_cor["t"], y=df_cor["vrd"],
            name="V<sub>Rd</sub>", line=dict(color="#1f4e79", width=2.5),
            hovertemplate="%{y:.2f} kN"))
        if v_ed_val > 0:
            fig_shear.add_hline(y=v_ed_val, line_dash="dot",
                line_color="#e17000", line_width=1.5,
                annotation_text=f"V_Ed = {v_ed_val:.1f} kN",
                annotation_position="top right",
                annotation_font=dict(color="#e17000"))
        _vline_ini(fig_shear, t_ini_session)
        if t_life_p3: _vline_eol(fig_shear, t_life_p3)
        fig_shear.update_layout(
            xaxis=dict(title=dict(text="Time [years]"), rangemode="tozero", **_GRID),
            yaxis=dict(title=dict(text="Shear [kN]"), rangemode="tozero", **_GRID),
            hovermode="x unified", template="plotly_white", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=_FONT, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_shear, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PDF STATE + BOTÓN FLOTANTE (fuera de todas las pestañas)
# ══════════════════════════════════════════════════════════════════════════════
pdf_state = {}
pdf_state.update({
    # Globales
    "t_global":     t_global,
    "icorr_val":    icorr_val,
    "attack_type":  st.session_state.get("attack_type", "Carbonation"),
    "t_ini_calc":   st.session_state.get("t_ini_res", 0.0),
    # Pestaña 1
    "fig_tuutti":   fig_tuutti  if "fig_tuutti"  in dir() else None,
    "fig_ini":      fig_ini     if "fig_ini"     in dir() else None,
    # Pestaña 2
    "fig_res":      fig_res     if "fig_res"     in dir() else None,
    "df_criticos":  df_criticos if "df_criticos" in dir() else None,
    "b_val": b_val, "h_val": h_val,
    "fck_val": fck_val, "fyk": fyk,
    "n_sup": n_sup, "p_sup": p_sup,
    "n_inf": n_inf, "phi_inf_0": phi_inf_0,
    "t_life":       t_life      if "t_life"      in dir() else None,
    # Pestaña 3
    "fig_stresses": fig_stresses if "fig_stresses" in dir() else None,
    "fig_shear":    fig_shear    if "fig_shear"    in dir() else None,
    "df_t":         df_t         if "df_t"         in dir() else None,
    "df_cor":       df_cor       if "df_cor"        in dir() else None,
    "h_p": h_p, "b_p": b_p,
    "phi_p_val": phi_p_val, "np_p": np_p,
    "fpy_p3_val": fpy_p3_val, "ae_p3_val": ae_p3_val,
    "t_life_p3":    t_life_p3   if "t_life_p3"   in dir() else None,
})

render_pdf_button(pdf_state)
