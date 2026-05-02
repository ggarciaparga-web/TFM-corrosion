import numpy as np

def calcular_degradacion_cortante(params):
    """
    Motor de cálculo para el cortante según Model Code 2010 / MCFT
    Integrado con tiempo de iniciación y pretensado dinámico.
    """
    # 1. Parámetros de entrada del diccionario
    t_global = params['t_global']
    t_ini = params['t_ini']
    h = params['h']
    bw = params['bw']
    r1 = params['rec_inf'] # Sincronizado con tu rec_inf de la app
    phi1_initial = params['phi_inf_0']
    n_phi1 = params['n_inf']
    Ae = params['Ae']
    dg = params['dg']
    fck = params['fck']
    Es = params['Es']
    fpy = params['fpy']
    phi_p0 = params['phi_p0']
    n_p = params['n_p']
    Med = params['Med']
    Ved = params['Ved']
    icorr = params['icorr']
    alpha = params['alpha']

    # 2. Cálculos geométricos constantes
    d = h - r1 - (phi1_initial / 2.0)
    z = 0.9 * d
    kdg = min(0.75, 32.0 / (16.0 + dg))
    
    a_passive_initial = (np.pi * phi1_initial ** 2 / 4.0) * n_phi1
    a_active_initial = (np.pi * phi_p0 ** 2 / 4.0) * n_p

    tiempos = np.arange(0, t_global + 1)
    res_list = []

    for t in tiempos:
        # Lógica de iniciación: Px es 0 hasta t > t_ini
        if t <= t_ini:
            px = 0.0
        else:
            px = 0.0116 * icorr * (t - t_ini)

        # 3. Degradación de diámetros y áreas
        phi1_curr = max(0.0, phi1_initial - alpha * px)
        as_det = (np.pi * phi1_curr ** 2 / 4.0) * n_phi1

        phi_p_curr = max(0.0, phi_p0 - alpha * px)
        ap_det = (np.pi * phi_p_curr ** 2 / 4.0) * n_p

        # 4. Axil de Pretensado dinámico (Actualización Ned)
        ned_curr = -(ap_det * fpy)
        at_det = as_det + ap_det

        if at_det <= 0.01:
            res_list.append({"t": t, "vrdc": 0.0, "px": px, "ned": 0.0})
            continue

        # 5. Lógica de adherencia y MCFT
        current_kbond = 1.0 if px == 0 else 0.75
        
        # ex: Deformación longitudinal
        ex_num = (abs(Med) / z) + abs(Ved) + ned_curr * (0.5 + Ae / z)
        ex = (1.0 / (2.0 * Es * at_det)) * (1.0 / current_kbond) * ex_num
        ex = max(ex, 0)
        
        # kv y Vrd,c
        kv = (0.4 / (1.0 + 1500.0 * ex)) * (1300.0 / (1000.0 + kdg * z))
        vrdc_kn = (kv * (np.sqrt(fck) / 1.5) * z * bw) / 1000.0
        
        res_list.append({
            "t": t, 
            "vrdc": vrdc_kn, 
            "px": px, 
            "ned": ned_curr / 1000.0
        })
        
    return res_list
