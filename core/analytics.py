"""Cálculo de KPIs, mapa de calor y comparaciones de periodo.

Todo aquí recibe conexiones/DataFrames y devuelve estructuras simples
(dict, DataFrame) para que las páginas Streamlit sólo se preocupen de
pintar la UI (sección 3: separar frontend de lógica de negocio).
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from core import database as db
from core import rules
from core import utils

COLUMNAS_ESTADO = [
    "equipment_id", "planta", "area_sistema", "tag", "tipo_elemento", "descripcion",
    "grupo_redundancia", "requiere_validacion", "observacion_calidad",
    "estado", "disponibilidad", "modo_operacion", "criticidad", "prioridad",
    "hallazgo", "aviso_sap", "ot", "estado_dato", "fecha_hora", "usuario",
]


_CAMPOS_EVAL = [
    "estado", "disponibilidad", "modo_operacion", "criticidad", "prioridad",
    "hallazgo", "aviso_sap", "ot", "estado_dato", "fecha_hora", "usuario", "tipo_turno",
]
_DEFAULT_SIN_EVALUAR = {
    "estado": "Sin evaluar", "disponibilidad": "Sin evaluar", "modo_operacion": "Sin evaluar",
    "criticidad": "Verificar", "prioridad": "P3", "hallazgo": None, "aviso_sap": None,
    "ot": None, "estado_dato": "Pendiente", "fecha_hora": None, "usuario": None, "tipo_turno": None,
}


def build_estado_df(conn, fecha_limite: str | None = None, tipo_turno_filtro: str | None = None) -> pd.DataFrame:
    """Une equipos con su evaluación más reciente. 1 fila por equipo.

    fecha_limite: si se entrega (ISO), reconstruye el estado "as of" esa
    fecha/hora usando sólo evaluaciones anteriores o iguales (Mapa de Calor,
    sección 8, filtro por Fecha).
    tipo_turno_filtro: restringe a evaluaciones de ese turno (Día/Noche).
    """
    equipos_df = pd.DataFrame([dict(r) for r in db.get_equipos(conn)])
    evals_df = db.get_evaluaciones_df(conn)

    if fecha_limite:
        evals_df = evals_df[evals_df["fecha_hora"] <= fecha_limite]
    if tipo_turno_filtro:
        evals_df = evals_df[evals_df["tipo_turno"] == tipo_turno_filtro]

    if not evals_df.empty:
        evals_df = evals_df.sort_values(["fecha_hora", "evaluation_id"])
        ultimas = evals_df.groupby("equipment_id", as_index=False).tail(1)
    else:
        ultimas = pd.DataFrame(columns=["equipment_id"] + _CAMPOS_EVAL)

    df = equipos_df.merge(ultimas[["equipment_id"] + _CAMPOS_EVAL], on="equipment_id", how="left")
    for campo, valor_default in _DEFAULT_SIN_EVALUAR.items():
        df[campo] = df[campo].where(df[campo].notna(), valor_default)
    return df


def kpis_generales(df: pd.DataFrame) -> dict:
    total = len(df)
    if total == 0:
        return {k: 0 for k in [
            "total_equipos", "evaluados", "disponibilidad_pct", "criticos",
            "fuera_servicio", "sin_respaldo", "pendientes_validacion",
            "avisos_sap_abiertos",
        ]}
    evaluados = int((df["estado"] != "Sin evaluar").sum())
    disponibles = int(df["disponibilidad"].apply(utils.es_estado_disponible).sum())
    return {
        "total_equipos": total,
        "evaluados": evaluados,
        "disponibilidad_pct": round(100 * disponibles / total, 1),
        "criticos": int((df["criticidad"] == "Ruta crítica").sum()),
        "fuera_servicio": int((df["estado"] == "Fuera de servicio").sum()),
        "pendientes_validacion": int(
            ((df["requiere_validacion"] == "Sí") | (df["estado_dato"] != "OK")).sum()
        ),
        "avisos_sap_abiertos": int(df["aviso_sap"].fillna("").astype(str).str.strip().ne("").sum()),
    }


def kpis_por_planta(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    catalogos = rules.load_catalogs()
    nombres = catalogos.get("plantas_nombre_visible", {})

    def agg(g: pd.DataFrame) -> pd.Series:
        n = len(g)
        disponibles = g["disponibilidad"].apply(utils.es_estado_disponible).sum()
        return pd.Series({
            "n_equipos": n,
            "disponibilidad_pct": round(100 * disponibles / n, 1) if n else 0,
            "criticos_pct": round(100 * (g["criticidad"] == "Ruta crítica").sum() / n, 1) if n else 0,
            "degradados_pct": round(100 * (g["criticidad"] == "Degradado").sum() / n, 1) if n else 0,
            "sin_evaluar_pct": round(100 * (g["estado"] == "Sin evaluar").sum() / n, 1) if n else 0,
            "criticos_n": int((g["criticidad"] == "Ruta crítica").sum()),
            "fuera_servicio_n": int((g["estado"] == "Fuera de servicio").sum()),
        })

    out = df.groupby("planta").apply(agg).reset_index()
    out["planta_visible"] = out["planta"].map(lambda p: nombres.get(p, p))
    for c in ("n_equipos", "criticos_n", "fuera_servicio_n"):
        out[c] = out[c].astype(int)
    return out


def heatmap_area_df(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega por planta + área/sistema para el mapa de calor detallado."""
    if df.empty:
        return pd.DataFrame()

    def agg(g: pd.DataFrame) -> pd.Series:
        n = len(g)
        disponibles = g["disponibilidad"].apply(utils.es_estado_disponible).sum()
        return pd.Series({
            "n_equipos": n,
            "disponibilidad_pct": round(100 * disponibles / n, 1) if n else 0,
            "criticos_pct": round(100 * (g["criticidad"] == "Ruta crítica").sum() / n, 1) if n else 0,
            "degradados_pct": round(100 * (g["criticidad"] == "Degradado").sum() / n, 1) if n else 0,
            "sin_evaluar_pct": round(100 * (g["estado"] == "Sin evaluar").sum() / n, 1) if n else 0,
        })

    out = df.groupby(["planta", "area_sistema"]).apply(agg).reset_index()
    out["n_equipos"] = out["n_equipos"].astype(int)
    return out


