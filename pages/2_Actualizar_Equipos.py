"""Actualizar equipos — la página que usa el Jefe de Turno cada turno.

Regla de diseño (sección 2 y 6 del encargo): actualizar un equipo debe
tomar menos de 15 segundos. Por eso:
  - se precarga la última condición conocida ("copiar del turno anterior"),
  - el JT sólo toca lo que cambió,
  - filas sin cambios NO generan una nueva evaluación (no hay que llenar
    163 registros de nuevo),
  - un buscador por TAG permite actualizar un solo equipo en segundos.
"""
import datetime as dt

import streamlit as st

from core import analytics, database as db, rules, utils
from core.session import get_conn, sidebar_identidad

st.set_page_config(page_title="PAS · Actualizar equipos", page_icon="✏️", layout="wide")

conn = get_conn()
usuario, tipo_turno, codigo_turno = sidebar_identidad()
catalogos = rules.load_catalogs()

st.title("Actualizar equipos")
st.caption("Se muestra la última condición registrada. Modifique sólo lo que cambió y presione **Guardar**.")

df_estado = analytics.build_estado_df(conn)

col_a, col_b, col_c = st.columns([1, 1, 1.4])
with col_a:
    planta = st.selectbox("Planta", catalogos["plantas"],
                           format_func=lambda p: catalogos["plantas_nombre_visible"].get(p, p))
df_planta = df_estado[df_estado["planta"] == planta]
areas = ["Todas las áreas"] + sorted(df_planta["area_sistema"].dropna().unique().tolist())
with col_b:
    area = st.selectbox("Área / Sistema", areas)
with col_c:
    busqueda_tag = st.text_input("Buscar TAG (para actualizar 1 solo equipo)", placeholder="Ej: P101A(II)")

df_filtro = df_planta if area == "Todas las áreas" else df_planta[df_planta["area_sistema"] == area]
if busqueda_tag.strip():
    df_filtro = df_filtro[df_filtro["tag"].str.contains(busqueda_tag.strip(), case=False, na=False)]

if df_filtro.empty:
    st.warning("No hay equipos que coincidan con el filtro seleccionado.")
    st.stop()

EDITABLES = ["estado", "disponibilidad", "modo_operacion", "hallazgo", "aviso_sap"]
COLUMNAS_TABLA = ["equipment_id", "tag", "descripcion", "criticidad", "fecha_hora", "usuario"] + EDITABLES

base_df = df_filtro[COLUMNAS_TABLA].copy().reset_index(drop=True)
base_df["fecha_hora"] = base_df["fecha_hora"].fillna("Sin evaluar")
base_df["usuario"] = base_df["usuario"].fillna("—")

st.caption(f"{len(base_df)} equipo(s) en el filtro actual · {int((base_df['estado']=='Sin evaluar').sum())} sin evaluar")

edited_df = st.data_editor(
    base_df,
    key=f"editor_{planta}_{area}",
    use_container_width=True,
    hide_index=True,
    disabled=["equipment_id", "tag", "descripcion", "criticidad", "fecha_hora", "usuario"],
    column_config={
        "equipment_id": "ID",
        "tag": "TAG",
        "descripcion": "Servicio / Descripción",
        "criticidad": "Criticidad actual",
        "fecha_hora": "Última evaluación",
        "usuario": "Últ. usuario",
        "estado": st.column_config.SelectboxColumn("Estado", options=catalogos["estado_actual"], required=True),
        "disponibilidad": st.column_config.SelectboxColumn("Disponibilidad", options=catalogos["disponibilidad"], required=True),
        "modo_operacion": st.column_config.SelectboxColumn("Modo", options=catalogos["modo_operacion"], required=True),
        "hallazgo": st.column_config.TextColumn("Hallazgo (opcional)"),
        "aviso_sap": st.column_config.TextColumn("Aviso SAP (opcional)"),
    },
)

