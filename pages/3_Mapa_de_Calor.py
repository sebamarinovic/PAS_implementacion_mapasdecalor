"""Mapa de calor PAS (sección 8): vista general por planta y drill-down
por área/sistema, con filtros, porcentajes (no sólo cantidades absolutas),
redundancia y línea de proceso."""
import datetime as dt

import pandas as pd
import streamlit as st

from core import analytics, process_lines, rules, ui_charts
from core.session import get_conn, sidebar_identidad

st.set_page_config(page_title="PAS · Mapa de calor", page_icon="🗺️", layout="wide")

conn = get_conn()
sidebar_identidad()
catalogos = rules.load_catalogs()

st.title("Mapa de calor PAS")
st.caption("Verde = operación normal · Amarillo = degradado / con restricción · Rojo = crítico / fuera de servicio · Gris = sin información o pendiente de validar")

with st.expander("Filtros", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        turno_filtro = st.selectbox("Turno", ["Todos"] + catalogos["tipo_turno"])
    with c2:
        fecha = st.date_input("Fecha (estado vigente a esa fecha)", value=dt.date.today())
    with c3:
        plantas_filtro = st.multiselect(
            "Planta", catalogos["plantas"],
            format_func=lambda p: catalogos["plantas_nombre_visible"].get(p, p),
        )
    c4, c5, c6 = st.columns(3)
    with c4:
        tipo_elemento_filtro = st.multiselect("Tipo de equipo", catalogos["tipo_elemento"])
    with c5:
        estado_filtro = st.multiselect("Estado", catalogos["estado_actual"])
    with c6:
        criticidad_filtro = st.multiselect("Criticidad", catalogos["criticidad"])

fecha_limite = None
if fecha != dt.date.today():
    fecha_limite = f"{fecha.isoformat()}T23:59:59"
tipo_turno_filtro = None if turno_filtro == "Todos" else turno_filtro

df = analytics.build_estado_df(conn, fecha_limite=fecha_limite, tipo_turno_filtro=tipo_turno_filtro)
if plantas_filtro:
    df = df[df["planta"].isin(plantas_filtro)]
if tipo_elemento_filtro:
    df = df[df["tipo_elemento"].isin(tipo_elemento_filtro)]
if estado_filtro:
    df = df[df["estado"].isin(estado_filtro)]
if criticidad_filtro:
    df = df[df["criticidad"].isin(criticidad_filtro)]

if df.empty:
    st.warning("No hay equipos que coincidan con los filtros seleccionados.")
    st.stop()

st.subheader("Vista general por planta")
kpp = analytics.kpis_por_planta(df)
ui_charts.render_tarjetas_calor(kpp, "planta_visible")

if len(plantas_filtro) == 1:
    planta_unica = plantas_filtro[0]
    nombre_visible = catalogos["plantas_nombre_visible"].get(planta_unica, planta_unica)
    st.subheader(f"Detalle por área — {nombre_visible}")
    agg_area = analytics.heatmap_area_df(df)
    ui_charts.render_tarjetas_calor(agg_area, "area_sistema")

    st.subheader("Equipos del área seleccionada")
    cols_detalle = ["tag", "area_sistema", "tipo_elemento", "estado", "disponibilidad", "criticidad", "hallazgo", "aviso_sap"]
    st.dataframe(
        df[cols_detalle].rename(columns={
            "tag": "TAG", "area_sistema": "Área/Sistema", "tipo_elemento": "Tipo",
            "estado": "Estado", "disponibilidad": "Disponibilidad", "criticidad": "Criticidad",
            "hallazgo": "Hallazgo", "aviso_sap": "Aviso SAP",
        }),
        use_container_width=True, hide_index=True,
    )
else:
    st.caption("Seleccione una sola planta en el filtro para ver el detalle por área y la tabla de equipos.")

st.divider()
st.subheader("Redundancia y ruta crítica")
equipos_dict = df.to_dict("records")
ultimas_dict = {r["equipment_id"]: r for r in equipos_dict}
redundancia = rules.evaluate_redundancy(equipos_dict, ultimas_dict)
if redundancia:
    fig_red = ui_charts.grafico_redundancia(redundancia)
    if fig_red is not None:
        st.plotly_chart(fig_red, use_container_width=True)
    df_red = pd.DataFrame(redundancia)[[
        "grupo", "planta", "area_sistema", "n_miembros", "n_disponibles",
        "minimo_disponible", "estado_redundancia", "validado",
    ]]
    df_red["minimo_disponible"] = df_red["minimo_disponible"].apply(
        lambda v: "—" if pd.isna(v) else int(v)
    )
    df_red = df_red.rename(columns={
        "grupo": "Grupo", "planta": "Planta", "area_sistema": "Área/Sistema",
        "n_miembros": "N° miembros", "n_disponibles": "N° disponibles",
        "minimo_disponible": "Mínimo sugerido", "estado_redundancia": "Estado",
        "validado": "Regla validada",
    })
    st.dataframe(df_red, use_container_width=True, hide_index=True)
    st.caption(
        "Los grupos marcados como 'Pendiente de validación' no se clasifican automáticamente como "
        "'Sin respaldo' hasta que Operaciones confirme la regla en config/rules.yaml (ver página Administración)."
    )

st.divider()
st.subheader("Línea de proceso")
st.caption(
    "Relación funcional entre plantas: color de cada etapa = severidad actual de esa planta. "
    "El enfriamiento cruzado (líneas punteadas) está confirmado por documentos de ingeniería — "
    "ver detalle abajo."
)
kpp_completo = analytics.kpis_por_planta(analytics.build_estado_df(conn))
st.plotly_chart(process_lines.grafico_lineas_proceso(kpp_completo), use_container_width=True)

with st.expander("Detalle de líneas de proceso y enfriamiento cruzado"):
    datos = process_lines.load_process_lines()
    st.markdown("**Líneas de proceso (gas → ácido):**")
    for linea in datos["lineas_proceso"]:
        st.markdown(f"- {' → '.join(linea['etapas_visible'])}")

    st.markdown("**Enfriamiento de gases de entrada (P-101) — crítico funcional, mínimo aún sin confirmar:**")
    st.caption("Enfrían la totalidad de los gases de entrada de su planta; pérdida total = crítico para toda la planta, no sólo el subtren.")
    for grupo in datos["enfriamiento_gases_entrada"]:
        for sub in grupo["subtrenes"]:
            st.markdown(f"- {sub['nombre']}: {', '.join(sub['tags'])}")

    st.markdown("**Bombas de agua desmineralizada — respaldo automático confirmado:**")
    for b in datos["bombas_agua_desmi"]:
        nombre_planta = rules.load_catalogs()["plantas_nombre_visible"].get(b["enfria_a"], b["enfria_a"])
        st.markdown(f"- {b['tag']} → enfría {nombre_planta} · respaldo común: {b['respaldo_comun']}. _{b['nota']}_")

    st.markdown("**Enfriamiento cruzado — ✅ confirmado por documentos de ingeniería:**")
    for rel in datos["enfriamiento_cruzado"]:
        st.markdown(
            f"- {rel['torre']} enfría sistema {rel['sistema']} de **{rel['enfria_a_visible']}** · "
            f"bombas: {', '.join(rel['bombas'])} · intercambiadores: {', '.join(rel['intercambiadores'])}. "
            f"_{rel['nota']}_"
        )
        st.caption(rel["fuente_validacion"])
    st.caption(datos["fuente"])
