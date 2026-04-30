import numpy as np

def calcular_contevect(t_ana, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
                       fyk, fck, i_corr, alpha, t_ini_calculado):
    
    tiempos = np.arange(0, t_ana + 0.1, 0.1)
    tiempos_corr = np.maximum(0, tiempos - t_ini_calculado)
    
    # Constantes de material
    fyd = fyk / 1.15
    fcd = fck / 1.5
    fctm = 0.3 * (fck**(2/3)) # fctm aproximado
    
    # 1. Punto Inicial (t=0 después de t_ini)
    d_nominal = h - rec_inf - (phi_inf_0 / 2)
    as_inf_0 = n_inf * (np.pi * phi_inf_0**2) / 4
    x0 = (as_inf_0 * fyd) / (0.8 * b * fcd)
    z0 = d_nominal - 0.4 * x0
    m0 = (as_inf_0 * fyd * z0) / 1e6

    # 2. Definición de px en el tiempo
    px_v = 0.0116 * i_corr * tiempos_corr
    phi_inf_t = np.maximum(phi_inf_0 - (alpha * px_v), 0)
    as_inf_t = n_inf * (np.pi * phi_inf_t**2) / 4

    # 3. Cálculo de puntos críticos
    # Punto 1: Inicio de fisuración/degradación
    px_1 = (83.8 + 7.4 * (rec_inf / phi_inf_0) - 22.6 * fctm) * 1e-3
    px_1 = max(px_1, 0.001) # Evitar valores negativos

    # Punto 2: Pérdida de recubrimiento (Spalling)
    # Ratios para condiciones
    r1 = rec_inf / phi_inf_0
    r2 = b / (n_inf * phi_inf_0) # Aproximación de espaciamiento relativo

    mu_vect = []
    
    for i in range(len(tiempos)):
        px = px_v[i]
        d_actual = d_nominal
        
        # Comprobar condiciones de pérdida de recubrimiento (Punto 2)
        cond1 = (r1 < 1.0 and r2 < 5.0 and px > 0.4)
        cond2 = (r1 < 1.0 and r2 > 5.0 and px > 0.2)
        cond3 = (r1 > 1.5 and r2 > 0.5 and px > 0.2)
        
        if cond1 or cond2 or cond3:
            # Reducción del canto útil por pérdida de hormigón
            d_actual = d_nominal - rec_inf
        
        if as_inf_t[i] <= 0:
            mu_vect.append(0.0)
        else:
            x = (as_inf_t[i] * fyd) / (0.8 * b * fcd)
            # Si d_actual ha cambiado, z se calcula sobre el nuevo d
            z = d_actual - 0.4 * x
            m_r = (as_inf_t[i] * fyd * z) / 1e6
            mu_vect.append(max(m_r, 0))

    return tiempos, px_v, np.array(mu_vect)
