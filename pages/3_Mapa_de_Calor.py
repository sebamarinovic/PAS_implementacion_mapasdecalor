"""Mapa de calor PAS (sección 8): vista general por planta y drill-down
por área/sistema, con filtros y porcentajes (no sólo cantidades absolutas)."""
import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import analytics, rules, utils
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


def _heatmap(agg: pd.DataFrame, etiqueta_col: str, titulo: str):
    agg = agg.sort_values(etiqueta_col)
    riesgo = (agg["criticos_pct"] + 0.5 * agg["degradados_pct"]).clip(upper=100)
    texto = [
        f"<b>{row[etiqueta_col]}</b><br>{int(row['n_equipos'])} equipos<br>"
        f"Disp {row['disponibilidad_pct']}% · Crít {row['criticos_pct']}% · "
        f"Degr {row['degradados_pct']}% · S/Eval {row['sin_evaluar_pct']}%"
        for _, row in agg.iterrows()
    ]
    fig = go.Figure(data=go.Heatmap(
        z=[riesgo.tolist()],
        x=agg[etiqueta_col].tolist(),
        y=[titulo],
        text=[texto],
        texttemplate="%{text}",
        textfont={"size": 11},
        colorscale=[[0, "#2E7D32"], [0.5, "#F9A825"], [1.0, "#C62828"]],
        zmin=0, zmax=100,
        showscale=False,
        xgap=6, ygap=6,
    ))
    fig.update_layout(height=170 + 20 * 0, margin=dict(l=10, r=10, t=10, b=10))
    fig.update_yaxes(showticklabels=False)
    return fig


st.subheader("Vista general por planta")
kpp = analytics.kpis_por_planta(df)
st.plotly_chart(_heatmap(kpp, "planta_visible", "PAS"), use_container_width=True)

tabla_planta = kpp[["planta_visible", "n_equipos", "disponibilidad_pct", "criticos_pct", "degradados_pct", "sin_evaluar_pct"]].rename(columns={
    "planta_visible": "Planta", "n_equipos": "N° equipos", "disponibilidad_pct": "% Disponibilidad",
    "criticos_pct": "% Críticos", "degradados_pct": "% Degradados", "sin_evaluar_pct": "% Sin evaluar",
})
st.dataframe(
    tabla_planta.style.apply(
        lambda r: [f"background-color: {utils.color_semaforo(r['% Críticos'], r['% Degradados'], r['% Sin evaluar'])}"] * len(r),
        axis=1,
    ).format({c: "{:.1f}%" for c in ["% Disponibilidad", "% Críticos", "% Degradados", "% Sin evaluar"]}),
    use_container_width=True, hide_index=True,
)

if len(plantas_filtro) == 1:
    planta_unica = plantas_filtro[0]
    nombre_visible = catalogos["plantas_nombre_visible"].get(planta_unica, planta_unica)
    st.subheader(f"Detalle por área — {nombre_visible}")
    agg_area = analytics.heatmap_area_df(df)
    st.plotly_chart(_heatmap(agg_area, "area_sistema", nombre_visible), use_container_width=True)

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
    df_red = pd.DataFrame(redundancia)[[
        "grupo", "planta", "area_sistema", "n_miembros", "n_disponibles",
        "minimo_disponible", "estado_redundancia", "validado",
    ]].rename(columns={
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