guardar = st.button("💾 GUARDAR ACTUALIZACIÓN DEL TURNO", type="primary", use_container_width=True)

if guardar:
    if not usuario.strip():
        st.error("Ingrese el nombre del Jefe de Turno / Operador en la barra lateral antes de guardar.")
        st.stop()

    comparacion = edited_df.merge(base_df, on="equipment_id", suffixes=("_nuevo", "_previo"))

    n_guardados = 0
    ahora = db.now_iso()
    for _, fila in comparacion.iterrows():
        cambio = any(str(fila[f"{c}_nuevo"]) != str(fila[f"{c}_previo"]) for c in EDITABLES)
        if not cambio:
            continue
        estado = fila["estado_nuevo"]
        disponibilidad = fila["disponibilidad_nuevo"]
        criticidad, prioridad, estado_dato = rules.classify_equipo(estado, disponibilidad)
        ev_id = db.siguiente_evaluation_id(conn)
        db.insert_evaluacion(conn, {
            "evaluation_id": ev_id,
            "equipment_id": fila["equipment_id"],
            "fecha_hora": ahora,
            "tipo_turno": tipo_turno,
            "codigo_turno": codigo_turno,
            "usuario": usuario,
            "estado": estado,
            "disponibilidad": disponibilidad,
            "modo_operacion": fila["modo_operacion_nuevo"],
            "criticidad": criticidad,
            "prioridad": prioridad,
            "hallazgo": fila["hallazgo_nuevo"] or None,
            "aviso_sap": fila["aviso_sap_nuevo"] or None,
            "ot": None,
            "evidencia": None,
            "comentario": None,
            "rule_version": rules.rule_version(),
            "estado_dato": estado_dato,
            "fuente": "App",
        })
        db.log_auditoria(
            conn, "evaluaciones", fila["equipment_id"], usuario, "Actualización de turno",
            campo="estado/disponibilidad",
            valor_anterior=f"{fila['estado_previo']}/{fila['disponibilidad_previo']}",
            valor_nuevo=f"{estado}/{disponibilidad}",
        )
        n_guardados += 1

    conn.commit()
    if n_guardados:
        st.success(f"{n_guardados} equipo(s) actualizados correctamente.")
        st.rerun()
    else:
        st.info("No se detectaron cambios respecto de la última condición registrada.")

st.divider()
with st.expander("Cerrar turno (registrar snapshot PAS completo)"):
    st.write(
        "Registra un cierre de turno con la cobertura de evaluación y los indicadores "
        "vigentes en ese momento para **las 5 plantas**, igual que PAS_CierresTurno en el "
        "diseño original. No borra ni duplica evaluaciones: sólo dejar constancia del cierre."
    )
    if st.button("🔒 Cerrar turno ahora"):
        if not usuario.strip():
            st.error("Ingrese el nombre del responsable en la barra lateral antes de cerrar el turno.")
        else:
            df_total = analytics.build_estado_df(conn)
            kpis_total = analytics.kpis_generales(df_total)
            shift_id = db.siguiente_shift_id(conn)
            db.insert_cierre_turno(conn, {
                "shift_id": shift_id,
                "fecha_operacional": dt.date.today().isoformat(),
                "tipo_turno": tipo_turno,
                "codigo_turno": codigo_turno,
                "jefe_responsable": usuario,
                "cobertura_pct": round(100 * kpis_total["evaluados"] / kpis_total["total_equipos"], 1) if kpis_total["total_equipos"] else 0,
                "criticos_abiertos": kpis_total["criticos"],
                "pendientes_validar": kpis_total["pendientes_validacion"],
                "estado_cierre": "Cerrado",
                "fecha_hora_cierre": db.now_iso(),
            })
            conn.commit()
            st.success(f"Turno cerrado ({shift_id}). Cobertura: {round(100 * kpis_total['evaluados'] / kpis_total['total_equipos'], 1) if kpis_total['total_equipos'] else 0}%")
