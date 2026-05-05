import numpy as np
import math

def calcular_diagramas_desde_matriz(matriz_model_code, b, h, rec_sup, rec_inf, n_sup, n_inf, fyk, fck, Ec, fct, ecy, esy, Es):
    """
    matriz_model_code contiene: [phi_inf_t, mu_res, phi_sup_t]
    mu_res (columna 1) es el Mrd calculado con la lógica Model Code.
    """
    n_rel = Es / Ec
    # d basado en el diámetro inicial phi_inf_0 (primera fila, col 0)
    phi_inf_0 = matriz_model_code[0, 0]
    d_model_code = h - rec_inf - (phi_inf_0 / 2) 
    r2 = rec_sup + (phi_inf_0 / 2) 
    
    dict_diagramas = {}

    for i in range(len(matriz_model_code)):
        # --- DATOS DE ENTRADA DESDE TU MATRIZ ---
        phi_inf = matriz_model_code[i, 0]
        mrd_referencia = matriz_model_code[i, 1]  # Este es el Punto 4
        phi_sup = matriz_model_code[i, 2]
        
        # Áreas actuales según el tiempo i
        As1 = n_inf * (math.pi * (phi_inf**2) / 4)
        As2 = n_sup * (math.pi * (phi_sup**2) / 4)
        
        # Si no hay sección resistente, se devuelve matriz vacía para ese tiempo
        if phi_inf <= 0 or mrd_referencia <= 0:
            dict_diagramas[i] = np.zeros((6, 2))
            continue

        # --- SECCIÓN HOMOGENEIZADA (Punto 1) ---
        Ahormigon = b * h
        A1_homog = n_rel * As1
        A2_homog = n_rel * As2
        A_homog = Ahormigon + A1_homog + A2_homog

        xgh = (1 / A_homog) * ((Ahormigon * (h / 2)) + A1_homog * d_model_code + A2_homog * r2)
        I_homg = ( (1/12 * b * h**3) + Ahormigon * ( (h/2) - xgh )**2 + A1_homog * (d_model_code - xgh)**2 + A2_homog * (r2 - xgh)**2 )

        # --- SECCIÓN FISURADA (Puntos 2 y 3) ---
        x = (A1_homog * d_model_code + A2_homog * r2) / ((b / 2) + A1_homog + A2_homog)
        I_fisurada = ( (1/3 * b * x**3) + A2_homog * (x - r2)**2 + A1_homog * (d_model_code - x)**2 )

        # --- MOMENTOS Y CURVATURAS (Punto 1 y 1') ---
        M_fisurado = (fct * I_homg) / (h - xgh)
        punto1 = M_fisurado / (Ec * I_homg)
        punto1_prima = M_fisurado / (Ec * I_fisurada)

        # --- CÁLCULO DEL PUNTO 2 (Lógica de control) ---
        ec = ecy # Usamos ecy para el límite del hormigón
        es1 = ec * (d_model_code - x) / x
        es2 = ec * (x - r2) / x

        if abs(es1) <= esy and abs(es2) <= esy:
            punto2 = ec / x
            control = "HORMIGÓN"
        else:
            es1 = esy
            ec_p2 = es1 * x / (d_model_code - x)
            punto2 = es1 / (d_model_code - x)
            control = "ACERO INFERIOR"

        Mps = punto2 * Ec * I_fisurada

        # --- PUNTO 3 (Post-Plastificación con lógica completa) ---
        if control == "ACERO INFERIOR":
            p3 = ecy / x
        elif control == "HORMIGÓN":
            es1_check = ecy * (d_model_code - x) / x
            p3 = esy / (d_model_code - x) if abs(es1_check) >= esy else ecy / x
        else:
            p3 = ecy / x # Caso genérico por seguridad
        
        M3 = p3 * Ec * I_fisurada

        # --- PUNTO 4 (Sincronizado con Model Code) ---
        # Momento es exactamente el Mrd de la matriz
        M4 = mrd_referencia 
        
        # Curvatura punto 4: Cálculo de x_real para rotura (Model Code)
        # fcd_red = 0.75 * kc * fcd (con fck/1.5)
        fcd_red = (0.75 * min(1.0, (30/fck)**(1/3))) * (fck / 1.5)
        x_mrd = (As1 * (fyk / 1.15)) / (0.8 * b * fcd_red)
        
        # x_real = x_bloque / 0.8
        punto4 = (0.0035 / (x_mrd / 0.8)) if x_mrd > 0 else p3

        # --- MATRIZ FINAL (Conversión de unidades) ---
        # Momento: N*mm -> kNm (/1e6)
        # Curvatura: 1/mm -> 1/m (*1000)
        matriz_resultados = np.array([
            [0.0, 0.0],
            [M_fisurado / 1e6, punto1 * 1000],
            [M_fisurado / 1e6, punto1_prima * 1000],
            [Mps / 1e6,        punto2 * 1000],
            [M3 / 1e6,         p3 * 1000],
            [M4,               punto4 * 1000]
        ])
        
        dict_diagramas[i] = matriz_resultados

    return dict_diagramas
