import streamlit as st
import pandas as pd
import numpy as np
import base64
import plotly.graph_objects as go
from calculos import tiempoiniciacion as calc_ini
from calculos import Modelcode as calc_mc
from calculos import Contevect as calc_cv
from calculos import Cortante as calc_cor
from calculos import pretensado as calc_pre
 
# ── PAGE CONFIG (solo una vez) ────────────────────────────────────────────
st.set_page_config(page_title="Durability & Residual Capacity Platform", layout="wide")
 
# ── ESTILO GLOBAL ─────────────────────────────────────────────────────────
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main { background-color: #ffffff; }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background-color: #f0f0f0;
        border-radius: 4px 4px 0 0;
        color: #666666;
        padding: 10px 22px;
        border: 1px solid #cccccc;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        border-bottom: 2px solid #e17000 !important;
        color: #000000 !important;
        font-weight: 700 !important;
    }
    .input-box {
        background-color: #f8f8f8;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 14px 16px 6px 16px;
        margin-bottom: 12px;
    }
    .legend-dot {
        display: inline-block;
        width: 12px; height: 12px;
        border-radius: 50%;
        margin-right: 5px;
        vertical-align: middle;
    }
    </style>
""", unsafe_allow_html=True)
 
# ── SESSION STATE DEFAULTS ────────────────────────────────────────────────
_defaults = {
    't_ini_res': 0.0, 'tipo_ataque': "Carbonation", 'attack_type': "Carbonation",
    'alpha': 2.0, 'h_val': 300, 'b_val': 150, 'rec_sup': 20, 'rec_inf': 20,
    'n_sup': 2, 'p_sup': 10, 'n_inf': 2, 'phi_inf_0': 16, 'fyk': 500, 'fck_val': 25,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
 
# ── HELPERS ───────────────────────────────────────────────────────────────
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None
 
GRID_COLOR = "#F0F0F0"
LINE_WIDTH = 3
 
def base_layout(title="", height=420, xtitle="Time [years]", ytitle=""):
    return dict(
        title=dict(text=title, font=dict(size=12, color="#444444")) if title else None,
        xaxis=dict(title=xtitle, rangemode="tozero",
                   gridcolor=GRID_COLOR, linecolor="#cccccc", zeroline=False),
        yaxis=dict(title=ytitle, rangemode="tozero",
                   gridcolor=GRID_COLOR, linecolor="#cccccc", zeroline=False),
        plot_bgcolor="white", paper_bgcolor="white",
        hovermode="x unified", height=height,
        margin=dict(l=10, r=10, t=45, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11)),
        template="plotly_white",
    )
 
def add_vline_annotated(fig, x, label, color, dash="dash"):
    fig.add_vline(
        x=x, line_dash=dash, line_color=color, line_width=1.5, opacity=0.85,
        annotation=dict(
            text=f"<b>{label}</b>",
            font=dict(size=11, color=color),
            bgcolor="rgba(255,255,255,0.80)",
            borderpad=3,
            yref="paper", y=0, yanchor="top",
        )
    )
 
def section_legend_html(top_color, bot_color, top_label, bot_label):
    return (
        f'<span class="legend-dot" style="background:{top_color}"></span>'
        f'<span style="font-size:12px;color:#555">{top_label}</span>'
        f'&nbsp;&nbsp;&nbsp;'
        f'<span class="legend-dot" style="background:{bot_color}"></span>'
        f'<span style="font-size:12px;color:#555">{bot_label}</span>'
    )
 
# ── BANNER ────────────────────────────────────────────────────────────────
img_b64 = get_base64("captra.png")
if img_b64:
    st.markdown(f"""
        <style>
        .header-container {{
            background-image: linear-gradient(rgba(255,255,255,0.25), rgba(255,255,255,0.25)),
                              url("data:image/png;base64,{img_b64}");
            background-position: 50% 65%; background-size: cover;
            border-radius: 8px; text-align: center; margin-bottom: 20px;
            display: flex; align-items: center; justify-content: center;
            height: 100px; overflow: hidden;
        }}
        .header-title {{
            color: #1a1a1a; font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 28px; font-weight: 700;
            text-shadow: 2px 2px 8px rgba(255,255,255,1); margin: 0; padding: 0;
        }}
        </style>
        <div class="header-container">
            <p class="header-title">Durability and Residual Capacity Platform</p>
        </div>""", unsafe_allow_html=True)
else:
    st.title("Durability and Residual Capacity Platform")
    st.warning("⚠️ Image 'captra.png' not found.")
 
# ── PARÁMETROS GLOBALES ───────────────────────────────────────────────────
st.markdown('<div class="input-box">', unsafe_allow_html=True)
g1, g2, _, _ = st.columns(4)
with g1:
    t_global  = st.number_input("Study time [years]", value=250, step=1, key="global_time")
with g2:
    icorr_val = st.number_input("$I_{corr}$ [μA/cm²]", value=0.5, step=0.1, key="global_icorr")
st.markdown('</div>', unsafe_allow_html=True)
 
# ── TABS ──────────────────────────────────────────────────────────────────
tab_ini, tab_mc, tab_pret = st.tabs(["📈  Initiation Period", "🔩  Residual Capacity", "🔗  Prestressed"])
 
# ══════════════════════════════════════════════════════════════════════════
# PESTAÑA 1 — TIEMPO DE INICIACIÓN
# ══════════════════════════════════════════════════════════════════════════
with tab_ini:
    attack_type = st.radio("Select analysis phenomenon:", ["Carbonation", "Chlorides"], horizontal=True)
    st.session_state['attack_type'] = attack_type
    st.session_state['alpha'] = 2.0 if attack_type == "Carbonation" else 10.0
 
    st.markdown('<div class="input-box">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.2, 1.5, 1.2])
    with c1:
        d_mm = st.number_input("Cover $c$ [mm]", value=30.0)
 
    if attack_type == "Carbonation":
        with c2:
            rh_real = st.number_input("$RH_{real}$ [%]", 0, 100, 50)
            hre     = st.number_input("$H_{re}$ [%]", value=65.0)
        with c3:
            rain_days = st.number_input("Rain [d/y]", value=50)
            psr       = st.number_input("$P_{sr}$ [-]", value=0.0)
        with c4:
            racc = st.number_input("$R_{acc}$ [mm²/y / kg/m³]", value=4541.32)
            csd  = st.number_input("$C_{s,d}$ [kg/m³]", value=0.00082, format="%.5f")
        with c5:
            kcd = st.number_input("$k_{cd}$ [-]", value=0.67)
            kt  = st.number_input("$k_{t}$ [-]", value=1.0)
        with st.expander("Additional Calibration Parameters"):
            ca1, ca2, ca3, ca4 = st.columns(4)
            with ca1: ge     = st.number_input("$g_{e}$ [-]", value=2.5)
            with ca2: fe     = st.number_input("$f_{e}$ [-]", value=5.0)
            with ca3: bw_ini = st.number_input("$b_{w}$ [-]", value=0.446)
            with ca4: t0_ini = st.number_input("$t_{0}$ [-]", value=0.0767)
        t_i, w_i, y_vals, t_ini_calc = calc_ini.calcular_carbonatacion(
            d_mm, rh_real, hre, ge, fe, kcd, kt, csd, racc, psr, rain_days, bw_ini, t0_ini, t_global)
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
            dcrm = st.number_input("$D_{app}·10^{-12}$ [m²/s]", value=1.95, format="%.2e")
        with c5:
            a_age = st.number_input("$a$ (ageing) [-]", value=0.4902)
            b_cl  = st.number_input("$b_{cl}$ [K]", value=4800.0)
        ke, t0_cl = 1.0, 0.0767
        t_i, dapp, z, y_vals, t_ini_calc = calc_ini.calcular_cloruros(
            d_mm, c0, cs, ccrit, b_cl, tref, treal, ke, t0_cl, a_age, dcrm, t_global)
        y_label, limit_val = "Concentration [%]", ccrit
 
    st.markdown('</div>', unsafe_allow_html=True)
    st.session_state['t_ini_res'] = t_ini_calc if t_ini_calc else 0.0
 
    st.divider()
    res_metrica, res_tuutti, res_progreso = st.columns([0.8, 2, 2])
 
    with res_metrica:
        if t_ini_calc and t_ini_calc > 0:
            st.metric("Initiation Time", f"{t_ini_calc:.2f} yrs")
        else:
            st.warning("No initiation detected")
 
    with res_tuutti:
        if t_i is not None:
            t_ini_eff = st.session_state['t_ini_res']
            px_vals   = 0.0116 * icorr_val * np.maximum(0, t_i - t_ini_eff)
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=t_i, y=px_vals,
                line=dict(color='#228B22', width=LINE_WIDTH), name="P<sub>x</sub>",
                hovertemplate="%{y:.3f} mm"))
            fig_t.update_layout(**base_layout(
                title="Tuutti's Model — Corrosion Penetration P<sub>x</sub>",
                ytitle="P<sub>x</sub> [mm]", height=300))
            st.plotly_chart(fig_t, use_container_width=True)
 
    with res_progreso:
        if t_i is not None:
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=t_i, y=y_vals,
                fill='tozeroy', fillcolor='rgba(225,112,0,0.12)',
                line=dict(color='#e17000', width=LINE_WIDTH), name="Progress",
                hovertemplate="%{y:.3f}"))
            fig_p.add_trace(go.Scatter(x=t_i, y=[limit_val]*len(t_i),
                line=dict(color='#333333', dash='dash', width=1.5), name="Limit"))
            fig_p.update_layout(**base_layout(
                title="Initiation Progress", ytitle=y_label, height=300))
            st.plotly_chart(fig_p, use_container_width=True)
 
# ══════════════════════════════════════════════════════════════════════════
# PESTAÑA 2 — CAPACIDAD RESIDUAL
# ══════════════════════════════════════════════════════════════════════════
with tab_mc:
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type      = st.session_state.get('attack_type', "Carbonation")
 
    st.info(f"**Initiation time:** {t_ini_session:.2f} yrs  ·  "
            f"**Attack type:** {atk_type}  ·  **α:** {current_alpha}")
 
    st.markdown('<div class="input-box">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c_viz = st.columns([1, 1, 1, 1, 1, 2])
    with c1:
        h_val     = st.number_input("$h$ [mm]",      value=300, key="h_mc")
        b_val     = st.number_input("$b$ [mm]",      value=150, key="b_mc")
    with c2:
        rec_sup   = st.number_input("$c_{top}$ [mm]", value=20,  key="rs_mc")
        rec_inf   = st.number_input("$c_{bot}$ [mm]", value=20,  key="ri_mc")
    with c3:
        n_sup     = st.number_input("$n_{top}$",     value=2, min_value=0, key="ns_mc")
        p_sup     = st.number_input("$Φ_{top}$",     value=10, key="ps_mc")
    with c4:
        n_inf     = st.number_input("$n_{bot}$",     value=2, min_value=0, key="ni_mc")
        phi_inf_0 = st.number_input("$Φ_{bot}$",     value=16, key="pi_mc")
    with c5:
        fyk       = st.number_input("$f_{yk}$ [MPa]", value=500, key="fyk_mc")
        fck_val   = st.number_input("$f_{ck}$ [MPa]", value=25,  key="fck_mc")
 
    for k, v in [('h_val', h_val), ('b_val', b_val), ('rec_sup', rec_sup),
                 ('rec_inf', rec_inf), ('n_sup', n_sup), ('p_sup', p_sup),
                 ('fyk', fyk), ('fck_val', fck_val)]:
        st.session_state[k] = v
 
    with c_viz:
        fig_sec = go.Figure()
        fig_sec.add_shape(type="rect", x0=0, y0=0, x1=b_val, y1=h_val,
                          line=dict(color="#333333", width=2), fillcolor="#DDDDDD", opacity=0.4)
        if n_sup > 0:
            sp = (b_val - 2*rec_sup) / (n_sup - 1) if n_sup > 1 else 0
            xs = rec_sup if n_sup > 1 else b_val / 2
            for i in range(n_sup):
                fig_sec.add_trace(go.Scatter(
                    x=[xs + i*sp], y=[h_val - rec_sup], mode='markers',
                    marker=dict(size=p_sup*0.8, color="#2C2C2C",
                                line=dict(color="#000000", width=1)), showlegend=False))
        if n_inf > 0:
            sp = (b_val - 2*rec_inf) / (n_inf - 1) if n_inf > 1 else 0
            xi = rec_inf if n_inf > 1 else b_val / 2
            for i in range(n_inf):
                fig_sec.add_trace(go.Scatter(
                    x=[xi + i*sp], y=[rec_inf], mode='markers',
                    marker=dict(size=phi_inf_0*0.8, color="#CC0000",
                                line=dict(color="#800000", width=1)), showlegend=False))
        fig_sec.update_layout(
            xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            height=170, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec, use_container_width=True)
        st.markdown(section_legend_html("#2C2C2C", "#CC0000", "Top steel", "Bottom steel"),
                    unsafe_allow_html=True)
 
    st.markdown('</div>', unsafe_allow_html=True)
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
 
    st.subheader("Residual Flexural Capacity")
    col_graph, col_table = st.columns([2, 1])
 
    with col_graph:
        COLOR_CV   = "#228B22"
        COLOR_STD  = "#1f77b4"
        COLOR_CONS = "#d62728"
 
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=t_cv, y=mu_cv, name="Contevect Model",
            line=dict(color=COLOR_CV, width=LINE_WIDTH), hovertemplate="%{y:.2f} kNm"))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_std_mc, name="MC Standard",
            line=dict(color=COLOR_STD, width=LINE_WIDTH, dash="dash"), hovertemplate="%{y:.2f} kNm"))
        fig_res.add_trace(go.Scatter(x=t_mc, y=mu_cons_mc, name="MC Conservative",
            line=dict(color=COLOR_CONS, width=LINE_WIDTH, dash="dot"), hovertemplate="%{y:.2f} kNm"))
        fig_res.add_trace(go.Scatter(
            x=df_criticos["Tiempo"], y=df_criticos["Mu"],
            mode='markers', name='Critical Events (CV)',
            marker=dict(color=COLOR_CV, size=10, symbol='diamond',
                        line=dict(color="#ffffff", width=1.5))))
 
        add_vline_annotated(fig_res, t_ini_session,
                            f"Start · {t_ini_session:.1f} y", "#888888", dash="dash")
        if t_life:
            add_vline_annotated(fig_res, t_life,
                                f"End of Life · {t_life:.1f} y", "#CC0000", dash="dot")
 
        layout = base_layout(
            title=(f"M<sub>rd</sub> evolution — b={b_val} mm · h={h_val} mm · "
                   f"f<sub>ck</sub>={fck_val} MPa · f<sub>yk</sub>={fyk} MPa"),
            ytitle="Moment Capacity [kNm]", height=460)
        fig_res.update_layout(**layout)
        st.plotly_chart(fig_res, use_container_width=True)
 
    with col_table:
        st.markdown("**Key Degradation Events (Contevect)**")
        st.dataframe(df_criticos[["Tiempo", "Px", "Mu"]],
            column_config={
                "Tiempo": st.column_config.NumberColumn("Time [y]",   format="%.1f"),
                "Px":     st.column_config.NumberColumn("Corr. [mm]", format="%.3f"),
                "Mu":     st.column_config.NumberColumn("Mu [kNm]",   format="%.2f"),
            }, hide_index=True, use_container_width=True)
 
# ══════════════════════════════════════════════════════════════════════════
# PESTAÑA 3 — PRETENSADO
# ══════════════════════════════════════════════════════════════════════════
with tab_pret:
    t_ini_session = st.session_state.get('t_ini_res', 0.0)
    current_alpha = st.session_state.get('alpha', 2.0)
    atk_type      = st.session_state.get('attack_type', "Carbonation")
 
    st.info(f"**Initiation time:** {t_ini_session:.2f} yrs  ·  **Attack type:** {atk_type}")
 
    _h   = st.session_state.get('h_val', 300)
    _b   = st.session_state.get('b_val', 150)
    _rs  = st.session_state.get('rec_sup', 20)
    _ri  = st.session_state.get('rec_inf', 20)
    _ns  = st.session_state.get('n_sup', 2)
    _ps  = st.session_state.get('p_sup', 10)
    _fyk = st.session_state.get('fyk', 500)
    _fck = st.session_state.get('fck_val', 25)
 
    st.markdown('<div class="input-box">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6, c_viz = st.columns([1, 1, 1, 1, 1, 1, 2.5])
    with c1:
        h_p = st.number_input("$h$ [mm]",   value=_h,  key="h_p3")
        b_p = st.number_input("$b$ [mm]",   value=_b,  key="b_p3")
    with c2:
        rs_p = st.number_input("$c_{top}$ [mm]", value=_rs,  key="rs_p3")
        ri_p = st.number_input("$c_{bot}$ [mm]", value=_ri,  key="ri_p3")
    with c3:
        nt_p = st.number_input("$n_{top}$",  value=_ns, key="nt_p3")
        pt_p = st.number_input("$Φ_{top}$",  value=_ps, key="pt_p3")
    with c4:
        np_p      = st.number_input("$n_{bot}$",       value=2,    key="np_p3")
        phi_p_val = st.number_input("$Φ_{p}$ [mm]",   value=14.0, key="phip_p3")
    with c5:
        ae_p3_val  = st.number_input("$A_e$ [mm]",     value=92.0,  key="ae_p3_key")
        fpy_p3_val = st.number_input("$f_{py}$ [MPa]", value=1860,  key="fpy_p3_key")
    with c6:
        fyk_p = st.number_input("$f_{yk}$ [MPa]", value=_fyk, key="fyk_p3")
        fck_p = st.number_input("$f_{ck}$ [MPa]", value=_fck, key="fck_p3")
 
    with c_viz:
        fig_sec_p = go.Figure()
        fig_sec_p.add_shape(type="rect", x0=0, y0=0, x1=b_p, y1=h_p,
                            line=dict(color="#333333", width=2), fillcolor="#DDDDDD", opacity=0.4)
        if nt_p > 0:
            sp = (b_p - 2*rs_p) / (nt_p - 1) if nt_p > 1 else 0
            xs = rs_p if nt_p > 1 else b_p / 2
            for i in range(nt_p):
                fig_sec_p.add_trace(go.Scatter(
                    x=[xs + i*sp], y=[h_p - rs_p], mode='markers',
                    marker=dict(size=pt_p*0.8, color="#2C2C2C",
                                line=dict(color="#000000", width=1)), showlegend=False))
        y_pretensado = (h_p / 2) - ae_p3_val
        if np_p > 0:
            sp = (b_p - 2*ri_p) / (np_p - 1) if np_p > 1 else 0
            xp = ri_p if np_p > 1 else b_p / 2
            for i in range(np_p):
                fig_sec_p.add_trace(go.Scatter(
                    x=[xp + i*sp], y=[y_pretensado], mode='markers',
                    marker=dict(size=phi_p_val*1.1, color="#1f77b4",
                                line=dict(color="#0a4a7a", width=1)), showlegend=False))
        fig_sec_p.update_layout(
            xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            height=170, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sec_p, use_container_width=True)
        st.markdown(section_legend_html("#2C2C2C", "#1f77b4", "Top steel", "Prestressing steel"),
                    unsafe_allow_html=True)
 
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
 
    params_p3 = {
        't_global': t_global, 't_ini': t_ini_session,
        'h': h_p, 'bw': b_p, 'phi_p0': phi_p_val, 'n_p': np_p,
        'fpy': fpy_p3_val, 'Ae': ae_p3_val, 'icorr': icorr_val, 'alpha': current_alpha,
    }
    res_tensiones = calc_pre.calcular_tensiones_pretensado(params_p3)
    df_t = pd.DataFrame(res_tensiones)
 
    umbral_px_p3 = 0.05 if atk_type == "Carbonation" else 0.5
    idx_life_p3  = df_t[df_t['px'] >= umbral_px_p3]
    t_life_p3    = idx_life_p3['t'].iloc[0] if not idx_life_p3.empty else None
 
    st.subheader("Prestressing Stress Evolution")
    fig_st = go.Figure()
    fig_st.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_inferior'],
        name="σ Bottom", line=dict(color='#228B22', width=LINE_WIDTH),
        hovertemplate="%{y:.1f} MPa"))
    fig_st.add_trace(go.Scatter(x=df_t['t'], y=df_t['sigma_superior'],
        name="σ Top", line=dict(color='#A60628', width=LINE_WIDTH),
        hovertemplate="%{y:.1f} MPa"))
 
    add_vline_annotated(fig_st, t_ini_session,
                        f"Start · {t_ini_session:.1f} y", "#888888", dash="dash")
    if t_life_p3:
        add_vline_annotated(fig_st, t_life_p3,
                            f"End of Life · {t_life_p3:.1f} y", "#CC0000", dash="dot")
 
    fig_st.update_layout(**base_layout(
        title=(f"Stress evolution — b={b_p} mm · h={h_p} mm · "
               f"f<sub>py</sub>={fpy_p3_val} MPa"),
        ytitle="Stress [MPa]", height=460))
    st.plotly_chart(fig_st, use_container_width=True)