def historial_resumen(conn, equipment_id: str) -> dict:
    """Responde las preguntas de la sección 11: cuándo salió, cuánto lleva,
    cuántas veces ha fallado, cuántas reincidencias, cuándo se recuperó."""
    hist = [dict(r) for r in db.get_historial_equipo(conn, equipment_id)]
    if not hist:
        return {}

    veces_fuera_servicio = 0
    veces_perdio_disponibilidad = 0
    reincidencias = 0
    ultimo_evento_fuera = None
    ultima_recuperacion = None
    prev_disponible = None
    prev_estado_fs = False

    for ev in hist:
        disponible = utils.es_estado_disponible(ev["disponibilidad"])
        estado_fs = ev["estado"] == "Fuera de servicio"

        if estado_fs and not prev_estado_fs:
            veces_fuera_servicio += 1
            ultimo_evento_fuera = ev["fecha_hora"]
            if prev_disponible is True:
                reincidencias += 1
        if prev_disponible is True and disponible is False:
            veces_perdio_disponibilidad += 1
        if prev_disponible is False and disponible is True:
            ultima_recuperacion = ev["fecha_hora"]

        prev_disponible = disponible
        prev_estado_fs = estado_fs

    actual = hist[-1]
    tiempo_fuera_actual = None
    if actual["estado"] == "Fuera de servicio" and ultimo_evento_fuera:
        try:
            inicio = dt.datetime.fromisoformat(ultimo_evento_fuera)
            tiempo_fuera_actual = dt.datetime.now() - inicio
        except ValueError:
            pass

    return {
        "estado_actual": actual["estado"],
        "disponibilidad_actual": actual["disponibilidad"],
        "ultimo_hallazgo": actual["hallazgo"],
        "ultimo_sap": actual["aviso_sap"],
        "veces_fuera_servicio": veces_fuera_servicio,
        "veces_perdio_disponibilidad": veces_perdio_disponibilidad,
        "reincidencias": reincidencias,
        "ultima_salida_servicio": ultimo_evento_fuera,
        "ultima_recuperacion": ultima_recuperacion,
        "tiempo_fuera_actual": tiempo_fuera_actual,
        "n_evaluaciones": len(hist),
    }


def comparar_periodos(df_actual: pd.DataFrame, df_anterior: pd.DataFrame) -> dict:
    """Compara el estado más reciente de dos periodos (sección 13)."""
    if df_anterior.empty:
        base_ids = set()
    else:
        base_ids = set(df_anterior.loc[df_anterior["criticidad"] == "Ruta crítica", "equipment_id"])
    actual_ids = set(df_actual.loc[df_actual["criticidad"] == "Ruta crítica", "equipment_id"])

    nuevos_criticos = actual_ids - base_ids
    recuperados = base_ids - actual_ids
    permanecen_criticos = actual_ids & base_ids

    disp_actual = df_actual.set_index("equipment_id")["disponibilidad"].apply(utils.es_estado_disponible)
    if not df_anterior.empty:
        disp_anterior = df_anterior.set_index("equipment_id")["disponibilidad"].apply(utils.es_estado_disponible)
    else:
        disp_anterior = pd.Series(dtype=bool)
    comunes = disp_actual.index.intersection(disp_anterior.index)
    cambios_disponibilidad = int((disp_actual.loc[comunes] != disp_anterior.loc[comunes]).sum())

    return {
        "nuevos_criticos": sorted(nuevos_criticos),
        "recuperados": sorted(recuperados),
        "permanecen_criticos": sorted(permanecen_criticos),
        "cambios_disponibilidad": cambios_disponibilidad,
    }
