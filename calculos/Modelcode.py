import numpy as np

def calcular_capacidad_residual(t_ana, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                               fyk, fck, i_corr, alpha):
    
    # Tiempos de análisis (paso 0.1 años)
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    
    # Profundidad de corrosión px
    px = 0.0116 * i_corr * tiempos
    
    # Actualización de diámetros
    phi_sup_t = phi_sup_0 - (alpha * px)
    phi_inf_t = phi_inf_0 - (alpha * px)
    
    # Asegurar que el diámetro no sea negativo
    phi_sup_t = np.maximum(phi_sup_t, 0)
    phi_inf_t = np.maximum(phi_inf_t, 0)
    
    # Áreas de acero (en mm2)
    as_sup_0 = n_sup * (np.pi * phi_sup_0**2) / 4
    as_inf_0 = n_inf * (np.pi * phi_inf_0**2) / 4
    
    as_sup_t = n_sup * (np.pi * phi_sup_t**2) / 4
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    
    # Cálculo de m_corr (pérdida de masa/sección)
    m_corr_inf = (as_inf_0 - as_inf_t) / as_inf_0
    
    # Valores de diseño
    fyd = fyk / 1.15
    fcd = fck / 1.5
    
    # Reducción de fcd según Model Code (Approach 1)
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    
    # Canto útil d (asumiendo armadura inferior en tracción para momento positivo)
    d = h - rec_inf - (phi_inf_0 / 2)
    
    # Inicialización de vectores de momento
    mu_res = []
    mu_cons = []
    
    for i in range(len(tiempos)):
        if phi_inf_t[i] <= 0 or m_corr_inf[i] >= 1:
            mu_res.append(0.0)
            mu_cons.append(0.0)
        else:
            # Cálculo de x (fibra neutra) usando As_corroida inferior
            x = (as_inf_t[i] * fyd) / (0.8 * b * fcd_red)
            
            # Brazo de palanca z (Approach 1)
            z = d - 0.4 * x
            m_r = (as_inf_t[i] * fyd * z) / 1e6 # kNm
            mu_res.append(max(m_r, 0))
            
            # Brazo de palanca z_conservative (Approach 2)
            z_cons = d - rec_sup - 0.4 * x
            m_c = (as_inf_t[i] * fyd * z_cons) / 1e6 # kNm
            mu_cons.append(max(m_c, 0))
            
    return tiempos, px, phi_sup_t, phi_inf_t, np.array(mu_res), np.array(mu_cons)
