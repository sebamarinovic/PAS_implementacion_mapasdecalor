"""Generación de informes PDF (secciones 12 y 13): por área, consolidado y
semanal (comparando periodo actual vs. anterior, filtrable por turno)."""
import datetime as dt

import streamlit as st

from core import analytics, reports, rules
from core.session import get_conn, sidebar_identidad

st.set_page_config(page_title="PAS · Informes", page_icon="📄", layout="wide")

conn = get_conn()
usuario, tipo_turno, codigo_turno = sidebar_identidad()
catalogos = rules.load_catalogs()

st.title("Informes PDF")

tab_area, tab_consolidado, tab_semanal = st.tabs(["Informe por área", "Informe consolidado PAS", "Informe semanal / comparativo"])

with tab_area:
    st.write("Informe con KPIs, mapa de calor, equipos críticos, redundancia, hallazgos y avisos SAP de una sola planta.")
    planta = st.selectbox("Planta", catalogos["plantas"],
                           format_func=lambda p: catalogos["plantas_nombre_visible"].get(p, p), key="planta_area")
    if st.button("Generar PDF de área", key="btn_area"):
        path = reports.informe_area(conn, planta, responsable=usuario, turno=tipo_turno)
        with open(path, "rb") as f:
            st.download_button("⬇ Descargar informe", f.read(), file_name=path.name, mime="application/pdf")
        st.success(f"Informe generado: {path.name}")

with tab_consolidado:
    st.write("Informe con el estado de las 5 plantas (GCP-2, GCP-4, CAP-3, CAP-4, Circuito de Aguas).")
    if st.button("Generar PDF consolidado", key="btn_consolidado"):
        path = reports.informe_consolidado(conn, responsable=usuario, turno=tipo_turno)
        with open(path, "rb") as f:
            st.download_button("⬇ Descargar informe", f.read(), file_name=path.name, mime="application/pdf")
        st.success(f"Informe generado: {path.name}")

with tab_semanal:
    st.write(
        "Compara el estado actual con el estado de hace 7 días: nuevos críticos, equipos "
        "recuperados, equipos que permanecen críticos y cambios de disponibilidad."
    )
    ambito = st.selectbox("Ámbito", ["Consolidado (todos los turnos)", "Sólo turno Día", "Sólo turno Noche"])
    alcance = st.radio("Alcance del informe", ["Consolidado PAS", "Por planta"], horizontal=True)
    planta_semanal = None
    if alcance == "Por planta":
        planta_semanal = st.selectbox("Planta", catalogos["plantas"],
                                       format_func=lambda p: catalogos["plantas_nombre_visible"].get(p, p), key="planta_semanal")

    if st.button("Generar informe semanal", key="btn_semanal"):
        tipo_turno_filtro = {"Sólo turno Día": "Día", "Sólo turno Noche": "Noche"}.get(ambito)
        hoy = dt.datetime.now().isoformat(timespec="seconds")
        hace_7_dias = (dt.datetime.now() - dt.timedelta(days=7)).isoformat(timespec="seconds")

        df_actual = analytics.build_estado_df(conn, tipo_turno_filtro=tipo_turno_filtro)
        df_anterior = analytics.build_estado_df(conn, fecha_limite=hace_7_dias, tipo_turno_filtro=tipo_turno_filtro)
        if planta_semanal:
            df_actual = df_actual[df_actual["planta"] == planta_semanal]
            df_anterior = df_anterior[df_anterior["planta"] == planta_semanal]

        comparacion = analytics.comparar_periodos(df_actual, df_anterior)
        if planta_semanal:
            path = reports.informe_area(conn, planta_semanal, responsable=usuario, turno=ambito, df_comparacion=comparacion)
        else:
            path = reports.informe_consolidado(conn, responsable=usuario, turno=ambito, df_comparacion=comparacion)

        with open(path, "rb") as f:
            st.download_button("⬇ Descargar informe semanal", f.read(), file_name=path.name, mime="application/pdf")
        st.success(f"Informe semanal generado: {path.name}")
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("Nuevos críticos", len(comparacion["nuevos_criticos"]))
        cc2.metric("Recuperados", len(comparacion["recuperados"]))
        cc3.metric("Permanecen críticos", len(comparacion["permanecen_criticos"]))
