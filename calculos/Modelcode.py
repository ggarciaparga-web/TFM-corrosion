import numpy as np

def calcular_capacidad_residual(t_ana, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                               fyk, fck, i_corr, alpha, t_ini_calculado):
    
    # Vector de tiempo
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    
    # 1. Penetración de la corrosión (px)
    tiempos_corrosion = np.maximum(0, tiempos - t_ini_calculado)
    px = 0.0116 * i_corr * tiempos_corrosion
    
    # 2. Actualización de diámetros (phi) - AMBOS como output
    phi_sup_t = np.maximum(phi_sup_0 - (alpha * px), 0)
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px), 0)
    
    # 3. Áreas para el cálculo interno de Mrd
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    
    # 4. Parámetros resistentes (Model Code)
    fyd = fyk / 1.15
    fcd = fck / 1.5
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    d = h - rec_inf - (phi_inf_0 / 2)
    
    mu_res = []
    
    for i in range(len(tiempos)):
        if phi_inf_t[i] <= 0:
            mu_res.append(0.0)
        else:
            # Cálculo de x (bloque de compresiones)
            x = (as_inf_t[i] * fyd) / (0.8 * b * fcd_red)
            z = d - 0.4 * x
            mu_res.append(max((as_inf_t[i] * fyd * z) / 1e6, 0))
    
    # --- MATRIZ DE SALIDA POR COLUMNAS ---
    # Columna 0: phi_inf_t (diámetro inferior residual)
    # Columna 1: mu_res (Momento resistente de diseño Mrd)
    # Columna 2: phi_sup_t (diámetro superior residual)
    
    matriz_salida = np.column_stack((
        phi_inf_t,         # Diámetro inferior
        np.array(mu_res),  # Mrd
        phi_sup_t          # Diámetro superior
    ))
    
    return matriz_salida
