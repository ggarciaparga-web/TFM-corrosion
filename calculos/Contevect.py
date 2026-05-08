import numpy as np
import pandas as pd

def calcular_mu_simple(a1, b_act, d_act, fyd_val, fck_val):
    fcd = fck_val / 1.5
    # Cálculo simplificado de la profundidad del bloque de compresión (x) y brazo mecánico (z)
    x = (a1 * fyd_val) / (0.8 * b_act * fcd)
    z = d_act - 0.4 * x
    mu = (a1 * fyd_val * z) / 1e6 # Resultado en kNm
    return max(mu, 0.0)

def calcular_contevect(t_ana, b_val, h_val, rec_sup, rec_inf, n_inf, phi_inf_0, 
                       fyk, fck_val, i_corr, alpha, t_ini):
    
    # --- 1. PARÁMETROS BASE ---
    fyd = fyk / 1.15
    fci = 0.333 * fck_val**(2/3) # Resistencia a tracción para fisuración
    d_init = h_val - rec_inf - (phi_inf_0 / 2) # Canto útil inicial
    phi_w0 = 0.0001 # Diámetro despreciable para armadura de piel/web
    a_init = (np.pi * phi_inf_0**2 / 4.0) * n_inf # Área inicial armadura inferior
    
    # Simulación base de penetración de corrosión
    tiempos = np.arange(0, t_ana + 0.5, 0.5)
    rows = []
    for t in tiempos:
        t_corr = max(0, t - t_ini) # Solo hay corrosión si t > t_ini
        px = 0.0116 * i_corr * t_corr
        p1 = max(0.0, phi_inf_0 - alpha * px)
        
        a1 = (np.pi * p1**2 / 4.0) * n_inf
        
        rows.append({
            "Tiempo": t, "Px": px, "A1": a1,
            "rho1": a1 / (b_val * d_init),
            "rho2": 0.001 # Valor auxiliar para lógica de eventos
        })
    
    df_base = pd.DataFrame(rows)

    # --- 2. IDENTIFICACIÓN DE EVENTOS CRÍTICOS ---
    # Umbral de penetración para fisuración del recubrimiento (Modelo Molina et al.)
    px0_threshold = max(0.0, (83.8 + 7.4 * (rec_inf / phi_inf_0) - 22.6 * fci) * 1e-3)
    
    points = []
    
    # Evento 0: Punto Inicial (t = t_ini, capacidad intacta)
    p_ini = {
        "Tiempo": t_ini, "Px": 0.0, "A1": a_init,
        "b": b_val, "d": d_init
    }
    points.append(p_ini)

    # Evento 1: Inicio de fisuración
    idx_px0 = (df_base["Px"] >= px0_threshold).idxmax()
    if df_base.loc[idx_px0, "Px"] > 0:
        p1_ev = df_base.loc[idx_px0].copy()
        p1_ev["b"], p1_ev["d"] = b_val, d_init
        points.append(p1_ev)

    # Eventos de degradación geométrica (Spalling / Desprendimiento)
    ev3, ev4 = None, None
    for _, row in df_base.iterrows():
        r1, px = row["rho1"]*100, row["Px"]
        
        # Lógica simplificada de pérdida de sección de hormigón
        if r1 > 1.5 and px > 0.2 and ev4 is None:
            ev4 = row.copy()
            ev4["b"], ev4["d"] = b_val - 2.0 * rec_inf, d_init - (rec_inf/2)
            
        if ev3 is None and px > 0.4:
            ev3 = row.copy()
            ev3["b"], ev3["d"] = b_val, d_init - (rec_inf/2)

    if ev3 is not None: points.append(ev3)
    if ev4 is not None: points.append(ev4)

    # Crear DataFrame de puntos críticos y calcular su Momento Último
    df_critical = pd.DataFrame(points).sort_values("Tiempo").drop_duplicates("Tiempo")
    df_critical["Mu"] = df_critical.apply(lambda r: calcular_mu_simple(r["A1"], r["b"], r["d"], fyd, fck_val), axis=1)

    # --- 3. GENERACIÓN DEL VECTOR FINAL (INTERPOLACIÓN) ---
    t_final_v = np.arange(0, t_ana + 0.1, 0.1)
    
    # La capacidad es constante hasta t_ini
    mu_final = np.interp(t_final_v, df_critical["Tiempo"], df_critical["Mu"])
    
    # Para tiempos posteriores al último evento calculado, seguimos degradando el acero
    t_last_crit = df_critical["Tiempo"].max()
    b_last = df_critical.iloc[-1]["b"]
    d_last = df_critical.iloc[-1]["d"]
    
    mask_cont = t_final_v > t_last_crit
    for i in range(len(t_final_v)):
        if mask_cont[i]:
            t_curr = t_final_v[i]
            t_corr = t_curr - t_ini
            px_curr = 0.0116 * i_corr * t_corr
            phi_curr = max(0.0, phi_inf_0 - alpha * px_curr)
            a1_curr = (np.pi * phi_curr**2 / 4.0) * n_inf
            mu_final[i] = calcular_mu_simple(a1_curr, b_last, d_last, fyd, fck_val)

    return t_final_v, df_critical, mu_final
