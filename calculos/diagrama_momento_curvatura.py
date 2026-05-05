import numpy as np
import math

def calcular_capacidad_y_diagramas(t_ana, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                                  fyk, fck, i_corr, alpha, t_ini_calculado, Ec, fct, ecy, esy, Es):
    
    # 1. Preparación de tiempos y constantes
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    n = Es / Ec
    # d basado en el diámetro inicial (phi_inf_0) según tu definición de Model Code
    d_model_code = h - rec_inf - (phi_inf_0 / 2) 
    r2 = rec_sup + (phi_sup_0 / 2)
    
    # 2. Corrosión temporal
    tiempos_corrosion = np.maximum(0, tiempos - t_ini_calculado)
    px = 0.0116 * i_corr * tiempos_corrosion
    phi_sup_t = np.maximum(phi_sup_0 - (alpha * px), 0)
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px), 0)
    
    # --- PARÁMETROS MODEL CODE (Para el Punto 4) ---
    # Usamos fyk y fck directamente (sin dividir por 1.15 o 1.5)
    fyd_mc = fyk 
    fcd_mc = fck 
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red_mc = kc * fcd_mc
    
    dict_diagramas = {}

    for i in range(len(tiempos)):
        # Áreas actuales según corrosión en el tiempo t
        As1 = n_inf * (math.pi * (phi_inf_t[i]**2) / 4)
        As2 = n_sup * (math.pi * (phi_sup_t[i]**2) / 4)
        
        if phi_inf_t[i] <= 0:
            dict_diagramas[round(tiempos[i], 2)] = np.zeros((6, 2))
            continue

        # --- SECCIÓN HOMOGENEIZADA (Puntos 1) ---
        Ah = b * h
        A1_h, A2_h = n * As1, n * As2
        Atot = Ah + A1_h + A2_h
        xgh = (1 / Atot) * ((Ah * h / 2) + A1_h * d_model_code + A2_h * r2)
        I_homg = ( (1/12 * b * h**3) + Ah * (h/2 - xgh)**2 + A1_h * (d_model_code - xgh)**2 + A2_h * (r2 - xgh)**2 )

        # --- SECCIÓN FISURADA (Puntos 1', 2, 3) ---
        x = (A1_h * d_model_code + A2_h * r2) / ((b / 2) + A1_h + A2_h)
        I_fisurada = ( (1/3 * b * x**3) + A2_h * (x - r2)**2 + A1_h * (d_model_code - x)**2 )

        # Punto 1 y 1'
        M_fis = (fct * I_homg) / (h - xgh)
        p1 = M_fis / (Ec * I_homg)
        p1_p = M_fis / (Ec * I_fisurada)

        # --- CÁLCULO DEL PUNTO 2 (Tu lógica de control original) ---
        ec = ecy
        es1 = ec * (d_model_code - x) / x
        es2 = ec * (x - r2) / x

        if abs(es1) <= esy and abs(es2) <= esy:
            p2 = ec / x
            control = "HORMIGÓN"
        else:
            es1 = esy
            ec = es1 * x / (d_model_code - x)
            p2 = es1 / (d_model_code - x)
            control = "ACERO INFERIOR"
        
        Mps = p2 * Ec * I_fisurada

        # --- PUNTO 3 (Post-Plastificación) ---
        if control == "ACERO INFERIOR":
            p3 = ecy / x
        elif control == "HORMIGÓN":
            es1_check = ecy * (d_model_code - x) / x
            p3 = esy / (d_model_code - x) if abs(es1_check) >= esy else ecy / x
        else:
            p3 = ecy / x # Caso genérico
        
        M3 = p3 * Ec * I_fisurada

        # --- PUNTO 4 (Lógica Model Code Solicitada) ---
        # Usando las variables fyd_mc y fcd_red_mc definidas arriba
        x_mrd = (As1 * fyd_mc) / (0.8 * b * fcd_red_mc)
        z_mrd = d_model_code - 0.4 * x_mrd
        
        Mrd = max((As1 * fyd_mc * z_mrd), 0)
        # Curvatura de rotura: εcu / x_real (donde x_real = x_bloque / 0.8)
        p4 = 0.0035 / (x_mrd / 0.8) if x_mrd > 0 else p3

        # --- MATRIZ FINAL (Momento en kNm, Curvatura en 1/m) ---
        matriz_resultados = np.array([
            [0.0, 0.0],
            [M_fis / 1e6, p1 * 1000],
            [M_fis / 1e6, p1_p * 1000],
            [Mps / 1e6,   p2 * 1000],
            [M3 / 1e6,    p3 * 1000],
            [Mrd / 1e6,   p4 * 1000]
        ])
        
        dict_diagramas[round(tiempos[i], 2)] = matriz_resultados

    return dict_diagramas
