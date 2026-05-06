import numpy as np

def calcular_capacidad_residual(t_ana, b_val, h_val, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                               fyk, fck, i_corr, alpha, t_ini_calculado):
    
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    
    # px solo crece después de t_ini
    # px = 0.0116 * i_corr * (t - t_ini) si t > t_ini, de lo contrario 0
    tiempos_corrosion = np.maximum(0, tiempos - t_ini_calculado)
    px = 0.0116 * i_corr * tiempos_corrosion
    
    # Actualización de diámetros
    phi_sup_t = np.maximum(phi_sup_0 - (alpha * px), 0)
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px), 0)
    
    # Áreas
    as_inf_0 = n_inf * (np.pi * phi_inf_0**2) / 4
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    
    fyd = fyk / 1.15
    fcd = fck / 1.5
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    d = h - rec_inf - (phi_inf_0 / 2)
    
    mu_res = []
    mu_cons = []
    
    for i in range(len(tiempos)):
        # Si no hay corrosión aún (t < t_ini), momento es el inicial
        # Si se ha perdido la barra, momento es 0
        if phi_inf_t[i] <= 0:
            mu_res.append(0.0)
            mu_cons.append(0.0)
        else:
            x = (as_inf_t[i] * fyd) / (0.8 * b * fcd_red)
            z = d - 0.4 * x
            z_cons = d - rec_sup - 0.4 * x
            
            mu_res.append(max((as_inf_t[i] * fyd * z) / 1e6, 0))
            mu_cons.append(max((as_inf_t[i] * fyd * z_cons) / 1e6, 0))
            
    return tiempos, px, phi_inf_t, np.array(mu_res), np.array(mu_cons)
