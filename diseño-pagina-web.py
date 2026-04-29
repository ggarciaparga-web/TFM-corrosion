# --- DENTRO DE TAB_MC EN diseño-pagina-web.py ---

with tab_mc:
    # ... (Inputs anteriores de geometría) ...
    
    # Recuperamos t_ini de la pestaña anterior (o 0 si no se calculó)
    t_ini_prev = st.session_state.get('t_ini_res', 0)
    tipo_ataque = st.session_state.get('tipo_ataque', "Carbonatación")
    alpha_v = 2.0 if tipo_ataque == "Carbonatación" else 10.0
    
    # Límite normativo de px (en mm)
    px_limite = 0.05 if tipo_ataque == "Carbonatación" else 0.5
    
    st.info(f"Análisis basado en Tiempo de Iniciación: **{t_ini_prev:.2f} años** (Alpha={alpha_v})")

    # Cálculo
    t_v, px_v, phi_i_v, m_res, m_cons = calc_mc.calcular_capacidad_residual(
        t_ana_mc, b, h, rec_sup, rec_inf, n_sup, phi_sup_0, n_inf, phi_inf_0, 
        fyk, fck, icorr, alpha_v, t_ini_prev
    )

    # Buscar tiempo asociado a px_limite
    idx_limite = np.where(px_v >= px_limite)[0]
    t_final_norma = t_v[idx_limite[0]] if len(idx_limite) > 0 else None

    # --- GRÁFICOS ---
    g_c1, g_c2 = st.columns(2)
    
    with g_c1:
        st.write("### Momento Resistente vs Tiempo")
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=t_v, y=m_res, name="Approach 1", line=dict(color='#e17000', width=3)))
        
        # Línea vertical del límite normativo
        if t_final_norma:
            fig_t.add_vline(x=t_final_norma, line_dash="dot", line_color="red", 
                            annotation_text=f"Fin Vida Útil ({t_final_norma:.1f} a)")
            
        fig_t.update_layout(plot_bgcolor='white', xaxis_title="Tiempo [años]", yaxis_title="Mrd [kNm]",
                          xaxis=dict(range=[0, t_ana_mc]), yaxis=dict(range=[0, max(m_res)*1.1]))
        st.plotly_chart(fig_t, use_container_width=True)

    with g_c2:
        st.write("### Momento Resistente vs Prof. Corrosión ($p_x$)")
        fig_px = go.Figure()
        fig_px.add_trace(go.Scatter(x=px_v, y=m_res, name="Mrd vs px", line=dict(color='#333', width=3)))
        
        # Línea vertical px límite
        fig_px.add_vline(x=px_limite, line_dash="dash", line_color="red", 
                         annotation_text=f"Límite {px_limite}mm")
        
        fig_px.update_layout(plot_bgcolor='white', xaxis_title="px [mm]", yaxis_title="Mrd [kNm]",
                            xaxis=dict(range=[0, max(px_v)*1.1 if len(px_v)>0 else 1]), 
                            yaxis=dict(range=[0, max(m_res)*1.1]))
        st.plotly_chart(fig_px, use_container_width=True)

    if t_final_norma:
        st.success(f"**Tiempo final según normativa (px={px_limite}mm):** {t_final_norma:.2f} años")
