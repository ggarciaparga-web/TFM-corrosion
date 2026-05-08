import numpy as np
import pandas as pd

def calcular_mu_simple(a1, b_act, d_act, fyd_val, fck_val):
    fcd = fck_val / 1.5
    x = (a1 * fyd_val) / (0.8 * b_act * fcd)
    z = d_act - 0.4 * x
    mu = (a1 * fyd_val * z) / 1e6
    return max(mu, 0.0)

def calcular_contevect(t_ana, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0, 
                       fyk, fck_val, i_corr, alpha, t_ini):
    
    # Parámetros base
    fyd = fyk_val / 1.15
    fci = 0.333 * fck**(2/3)
    d_init = h - rec_inf - (phi_inf_0 / 2)
    phi_w0 = 0.0001 
    a_init = (np.pi * phi_inf_0**2 / 4.0) * n_inf
    
    # 1. Simulación base de corrosión (solo tras t_ini)
    tiempos = np.arange(0, t_ana + 0.5, 0.5)
    rows = []
    for t in tiempos:
        t_corr = max(0, t - t_ini)
        px = 0.0116 * i_corr * t_corr
        p1 = max(0.0, phi_inf_0 - alpha * px)
        pw = max(0.0, phi_w0 - alpha * px)
        
        a1 = (np.pi * p1**2 / 4.0) * n_inf
        aw = (np.pi * pw**2 / 4.0)
        
        rows.append({
            "Tiempo": t, "Px": px, "A1": a1, "Aw": aw,
            "rho1": a1 / (b_val * d_init),
            "rho2": 0.001 
        })
    
    df_base = pd.DataFrame(rows)

    # 2. Identificación de Puntos Críticos (Eventos)
    px0_threshold = max(0.0, (83.8 + 7.4 * (rec_inf / phi_inf_0) - 22.6 * fci) * 1e-3)
    
    points = []
    
    # --- CORRECCIÓN AQUÍ ---
    # Punto Inicial de Degradación: t = t_ini (Px = 0, Geometría intacta)
    # Este punto debe ser el primero de la lista para que la interpolación sea constante antes
    p_ini = {
        "Tiempo": t_ini, "Px": 0.0, "A1": a_init, "Aw": (np.pi * phi_w0**2 / 4.0),
        "b": b_val, "d": d_init
    }
    points.append(p_ini)

    # Punto 1: Inicio de fisuración (Solo si px0_threshold > 0)
    idx_px0 = (df_base["Px"] >= px0_threshold).idxmax()
    if df_base.loc[idx_px0, "Px"] > 0:
        p1 = df_base.loc[idx_px0].copy()
        p1["b"], p1["d"] = b_init, d_init
        points.append(p1)

    ev3, ev4 = None, None
    for _, row in df_base.iterrows():
        r1, r2, px, aw = row["rho1"]*100, row["rho2"]*100, row["Px"], row["Aw"]
        
        if r1 > 1.5 and aw > (0.0036 * b_val) and px > 0.2 and ev4 is None:
            ev4 = row.copy()
            ev4["b"], ev4["d"] = b_init - 2.0 * rec_inf, d_init - rec_inf
            
        if ev3 is None:
            if (r1 < 1.0 and r2 < 5.0 and px > 0.4) or \
               (r1 < 1.0 and r2 > 5.0 and px > 0.2) or \
               (r1 > 1.5 and r2 > 0.5 and px > 0.2):
                ev3 = row.copy()
                ev3["b"], ev3["d"] = b_init, d_init - rec_inf

    if ev3 is not None: points.append(ev3)
    if ev4 is not None: points.append(ev4)

    df_critical = pd.DataFrame(points).sort_values("Tiempo").drop_duplicates("Tiempo")
    df_critical["Mu"] = df_critical.apply(lambda r: calcular_mu_simple(r["A1"], r["b"], r["d"], fyd, fck), axis=1)

    # 3. Generación del vector final con tramo constante inicial
    t_final_v = np.arange(0, t_ana + 0.1, 0.1)
    
    # np.interp usará el valor de t_ini para todo t < t_ini si t_ini es el primer punto
    mu_final = np.interp(t_final_v, df_critical["Tiempo"], df_critical["Mu"])
    
    # Continuación tras el último punto crítico
    t_last_crit = df_critical["Tiempo"].max()
    b_last, d_last = df_critical.iloc[-1]["b"], df_critical.iloc[-1]["d"]
    
    mask_cont = t_final_v > t_last_crit
    for i in range(len(t_final_v)):
        if mask_cont[i]:
            t_curr = t_final_v[i]
            t_corr = t_curr - t_ini
            px_curr = 0.0116 * i_corr * t_corr
            phi_curr = max(0.0, phi_inf_0 - alpha * px_curr)
            a1_curr = (np.pi * phi_curr**2 / 4.0) * n_inf
            mu_final[i] = calcular_mu_simple(a1_curr, b_last, d_last, fyd, fck)

    return t_final_v, df_critical, mu_final
