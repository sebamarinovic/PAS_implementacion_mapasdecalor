"""Contenido de la página Resumen PAS, compartido por app.py y
pages/1_Resumen_PAS.py para no duplicar lógica."""
from __future__ import annotations

import streamlit as st

from core import analytics, rules, ui_charts


def render(conn) -> None:
    st.title("PAS — Resumen operacional")
    st.caption(
        "División Chuquicamata · Plantas de Ácido y Oxígeno · GCP-2 · GCP-4 · CAP-3 · CAP-4 · Circuito de Aguas"
    )

    df = analytics.build_estado_df(conn)
    kpis = analytics.kpis_generales(df)
    equipos = df.to_dict("records")
    ultimas = {r["equipment_id"]: r for r in equipos}
    redundancia = rules.evaluate_redundancy(equipos, ultimas)
    sin_respaldo = sum(1 for g in redundancia if g["estado_redundancia"] == "Sin respaldo")
    pendiente_regla = sum(1 for g in redundancia if g["estado_redundancia"] == "Pendiente de validación")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Disponibilidad PAS", f"{kpis['disponibilidad_pct']}%")
    c2.metric("Equipos evaluados", f"{kpis['evaluados']}/{kpis['total_equipos']}")
    c3.metric("Equipos críticos", kpis["criticos"])
    c4.metric("Fuera de servicio", kpis["fuera_servicio"])
    c5.metric(
        "Sistemas sin respaldo", sin_respaldo,
        help=f"{pendiente_regla} grupo(s) de redundancia con regla operacional pendiente de validación",
    )
    c6.metric("Avisos SAP abiertos", kpis["avisos_sap_abiertos"])

    if kpis["pendientes_validacion"]:
        st.warning(
            f"⚠ {kpis['pendientes_validacion']} equipo(s) con datos pendientes de validación "
            "(duplicados, contradicciones u observaciones de calidad abiertas). Ver página Administración."
        )

    st.subheader("Condición por planta")
    kpp = analytics.kpis_por_planta(df)
    ui_charts.render_tarjetas_calor(kpp, "planta_visible")

    st.divider()
    col_a, col_b = st.columns([1, 1.4])
    with col_a:
        st.subheader("Distribución PAS por criticidad")
        st.plotly_chart(ui_charts.grafico_distribucion_criticidad(df), use_container_width=True)
    with col_b:
        st.subheader("Criticidad por planta")
        st.plotly_chart(ui_charts.grafico_criticidad_por_planta(df), use_container_width=True)

    tendencia = analytics.tendencia_diaria(conn)
    fig_tendencia = ui_charts.grafico_tendencia(tendencia)
    st.subheader("Tendencia")
    if fig_tendencia is None:
        st.caption(
            "Aún no hay suficientes turnos registrados en fechas distintas para mostrar una "
            "tendencia. Este gráfico se completa solo a medida que se cierran turnos."
        )
    else:
        st.plotly_chart(fig_tendencia, use_container_width=True)

    st.divider()
    cols = st.columns(4)
    with cols[0]:
        st.page_link("pages/2_Actualizar_Equipos.py", label="Actualizar equipos", icon="✏️")
    with cols[1]:
        st.page_link("pages/3_Mapa_de_Calor.py", label="Mapa de calor", icon="🗺️")
    with cols[2]:
        st.page_link("pages/5_Informes.py", label="Generar informes", icon="📄")
    with cols[3]:
        st.page_link("pages/6_Administracion.py", label="Control de calidad", icon="🛠️")
