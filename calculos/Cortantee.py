"""
calculos/cortante.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cálculo de resistencia a cortante Vrd (EC2:2023) para
vigas pretensadas con degradación por corrosión en el tiempo.

Función principal:
    calcular_cortante_pretensado(params) → list[dict]

Parámetros de entrada (dict 'params'):
    t_global   : int/float  — tiempo total de análisis [años]
    t_ini      : float      — tiempo de inicio de corrosión [años]
    h          : float      — canto total de la sección [mm]
    bw         : float      — ancho del alma [mm]
    c_bot      : float      — recubrimiento inferior [mm]  (ri_p)
    n_p        : int        — número de tendones de pretensado
    phi_p0     : float      — diámetro inicial tendón [mm]
    fpy        : float      — tensión última del pretensado [MPa]
    Ae         : float      — excentricidad del pretensado [mm]
                             (distancia desde CDG sección al tendón)
    fck        : float      — resistencia característica hormigón [MPa]
    icorr      : float      — intensidad de corrosión [μA/cm²]
    alpha      : float      — factor de reducción de diámetro
                             (carbonatación ≈ 2, cloruros ≈ 10)
    v_ed       : float      — cortante de cálculo aplicado [kN]  (puede ser 0)
    m_ed       : float      — momento de cálculo aplicado [kNm]  (puede ser 0)
    gamma_v    : float      — coeficiente parcial del cortante (default 1.4)
    gamma_c    : float      — coeficiente parcial del hormigón (default 1.5)
    d_lower    : float      — diámetro barra inferior armadura pasiva [mm]
                             (para cálculo ddg = 16 + d_lower)

Salida: lista de dicts con campos:
    t          : tiempo [años]
    px         : penetración de corrosión [mm]
    ap_t       : área de pretensado residual [mm²]
    n_kn       : fuerza de pretensado residual [kN]
    sigma_cp   : tensión media de compresión [MPa]
    rho_l      : cuantía longitudinal residual [-]
    tau_c0     : τRd,c0  [MPa]
    tau_scp    : τRd,σcp [MPa]
    tau_cmin   : τRd,c_min [MPa]
    tau_cmax   : τRd,c_max [MPa]
    tau_total  : min(τRd,c0+σcp , τRd,cmax) [MPa]
    vrd        : VRd [kN]
"""

import math
import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

