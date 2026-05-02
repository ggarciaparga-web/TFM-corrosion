import math
import numpy as np

def calcular_tensiones_pretensado(params):
    # 1. Extracción de parámetros de la App
    t_global = params['t_global']
    t_ini = params['t_ini']
    h = params['h']
    b = params['bw']
    phi_p0 = params['phi_p0']
    n_p = params['n_p']
    fpy = params['fpy']
    ae_val = params['Ae']  # Excentricidad
    icorr = params['icorr']
    alpha = params['alpha']

    # 2. Propiedades de la sección de hormigón
    a_concrete = b * h
    i_beam = (b * h**3) / 12.0
    y_inferior = h / 2.0
    y_superior = h / 2.0

    # 3. Área inicial y Fuerza inicial P0
    a_prestress_0 = n_p * math.pi * phi_p0**2 / 4.0
    p0 = 0.75 * fpy * a_prestress_0  # Fuerza inicial (N)
    p_losses = 0.25 * p0             # Pérdidas (N)

    tiempos = np.arange(0, t_global + 1)
    rows = []

    for t in tiempos:
        # Lógica de iniciación: Px es 0 hasta t > t_ini
        t_corr = max(0, t - t_ini)
        px = 0.0116 * icorr * t_corr
        
        # Diámetro y área degradada
        phi_final = max(phi_p0 - alpha * px, 0.0)
        a_prestress_final = n_p * math.pi * phi_final**2 / 4.0
        
        # Factor de corrosión (mcorr)
        mcorr = 1.0 - (a_prestress_final / a_prestress_0)
        mcorr = max(0.0, min(1.0, mcorr))

        # --- CÁLCULO DE TENSIONES SEGÚN TU LÓGICA ---
        
        # Tensiones debidas a P0 (Transferencia)
        sigma_inf_p0 = (p0 / a_concrete + ((p0 * ae_val) * y_inferior) / i_beam)
        sigma_sup_p0 = (p0 / a_concrete - ((p0 * ae_val) * y_superior) / i_beam)

        # Tensiones debidas a las pérdidas
        # Nota: p_losses suele tener signo contrario o se suma/resta según criterio
        sigma_inf_loss = (p_losses / a_concrete + ((p_losses * ae_val) * y_inferior) / i_beam)
        sigma_sup_loss = (p_losses / a_concrete - ((p_losses * ae_val) * y_superior) / i_beam)

        # Tensiones efectivas antes de corrosión
        # Según tu código: sigma_inf_effective = p0 + pérdidas
        sigma_inf_effective = sigma_inf_p0 + sigma_inf_loss
        sigma_sup_effective = sigma_sup_p0 - sigma_sup_loss

        # Aplicación de la degradación por pérdida de sección (mcorr)
        sigma_inf_final = sigma_inf_effective * (1.0 - mcorr)
        sigma_sup_final = sigma_sup_effective * (1.0 - mcorr)

        rows.append({
            "t": t,
            "px": px,
            "mcorr": mcorr,
            "sigma_inferior": sigma_inf_final,
            "sigma_superior": sigma_sup_final
        })

    return rows
