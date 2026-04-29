import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
# Importamos desde la carpeta calculos
from calculos import tiempoiniciacion as calc

# --- CONFIGURACIÓN DE PÁGINA ESTILO ETH ---
st.set_page_config(page_title="Concrete Durability Tool | ETH Style", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main { background-color: #ffffff; }
    h1 { color: #000000; font-weight: 700; border-bottom: 2px solid #e17000; padding-bottom: 10px; }
    h3 { color: #444; margin-top: 20px; border-left: 5px solid #e17000; padding-left: 10px; }
    /* Estilo para los contenedores de inputs */
    .stNumberInput, .stSlider { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("Calculadora de Durabilidad del Hormigón")

# --- SELECCIÓN DE MODELO (En el cuerpo principal) ---
tipo_ataque = st.radio("Seleccione el fenómeno a analizar:", ["Carbonatación", "Cloruros"], horizontal=True)

if tipo_ataque == "Carbonatación":
    st.subheader("Parámetros de Entrada - Carbonatación")
    
    # ORGANIZACIÓN DE INPUTS EN COLUMNAS (Sin sidebar)
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        d_mm = st.number_input("Recubrimiento $c$ [mm]", value=30.0)
        t_ana = st.number_input("Tiempo análisis [años]", value=100)
    
    with c2:
        rh_real = st.slider("Humedad $RH_{real}$ [%]", 0, 100, 50)
        rh_ref = st.number_input("$RH_{ref}$ [%]", value=65.0)
    
    with c3:
        dias_ll = st.number_input("Días de lluvia/año", value=50)
        psr = st.number_input("Prob. lluvia $p_{sR}$", value=0.1)
    
    with c4:
        racc = st.number_input("$R_{acc}$ [mm²/año/kg/m³]", value=4541.32)
        csd = st.number_input("$C_{s,d}$ [kg/m³]", value=0.00082)

    # Parámetros secundarios (puedes moverlos a columnas si quieres)
    kcd, kt, ge, fe, bw, t0 = 0.67, 1.25, 2.5, 5.0, 0.446, 0.0767

    # LLAMADA AL CÁLCULO
    t, w, xcd, t_ini = calc.calcular_carbonatacion(d_mm, rh_real, rh_ref, ge, fe, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_ana)

    # --- RESULTADOS Y GRÁFICO ---
    st.divider()
    res1, res2 = st.columns([1, 2])
    
    with res1:
        st.write("### Resultados")
        if t_ini:
            st.metric("Tiempo de Iniciación", f"{t_ini:.2f} años")
            st.info(f"El frente de carbonatación alcanza los {d_mm} mm a los {t_ini:.2f} años.")
        else:
            st.error(f"No se alcanza la armadura en {t_ana} años.")
        
        st.write("**Matriz de datos (primeros 10 años):**")
        df = pd.DataFrame({"Año": t, "W(t)": w, "Xcd [mm]": xcd})
        st.dataframe(df.head(100), height=300)

    with res2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=xcd, fill='tozeroy', name='Profundidad Xcd',
                                 line=dict(color='#e17000', width=3), fillcolor='rgba(225, 112, 0, 0.1)'))
        fig.add_trace(go.Scatter(x=t, y=[d_mm]*len(t), name='Recubrimiento',
                                 line=dict(color='black', width=2, dash='dash')))
        fig.update_layout(title="Evolución de la profundidad de carbonatación",
                          plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Profundidad [mm]")
        st.plotly_chart(fig, use_container_width=True)

elif tipo_ataque == "Cloruros":
    st.subheader("Parámetros de Entrada - Cloruros")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        d_mm = st.number_input("Recubrimiento $c$ [mm]", value=40.0)
        t_ana = st.number_input("Tiempo análisis [años]", value=100)
    
    with c2:
        c0 = st.number_input("$C_0$ [%]", value=0.1)
        cs = st.number_input("$C_s$ [%]", value=2.0)
        ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
    
    with c3:
        treal = st.number_input("$T_{real}$ [K]", value=289.6)
        tref = st.number_input("$T_{ref}$ [K]", value=293.0)
        be = st.number_input("$b_e$", value=4800.0)
    
    with c4:
        dcrm = st.number_input("$D_{crm}$ [mm²/año]", value=224.53)
        a_age = st.number_input("Factor edad $a$", value=0.4288)

    # Llamada al cálculo
    t, dapp, z, conc, t_ini = calc.calcular_cloruros(d_mm, c0, cs, ccrit, be, tref, treal, 1.0, 0.0767, a_age, dcrm, t_ana)

    # --- RESULTADOS Y GRÁFICO ---
    st.divider()
    res1, res2 = st.columns([1, 2])
    
    with res1:
        st.write("### Resultados")
        if t_ini:
            st.metric("Tiempo de Iniciación", f"{t_ini:.2f} años")
        else:
            st.error(f"La concentración crítica no se alcanza en {t_ana} años.")
        
        df = pd.DataFrame({"Año": t, "Dapp": dapp, "Z": z, "C(t) [%]": conc})
        st.dataframe(df.head(100), height=300)

    with res2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=conc, fill='tozeroy', name='Concentración Cl-',
                                 line=dict(color='#e17000', width=3), fillcolor='rgba(225, 112, 0, 0.1)'))
        fig.add_trace(go.Scatter(x=t, y=[ccrit]*len(t), name='C Crítica',
                                 line=dict(color='black', width=2, dash='dash')))
        fig.update_layout(title="Concentración de cloruros en la armadura",
                          plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="C [% peso cem]")
        st.plotly_chart(fig, use_container_width=True)
