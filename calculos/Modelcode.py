import numpy as np

def calcular_capacidad_residual(t_ana, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                               fyk, fck, i_corr, alpha, t_ini_calculado):
    
    # Vector de tiempo (pasos de 0.1 años)
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    
    # 1. Penetración de la corrosión (px)
    tiempos_corrosion = np.maximum(0, tiempos - t_ini_calculado)
    px = 0.0116 * i_corr * tiempos_corrosion
    
    # 2. Actualización de diámetros (phi)
    phi_sup_t = np.maximum(phi_sup_0 - (alpha * px), 0)
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px), 0)
    
    # 3. Áreas de acero (mm2) para el cálculo de Mrd
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    as_sup_t = n_sup * (np.pi * phi_sup_t**2) / 4 # Área superior calculada igual que la inferior
    
    # 4. Parámetros para Mrd (Diseño)
    fyd = fyk / 1.15
    fcd = fck / 1.5
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    d = h - rec_inf - (phi_inf_0 / 2)
    
    mu_res = []
    
    for i in range(len(tiempos)):
        # Si se ha perdido la barra inferior, el momento es 0
        if phi_inf_t[i] <= 0:
            mu_res.append(0.0)
        else:
            # Cálculo de la profundidad del bloque de compresiones (x)
            x = (as_inf_t[i] * fyd) / (0.8 * b * fcd_red)
            z = d - 0.4 * x
            mu_res.append(max((as_inf_t[i] * fyd * z) / 1e6, 0))
    
    # --- CONSTRUCCIÓN DE LA MATRIZ SOLICITADA ---
    # Columnas: [phi_inf_t, mu_res, as_sup_t]
    # Nota: He incluido as_sup_t como el área, que es lo que suele usarse para el M-Chi
    
    matriz_final = np.column_stack((
        phi_inf_t,          # Columna 0: Diámetro inferior residual
        np.array(mu_res),   # Columna 1: Momento resistente de diseño
        as_sup_t            # Columna 2: Área superior residual (A2)
    ))
    
    return matriz_final
