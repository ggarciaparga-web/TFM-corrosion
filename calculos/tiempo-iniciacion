import numpy as np
from scipy.special import erf

def calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_lluvia, bw, t0, t_final):
    tiempos = np.arange(0.1, t_final + 0.1, 0.1)  # Paso de 0.1 años
    tow = dias_lluvia / 365
    
    # Coeficiente Ked
    ked = ((1 - (rh_real/100)**fe) / (1 - (rh_ref/100)**fe))**ge
    
    # Función W(t) y Xcd(t)
    w_t = (t0 / tiempos)**(((psr * tow)**bw) / 2)
    # Raíz(2 * kcd * ked * kt * racc * csd) * W(t) * Raíz(t)
    factor_raiz = np.sqrt(2 * kcd * ked * kt * racc * csd)
    xcd_t = factor_raiz * w_t * np.sqrt(tiempos)
    
    # Tiempo de iniciación: primer tiempo donde xcd_t >= d_mm
    idx = np.where(xcd_t >= d_mm)[0]
    t_ini = tiempos[idx[0]] if len(idx) > 0 else None
    
    return tiempos, w_t, xcd_t, t_ini

def calcular_cloruros(d_mm, c0, cs, ccrit, be, tref, treal, kt, t0, a, dcrm, t_final):
    tiempos = np.arange(0.1, t_final + 0.1, 0.1)
    
    ke = np.exp(be * (1/tref - 1/treal))
    at = (t0 / tiempos)**a
    d_app = ke * dcrm * kt * at
    
    # Z = recubrimiento / (2 * raiz(Dapp * t))
    z = d_mm / (2 * np.sqrt(d_app * tiempos))
    
    # C = c0 + (cs - c0) * (1 - erf(z))
    concentracion = c0 + (cs - c0) * (1 - erf(z))
    
    # Tiempo de iniciación: primer tiempo donde concentracion >= ccrit
    idx = np.where(concentracion >= ccrit)[0]
    t_ini = tiempos[idx[0]] if len(idx) > 0 else None
    
    return tiempos, d_app, z, concentracion, t_ini
  
