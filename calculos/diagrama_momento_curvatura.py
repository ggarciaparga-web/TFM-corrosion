import numpy as np
import math
import matplotlib.pyplot as plt

def calcular_mrd_corrosion(t_ana, b, h, rec_inf, n_inf, phi_inf_0, fyk, fck, i_corr, alpha, t_ini):
    """
    Calcula el Mrd final considerando la pérdida de sección por corrosión al tiempo t_ana.
    """
    # 1. Pérdida de sección (px) al tiempo t_ana
    t_corr = max(0, t_ana - t_ini)
    px = 0.0116 * i_corr * t_corr
    
    # 2. Diámetro y área residual
    phi_inf_t = max(phi_inf_0 - (alpha * px), 0)
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4
    
    # 3. Propiedades de materiales (Cálculo según normativa)
    fyd = fyk / 1.15
    fcd = fck / 1.5
    nfc = min(1.0, (30/fck)**(1/3))
    kc = 0.75 * nfc
    fcd_red = kc * fcd
    d = h - rec_inf - (phi_inf_0 / 2)
    
    # 4. Cálculo del Momento Resistente (Mrd)
    if phi_inf_t <= 0:
        return 0.0, 0.0, 0.0
    
    x = (as_inf_t * fyd) / (0.8 * b * fcd_red) # Prof. bloque de compresiones
    z = d - 0.4 * x                           # Brazo mecánico
    mrd = (as_inf_t * fyd * z) / 1e6          # Convertir a kNm
    
    # Curvatura en rotura (Aproximación mecánica: εcu / x)
    # x_real = x / 0.8 (profundidad fibra neutra real)
    curvatura_rotura = 0.0035 / (x / 0.8) if x > 0 else 0
    
    return mrd, curvatura_rotura, as_inf_t

def generar_diagrama_mc():
    # --- Parámetros de Diseño (del documento diseño-pagina-web) ---
    b = 300 
    h = 150 
    r1 = 50  # recubrimiento inferior
    r2 = 50  # recubrimiento superior
    d = h - r1
    
    n1, phi1 = 2, 15 # Inferior (Tracción)
    n2, phi2 = 2, 15 # Superior (Compresión)
    
    Ec = 25000
    fct = 3.1
    ecy = 0.0035
    esy = 0.0021
    Es = 200000
    fyk = 500
    fck = 25
    
    # Parámetros Corrosión
    t_ana = 50      # años
    i_corr = 1.0    # uA/cm2
    alpha = 2.0
    t_ini = 5.0     # años
    
    # --- Cálculos Preliminares ---
    n = Es / Ec
    As1_0 = n1 * (math.pi * (phi1**2) / 4)
    As2 = n2 * (math.pi * (phi2**2) / 4)
    
    # Obtener Mrd con corrosión (Punto 4)
    mrd_val, curv_rotura, As1_t = calcular_mrd_corrosion(t_ana, b, h, r1, n1, phi1, fyk, fck, i_corr, alpha, t_ini)
    
    # --- Sección Homogeneizada (Punto 1) ---
    Ahormigon = b * h
    A1_h = n * As1_t
    A2_h = n * As2
    A_h = Ahormigon + A1_h + A2_h
    xgh = (1 / A_h) * ((Ahormigon * (h / 2)) + A1_h * d + A2_h * r2)
    I_h = ((1/12 * b * h**3) + Ahormigon * ((h/2) - xgh)**2 + A1_h * (d - xgh)**2 + A2_h * (r2 - xgh)**2)
    
    M_fis = (fct * I_h) / (h - xgh)
    p1 = (M_fis / (Ec * I_h)) * 1000 # Curvatura en 1/m
    
    # --- Sección Fisurada (Puntos 2 y 3) ---
    x_fis = (A1_h * d + A2_h * r2) / ((b / 2) + A1_h + A2_h) # Simplificación área traccionada despreciada
    I_fis = ((1/3 * b * x_fis**3) + A2_h * (x_fis - r2)**2 + A1_h * (d - x_fis)**2)
    p1_p = (M_fis / (Ec * I_fis)) * 1000
    
    # Punto 2 (Control de fluencia o agotamiento elástico hormigón)
    ec = ecy
    es1 = ec * (d - x_fis) / x_fis
    if abs(es1) <= esy:
        curv2 = ec / x_fis
    else:
        curv2 = esy / (d - x_fis)
    
    M2 = (curv2 * Ec * I_fis) / 1e6
    p2 = curv2 * 1000
    
    # Punto 3 (Plastificación avanzada)
    curv3 = 0.0035 / x_fis # Estado límite de deformación hormigón
    M3 = (curv3 * Ec * I_fis) / 1e6
    p3 = curv3 * 1000
    
    # Punto 4 (Agotamiento real Mrd)
    p4 = curv_rotura * 1000

    # --- Matriz y Gráfico ---
    matriz = np.array([
        [0, 0],
        [M_fis / 1e6, p1],
        [M_fis / 1e6, p1_p],
        [M2, p2],
        [M3, p3],
        [mrd_val, p4]
    ])
    
    plt.figure(figsize=(10,6))
    plt.plot(matriz[:,1], matriz[:,0], 'ro-', label='Diagrama M-Chi')
    plt.xlabel('Curvatura (1/m)')
    plt.ylabel('Momento (kNm)')
    plt.title(f'Diagrama Momento-Curvatura con Corrosión (t={t_ana} años)')
    plt.grid(True)
    plt.legend()
    plt.show()

    return matriz

if __name__ == "__main__":
    res = generar_diagrama_mc()
    print("Matriz [M(kNm), Curvatura(1/m)]:\n", res)
