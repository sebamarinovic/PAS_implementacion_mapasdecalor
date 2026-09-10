"""Historial por equipo (sección 11): línea de tiempo y preguntas frecuentes
(cuándo salió de servicio, cuánto lleva, reincidencias, etc.)."""
import plotly.graph_objects as go
import streamlit as st

from core import analytics, database as db, rules, utils
from core.session import get_conn, sidebar_identidad

st.set_page_config(page_title="PAS · Historial", page_icon="🕘", layout="wide")

conn = get_conn()
sidebar_identidad()
catalogos = rules.load_catalogs()

st.title("Historial de equipo")

df_estado = analytics.build_estado_df(conn)

c1, c2 = st.columns(2)
with c1:
    planta = st.selectbox("Planta", catalogos["plantas"],
                           format_func=lambda p: catalogos["plantas_nombre_visible"].get(p, p))
opciones = df_estado[df_estado["planta"] == planta].sort_values("tag")
with c2:
    equipment_id = st.selectbox(
        "TAG", opciones["equipment_id"].tolist(),
        format_func=lambda eid: opciones.loc[opciones["equipment_id"] == eid, "tag"].iloc[0],
    )

fila = df_estado[df_estado["equipment_id"] == equipment_id].iloc[0]

st.subheader(f"{fila['tag']} — {fila['descripcion'] or 'Sin descripción'}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Área / Sistema", fila["area_sistema"])
c2.metric("Estado actual", fila["estado"])
c3.metric("Disponibilidad actual", fila["disponibilidad"])
c4.metric("Criticidad", fila["criticidad"])
if fila["hallazgo"]:
    st.info(f"Último hallazgo: {fila['hallazgo']}")
if fila["aviso_sap"]:
    st.info(f"Último aviso SAP: {fila['aviso_sap']}")
if fila["requiere_validacion"] == "Sí":
    st.warning(f"Equipo marcado como 'Requiere validación': {fila['observacion_calidad']}")

resumen = analytics.historial_resumen(conn, equipment_id)
st.divider()
st.subheader("Indicadores de confiabilidad")
c1, c2, c3, c4 = st.columns(4)
c1.metric("N° evaluaciones", resumen.get("n_evaluaciones", 0))
c2.metric("Veces fuera de servicio", resumen.get("veces_fuera_servicio", 0))
c3.metric("Veces perdió disponibilidad", resumen.get("veces_perdio_disponibilidad", 0))
c4.metric("Reincidencias", resumen.get("reincidencias", 0))

if resumen.get("tiempo_fuera_actual"):
    dias = resumen["tiempo_fuera_actual"].days
    st.error(f"Este equipo lleva **{dias} día(s)** fuera de servicio desde {resumen['ultima_salida_servicio']}.")
elif resumen.get("ultima_recuperacion"):
    st.success(f"Última recuperación registrada: {resumen['ultima_recuperacion']}")

st.divider()
st.subheader("Línea de tiempo")
hist = [dict(r) for r in db.get_historial_equipo(conn, equipment_id)]
if not hist:
    st.info("Sin evaluaciones registradas para este equipo.")
else:
    orden_criticidad = {"Operativo": 0, "Degradado": 1, "Verificar": 2, "Ruta crítica": 3}
    xs = [h["fecha_hora"] for h in hist]
    ys = [orden_criticidad.get(h["criticidad"], 2) for h in hist]
    colores = [utils.color_por_criticidad(h["criticidad"]) for h in hist]
    textos = [f"{h['estado']} / {h['disponibilidad']}<br>{h['hallazgo'] or ''}" for h in hist]

    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        marker=dict(size=12, color=colores, line=dict(width=1, color="#333")),
        line=dict(color="#999", width=1),
        text=textos, hoverinfo="text+x",
    ))
    fig.update_yaxes(
        tickmode="array", tickvals=[0, 1, 2, 3],
        ticktext=["Operativo", "Degradado", "Verificar", "Ruta crítica"],
        range=[-0.5, 3.5],
    )
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    tabla = [{
        "Fecha/hora": h["fecha_hora"], "Turno": h["tipo_turno"], "Usuario": h["usuario"],
        "Estado": h["estado"], "Disponibilidad": h["disponibilidad"], "Modo": h["modo_operacion"],
        "Criticidad": h["criticidad"], "Hallazgo": h["hallazgo"], "SAP": h["aviso_sap"],
        "Estado del dato": h["estado_dato"],
    } for h in reversed(hist)]
    st.dataframe(tabla, use_container_width=True, hide_index=True)
