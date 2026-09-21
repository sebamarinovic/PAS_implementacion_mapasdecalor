"""Administración: control de calidad (sección 14), reglas de redundancia,
cierres de turno y auditoría (sección 16)."""
import streamlit as st

from core import analytics, database as db, rules, validators
from core.session import get_conn, sidebar_identidad

st.set_page_config(page_title="PAS · Administración", page_icon="🛠️", layout="wide")

conn = get_conn()
sidebar_identidad()

st.title("Administración")

tab_calidad, tab_reglas, tab_cierres, tab_auditoria = st.tabs(
    ["Control de calidad", "Reglas de redundancia", "Cierres de turno", "Auditoría"]
)

with tab_calidad:
    st.caption(
        "Nunca se corrige automáticamente una condición operacional. Esta pestaña sólo detecta "
        "y reporta; la corrección la realiza una persona autorizada."
    )
    df_estado = analytics.build_estado_df(conn)
    hallazgos = validators.run_quality_checks(df_estado)
    if hallazgos.empty:
        st.success("Sin hallazgos de calidad de datos.")
    else:
        tipos = ["Todos"] + sorted(hallazgos["tipo"].unique().tolist())
        filtro_tipo = st.selectbox("Filtrar por tipo de hallazgo", tipos)
        vista = hallazgos if filtro_tipo == "Todos" else hallazgos[hallazgos["tipo"] == filtro_tipo]
        st.metric("Hallazgos totales", len(hallazgos))
        st.dataframe(vista.rename(columns={
            "tipo": "Tipo", "equipment_id": "ID", "tag": "TAG", "planta": "Planta",
            "area_sistema": "Área/Sistema", "detalle": "Detalle", "accion_requerida": "Acción requerida",
        }), use_container_width=True, hide_index=True)

with tab_reglas:
    st.caption(
        "Las reglas de redundancia viven en config/rules.yaml para que Operaciones pueda "
        "revisarlas sin tocar código. Editar ese archivo y reiniciar la aplicación para aplicar cambios."
    )
    st.write(f"**Versión de reglas activa:** `{rules.rule_version()}`")
    grupos = rules.load_rules()["grupos_redundancia"]
    filas = [{
        "Grupo": nombre, "Planta": cfg["planta"], "Área/Sistema": cfg["area_sistema"],
        "Regla original": cfg["regla_original"],
        "Mínimo sugerido": cfg["minimo_disponible"] if cfg.get("minimo_disponible") is not None else "—",
        "Crítico funcional": "⚠ Sí" if cfg.get("critico_funcional") else "",
        "Validado": "✅ Sí" if cfg.get("validado") else "No",
        "Fuente de validación": cfg.get("fuente_validacion", ""),
        "Nota": cfg.get("nota", ""),
    } for nombre, cfg in grupos.items()]
    st.dataframe(filas, use_container_width=True, hide_index=True)
    st.info(
        "Mientras un grupo figure como 'Validado = No', el mapa de calor y los informes lo "
        "mostrarán como 'Pendiente de validación' y no lo clasificarán automáticamente como "
        "'Sin respaldo', aunque cuenten los equipos disponibles."
    )

with tab_cierres:
    cierres = [dict(r) for r in db.get_cierres_turno(conn)]
    if not cierres:
        st.info("Aún no se han registrado cierres de turno. Use el botón 'Cerrar turno' en Actualizar Equipos.")
    else:
        st.dataframe([{
            "Turno": c["shift_id"], "Fecha": c["fecha_operacional"], "Tipo": c["tipo_turno"],
            "Código": c["codigo_turno"], "Responsable": c["jefe_responsable"],
            "Cobertura %": c["cobertura_pct"], "Críticos abiertos": c["criticos_abiertos"],
            "Pendientes validar": c["pendientes_validar"], "Estado": c["estado_cierre"],
            "Fecha/hora cierre": c["fecha_hora_cierre"],
        } for c in cierres], use_container_width=True, hide_index=True)

with tab_auditoria:
    auditoria = [dict(r) for r in db.get_auditoria(conn)]
    if not auditoria:
        st.info("Sin registros de auditoría todavía.")
    else:
        st.dataframe([{
            "Fecha/hora": a["fecha_hora"], "Tabla": a["tabla"], "Registro": a["registro_id"],
            "Usuario": a["usuario"], "Acción": a["accion"], "Campo": a["campo"],
            "Valor anterior": a["valor_anterior"], "Valor nuevo": a["valor_nuevo"],
        } for a in auditoria], use_container_width=True, hide_index=True)
