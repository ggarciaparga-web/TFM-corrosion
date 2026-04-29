import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import calculations as calc

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO ETH ---
st.set_page_config(page_title="Concrete Durability App | ETH Style", layout="wide")

st.markdown("""
    <style>
    /* Tipografía y colores base */
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333;
    }
    .main {
        background-color: #ffffff;
    }
    /* Estilo para los headers */
    h1, h2, h3 {
        color: #000000;
        font-weight: 400 !important;
        border-bottom: 1px solid #eeeeee;
        padding-bottom: 10px;
    }
    /* Sidebar con estilo gris ETH */
    .css-1d391kg {
        background-color: #f5f5f5;
    }
    /* Botones y Sliders (Aproximación de color naranja ETH) */
    .stSlider > div > div > div > div {
        background-color: #e17000;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (CONTROLES) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/ETH_Logo.svg/1200px-ETH_Logo.svg.png", width=150) # Opcional: logo
st.sidebar.title("Parámetros de Entrada")

tipo_ataque = st.sidebar.radio("Tipo de Análisis", ["Carbonatación", "Cloruros"])

# --- LÓGICA DE INTERFAZ ---
if tipo_ataque == "Carbonatación":
    st.title("Ataque por Carbonatación")
    
    col_input, col_plot = st.columns([1, 2])
    
    with col_input:
        st.subheader("Variables")
        d_mm = st.slider("Recubrimiento $c$ [mm]", 10, 100, 30)
        rh_real = st.slider("Humedad $RH_{real}$ [%]", 0, 100, 50)
        dias_ll = st.number_input("Días de lluvia", value=50)
        t_ana = st.number_input("Tiempo de análisis [años]", value=100)
        
        # Parámetros fijos (pueden ser sliders también)
        kcd, kt, csd, racc = 0.67, 1.25, 0.00082, 4541.324
        psr, bw, t0 = 0.1, 0.446, 0.0767

    # Cálculos
    t, w, xcd, t_ini = calc.calcular_carbonatacion(d_mm, rh_real, 65, 2.5, 5.0, kcd, kt, csd, racc, psr, dias_ll, bw, t0, t_ana)

    with col_plot:
        st.subheader("Evolución de la profundidad $X_{cd}$")
        fig = go.Figure()
        # Área rellena (estilo Schnittkräfte)
        fig.add_trace(go.Scatter(x=t, y=xcd, fill='tozeroy', name='Prof. Carbonatación',
                                 line=dict(color='#e17000', width=2), fillcolor='rgba(225, 112, 0, 0.2)'))
        # Línea de recubrimiento
        fig.add_trace(go.Scatter(x=t, y=[d_mm]*len(t), name='Límite Recubrimiento',
                                 line=dict(color='black', width=1, dash='dash')))
        
        fig.update_layout(plot_bgcolor='white', margin=dict(l=20, r=20, t=20, b=20),
                          xaxis=dict(showgrid=True, gridcolor='#eeeeee'),
                          yaxis=dict(showgrid=True, gridcolor='#eeeeee', title="[mm]"),
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        if t_ini:
            st.success(f"**Tiempo de iniciación:** {t_ini:.2f} años")
        else:
            st.warning("No se alcanza el tiempo de iniciación en el periodo analizado.")

elif tipo_ataque == "Cloruros":
    st.title("Difusión de Cloruros")
    
    col_input, col_plot = st.columns([1, 2])
    
    with col_input:
        st.subheader("Variables")
        d_mm = st.slider("Recubrimiento $c$ [mm]", 10, 100, 40)
        ccrit = st.number_input("$C_{crit}$ [%]", value=0.6)
        cs = st.number_input("$C_s$ [%]", value=2.0)
        t_ana = st.number_input("Tiempo de análisis [años]", value=100)
    
    # Cálculos (usando los valores de tu descripción)
    t, dapp, z, conc, t_ini = calc.calcular_cloruros(d_mm, 0.1, cs, ccrit, 4800, 293.0, 289.6, 1.0, 0.0767, 0.4288, 224.5363, t_ana)

    with col_plot:
        st.subheader("Concentración en el recubrimiento $C(t)$")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t, y=conc, fill='tozeroy', name='Concentración Cl-',
                                 line=dict(color='#e17000', width=2), fillcolor='rgba(225, 112, 0, 0.2)'))
        fig.add_trace(go.Scatter(x=t, y=[ccrit]*len(t), name='C_crit',
                                 line=dict(color='black', width=1, dash='dash')))
        
        fig.update_layout(plot_bgcolor='white', margin=dict(l=20, r=20, t=20, b=20),
                          xaxis=dict(showgrid=True, gridcolor='#eeeeee'),
                          yaxis=dict(showgrid=True, gridcolor='#eeeeee', title="% peso cemento"))
        st.plotly_chart(fig, use_container_width=True)

        if t_ini:
            st.success(f"**Tiempo de iniciación:** {t_ini:.2f} años")