def calcular_cortante_pretensado(params: dict) -> list[dict]:
    """
    Calcula la evolución temporal de VRd para una viga pretensada
    con degradación por corrosión según EC2:2023.

    Ver cabecera del módulo para descripción completa de parámetros.
    """

    # ── Extraer parámetros ────────────────────────────────────────────────────
    t_global  = float(params.get('t_global', 250))
    t_ini     = float(params.get('t_ini', 0.0))
    h         = float(params.get('h', 300))          # mm
    bw        = float(params.get('bw', 150))          # mm
    c_bot     = float(params.get('c_bot', 50))        # mm  recubrimiento inferior
    n_p       = int(params.get('n_p', 2))             # nº tendones
    phi_p0    = float(params.get('phi_p0', 14.0))     # mm  diámetro inicial
    fpy       = float(params.get('fpy', 1860))        # MPa
    ae        = float(params.get('Ae', 92.0))         # mm  excentricidad
    fck       = float(params.get('fck', 25))          # MPa
    icorr     = float(params.get('icorr', 0.5))       # μA/cm²
    alpha     = float(params.get('alpha', 2.0))       # factor corrosión
    v_ed      = float(params.get('v_ed', 0.0))        # kN
    m_ed      = float(params.get('m_ed', 0.0))        # kNm
    gamma_v   = float(params.get('gamma_v', 1.4))
    d_lower   = float(params.get('d_lower', 12.0))    # mm

    # ── Geometría derivada ────────────────────────────────────────────────────
    # Canto útil del pretensado: dp = h - c_bot (centroide tendón)
    dp        = h - c_bot                             # mm
    # Área inicial total de pretensado (n_p tendones circulares)
    ap0       = n_p * math.pi * phi_p0**2 / 4        # mm²
    # Sección bruta
    ag        = bw * h                                # mm²
    # Diámetro máximo del árido (EC2 simplificado)
    ddg       = 16.0 + d_lower                        # mm
    # Cuantía longitudinal inicial
    rho_l0    = ap0 / (bw * dp)

    results = []

    times = np.arange(0, t_global + 1, 1)

    for t in times:
        t_corr = max(0.0, t - t_ini)

        # ── Penetración de corrosión ──────────────────────────────────────────
        px = 0.0116 * icorr * t_corr                 # mm

        # ── Diámetro y área residual del pretensado ───────────────────────────
        phi_p_t = max(0.0, phi_p0 - alpha * px)
        ap_t    = n_p * math.pi * phi_p_t**2 / 4    # mm²

        # ── Fuerza de pretensado residual: N = 0.5·Ap·fpy  [kN] ─────────────
        n_kn    = 0.5 * ap_t * fpy / 1000.0          # kN

        # ── Tensión media de compresión en la sección ─────────────────────────
        # σ_cp = N / Ag   (N en N, Ag en mm²) → MPa
        sigma_cp = (n_kn * 1000.0) / ag              # MPa

        # ── Cuantía longitudinal residual ─────────────────────────────────────
        rho_l_t = rho_l0 * (ap_t / ap0) if ap0 > 0 else 0.0

        # ── Brazo mecánico de la corte ────────────────────────────────────────
        # acs_0 = max(Med/VEd , dp/1000)  [m]
        dp_m = dp / 1000.0                           # m
        if v_ed > 0:
            acs_0 = max(m_ed / v_ed, dp_m)
        else:
            acs_0 = dp_m

        # acs = max(acs_0 + ep·(N/VEd)·(1/1000) , dp/1000)  [m]
        # ep = excentricidad en mm, convertida a m dentro de la expresión
        if v_ed > 0:
            acs = max(acs_0 + (ae / 1000.0) * (n_kn / v_ed), dp_m)
        else:
            acs = acs_0

        # av = min( sqrt(dp·acs_0/4) , dp/1000 )  [m]
        av = min(math.sqrt(dp_m * acs_0 / 4.0), dp_m)
        av = max(av, 1e-9)                           # evitar división por cero

        # ── Componentes de la resistencia τRd ────────────────────────────────

        # τRd,c0 = (0.66/γv)·(100·ρl·fck·ddg / (av·1000))^(1/3)   [MPa]
        tau_c0 = (0.66 / gamma_v) * max(
            (100.0 * rho_l_t * fck * ddg / (av * 1000.0)), 0.0
        ) ** (1.0 / 3.0)

        # k1 = min( (0.5/(acs·1000))·(ep + dp/3)·(N/(bw·0.9·dp)) ,
        #           0.18·N/(bw·0.9·dp) )
        denom_k1 = bw * 0.9 * dp
        if denom_k1 > 0:
            k1 = min(
                (0.5 / (acs * 1000.0)) * (ae + dp / 3.0) * (n_kn * 1000.0 / denom_k1),
                0.18 * n_kn * 1000.0 / denom_k1
            )
        else:
            k1 = 0.0
        k1 = max(k1, 0.0)

        # τRd,σcp = k1 · σ_cp   [MPa]
        tau_scp = k1 * sigma_cp

        # τRd,c_min = (11/γv)·sqrt( (fck/(fpy-1310))·(ddg/dp) )   [MPa]
        inner = (fck / max(fpy - 1310.0, 1e-9)) * (ddg / dp)
        tau_cmin = (11.0 / gamma_v) * math.sqrt(max(inner, 0.0))

        # τRd,c_max = min( 2.15·τRd,c0·(acs·1000/dp)^(1/6) , 2.7·τRd,c0 )
        tau_cmax = min(
            2.15 * tau_c0 * max((acs * 1000.0) / dp, 1e-9) ** (1.0 / 6.0),
            2.7 * tau_c0
        )

        # Tensión resistente de cortante resultante
        tau_total = min(tau_c0 + tau_scp, tau_cmax)
        tau_total = max(tau_total, tau_cmin)         # límite inferior

        # VRd = τ_total · bw · 0.9 · dp / 1000   [kN]
        vrd = tau_total * bw * 0.9 * dp / 1000.0
        vrd = max(vrd, 0.0)

        results.append({
            't'        : float(t),
            'px'       : px,
            'ap_t'     : ap_t,
            'n_kn'     : n_kn,
            'sigma_cp' : sigma_cp,
            'rho_l'    : rho_l_t,
            'tau_c0'   : tau_c0,
            'tau_scp'  : tau_scp,
            'tau_cmin' : tau_cmin,
            'tau_cmax' : tau_cmax,
            'tau_total': tau_total,
            'vrd'      : vrd,
        })

    return results
