import numpy as np

def calcular_capacidad_residual(t_ana, b_val, h_val, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                               fyk, fck, i_corr, alpha, t_ini):
    
    # Definición del paso de tiempo
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    
    # Penetración de la corrosión (solo después de t_ini)
    # px = 0.0116 * i_corr * t_corr
    tiempos_corrosion = np.maximum(0, tiempos - t_ini)
    px = 0.0116 * i_corr * tiempos_corrosion
    
    # Actualización de diámetros remanentes
    phi_sup_t = np.maximum(phi_sup_0 - (alpha * px), 0)
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px), 0)
    
    # Cálculo de Áreas de acero remanentes
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    
    # Parámetros de materiales según fib Model Code
    fyd = fyk / 1.15
    fcd = fck / 1.5
    
    # Factores de reducción para concreto (fib 2023 / Model Code)
    nfc = min(1.0, (30.0 / fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    
    # Canto útil inicial (distancia de fibra superior a centro de barras inf)
    d = h_val - rec_inf - (phi_inf_0 / 2)
    
    mu_res = []   # Model Code Estándar
    mu_cons = []  # Model Code Conservador (reducción extra por recubrimiento superior)
    
    for i in range(len(tiempos)):
        # Si la sección ha perdido su capacidad (barra desaparecida)
        if phi_inf_t[i] <= 0:
            mu_res.append(0.0)
            mu_cons.append(0.0)
        else:
            # Profundidad del eje neutro (bloque rectangular simplificado)
            x = (as_inf_t[i] * fyd) / (0.8 * b_val * fcd_red)
            
            # 1. Brazo de palanca Estándar (z = d - 0.4x)
            z_std = d - 0.4 * x
            
            # 2. Brazo de palanca Conservador (z_cons = d - rec_sup - 0.4x)
            # Nota: Esto simula una pérdida de sección en la fibra comprimida
            z_cons = d - rec_sup - 0.4 * x
            
            # Cálculo de momentos (convertido a kNm dividiendo por 1e6)
            m_std = (as_inf_t[i] * fyd * z_std) / 1e6
            m_cons = (as_inf_t[i] * fyd * np.maximum(0, z_cons)) / 1e6
            
            mu_res.append(max(m_std, 0))
            mu_cons.append(max(m_cons, 0))
            
    return tiempos, px, phi_inf_t, np.array(mu_res), np.array(mu_cons)
