import numpy as np
import pandas as pd

def calcular_mu_simple(a1, b_act, d_act, fyd_val, fck_val):
    fcd = fck_val / 1.5
    x = (a1 * fyd_val) / (0.8 * b_act * fcd)
    z = d_act - 0.4 * x
    mu = (a1 * fyd_val * z) / 1e6
    return max(mu, 0.0)

def calcular_contevect(t_ana, b_init, h, rec_sup, rec_inf, n_inf, phi_inf_0, 
                       fyk, fck, i_corr, alpha, t_ini):
    
    # Parámetros base
    fyd = fyk / 1.15
    fci = 0.333 * fck**(2/3)
    d_init = h - rec_inf - (phi_inf_0 / 2)
    phi_w0 = 0.0001 # Valor de estribos según tu ejemplo
    
    # 1. Simulación base de corrosión (solo ocurre tras t_ini)
    tiempos = np.arange(0, t_ana + 0.5, 0.5)
    rows = []
    for t in tiempos:
        # px solo aumenta después de t_ini
        t_corr = max(0, t - t_ini)
        px = 0.0116 * i_corr * t_corr
        p1 = max(0.0, phi_inf_0 - alpha * px)
        pw = max(0.0, phi_w0 - alpha * px)
        
        a1 = (np.pi * p1**2 / 4.0) * n_inf
        aw = (np.pi * pw**2 / 4.0)
        
        rows.append({
            "Tiempo": t, "Px": px, "A1": a1, "Aw": aw,
            "rho1": a1 / (b_init * d_init),
            "rho2": 0.001 # rho2 simplificado o según armado superior
        })
    
    df_base = pd.DataFrame(rows)

    # 2. Identificación de Puntos Críticos (Eventos)
    px0_threshold = max(0.0, (83.8 + 7.4 * (rec_inf / phi_inf_0) - 22.6 * fci) * 1e-3)
    
    points = []
    # Punto 0: Estado Inicial (t=0 hasta t=t_ini)
    p0 = df_base.iloc[0].copy()
    p0["b"], p0["d"] = b_init, d_init
    points.append(p0)

    # Punto 1: Inicio de fisuración (Px >= px0)
    idx_px0 = (df_base["Px"] >= px0_threshold).idxmax()
    p1 = df_base.loc[idx_px0].copy()
    p1["b"], p1["d"] = b_init, d_init
    points.append(p1)

    ev3, ev4 = None, None
    for _, row in df_base.iterrows():
        r1, r2, px, aw = row["rho1"]*100, row["rho2"]*100, row["Px"], row["Aw"]
        
        # Evento 4: Pérdida de ancho (b) y canto (d)
        if r1 > 1.5 and aw > (0.0036 * b_init) and px > 0.2 and ev4 is None:
            ev4 = row.copy()
            ev4["b"], ev4["d"] = b_init - 2.0 * rec_inf, d_init - rec_inf
            
        # Evento 3: Pérdida de recubrimiento (d)
        if ev3 is None:
            if (r1 < 1.0 and r2 < 5.0 and px > 0.4) or \
               (r1 < 1.0 and r2 > 5.0 and px > 0.2) or \
               (r1 > 1.5 and r2 > 0.5 and px > 0.2):
                ev3 = row.copy()
                ev3["b"], ev3["d"] = b_init, d_init - rec_inf

    if ev3 is not None: points.append(ev3)
    if ev4 is not None: points.append(ev4)

    df_critical = pd.DataFrame(points).sort_values("Tiempo").drop_duplicates("Px")
    df_critical["Mu"] = df_critical.apply(lambda r: calcular_mu_simple(r["A1"], r["b"], r["d"], fyd, fck), axis=1)

    # 3. Interpolación y Continuación
    # Generamos el vector final de tiempos
    t_final_v = np.arange(0, t_ana + 0.1, 0.1)
    mu_final = np.interp(t_final_v, df_critical["Tiempo"], df_critical["Mu"])
    
    # Para tiempos mayores al último punto crítico, calcular normalmente
    t_last_crit = df_critical["Tiempo"].max()
    b_last, d_last = df_critical.iloc[-1]["b"], df_critical.iloc[-1]["d"]
    
    mask_cont = t_final_v > t_last_crit
    for i in range(len(t_final_v)):
        if mask_cont[i]:
            t_curr = t_final_v[i]
            t_corr = max(0, t_curr - t_ini)
            px_curr = 0.0116 * i_corr * t_corr
            phi_curr = max(0.0, phi_inf_0 - alpha * px_curr)
            a1_curr = (np.pi * phi_curr**2 / 4.0) * n_inf
            mu_final[i] = calcular_mu_simple(a1_curr, b_last, d_last, fyd, fck)

    return t_final_v, df_critical, mu_final
