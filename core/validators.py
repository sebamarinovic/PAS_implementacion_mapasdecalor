"""Control de calidad de datos (sección 14 del encargo).

Nunca corrige nada automáticamente: sólo detecta y reporta. La corrección
la hace una persona autorizada (Leonardo / Eleazar / Jefe de Turno /
Administrador funcional), tal como indica 05_Vistas_Permisos.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from core import rules

DIAS_SIN_ACTUALIZAR_ALERTA = 14

EXPECTED_AREA_POR_PLANTA = {
    "GCP2": "GCP-2",
    "GCP4": "GCP-4",
}


def _area_inconsistente(planta: str, area: str) -> bool:
    esperado = EXPECTED_AREA_POR_PLANTA.get(planta)
    return esperado is not None and area != esperado


def run_quality_checks(df_estado: pd.DataFrame) -> pd.DataFrame:
    """Recibe el DataFrame de build_estado_df (1 fila por equipo, con su
    última evaluación) y devuelve una tabla de hallazgos de calidad."""
    catalogos = rules.load_catalogs()
    hallazgos = []

    if df_estado.empty:
        return pd.DataFrame(columns=["tipo", "equipment_id", "tag", "detalle", "accion_requerida"])

    # 1) TAG vacíos
    vacios = df_estado[df_estado["tag"].fillna("").astype(str).str.strip() == ""]
    for _, r in vacios.iterrows():
        hallazgos.append(_hallazgo("TAG vacío", r, "Completar TAG físico del equipo antes de operar el catálogo."))

    # 2) TAG duplicados (misma planta vs. distinta planta)
    con_tag = df_estado[df_estado["tag"].fillna("").astype(str).str.strip() != ""]
    for tag, grupo in con_tag.groupby("tag"):
        if len(grupo) < 2:
            continue
        plantas = grupo["planta"].unique()
        if len(plantas) == 1:
            estados_distintos = grupo[["estado", "disponibilidad"]].drop_duplicates().shape[0] > 1
            tipo = "TAG duplicado con datos diferentes" if estados_distintos else "TAG duplicado (misma planta)"
            for _, r in grupo.iterrows():
                hallazgos.append(_hallazgo(
                    tipo, r,
                    "Consolidar sólo si corresponden al mismo activo físico; si son equipos "
                    "distintos, incorporar sufijo de planta/unidad al TAG maestro.",
                    extra=f"Coincide con {len(grupo) - 1} registro(s) más del mismo TAG en {grupo.iloc[0]['planta']}."
                ))
        else:
            for _, r in grupo.iterrows():
                hallazgos.append(_hallazgo(
                    "Duplicado potencial entre plantas", r,
                    "Probablemente son activos distintos con el mismo TAG en plantas diferentes; "
                    "confirmar y, si corresponde, dejar constancia en observación de calidad.",
                    extra=f"TAG repetido en: {', '.join(sorted(plantas))}."
                ))

    # 3) Estados fuera de catálogo
    for _, r in df_estado.iterrows():
        if r["estado"] not in catalogos["estado_actual"]:
            hallazgos.append(_hallazgo("Estado fuera de catálogo", r,
                                        f"Normalizar 'Estado actual' ({r['estado']!r}) a un valor del catálogo controlado."))
        if r["disponibilidad"] not in catalogos["disponibilidad"]:
            hallazgos.append(_hallazgo("Valor fuera de catálogo", r,
                                        f"El campo Disponibilidad tiene {r['disponibilidad']!r}, valor no admitido por el catálogo."))
        if r["modo_operacion"] not in catalogos["modo_operacion"]:
            hallazgos.append(_hallazgo("Valor fuera de catálogo", r,
                                        f"El campo Modo de operación tiene {r['modo_operacion']!r}, valor no admitido por el catálogo."))

    # 4) Disponibilidad contradictoria (incluye "Fuera de servicio" pero "Disponible")
    for _, r in df_estado.iterrows():
        if rules.is_contradiccion(r["estado"], r["disponibilidad"]):
            hallazgos.append(_hallazgo("Estado/disponibilidad contradictorios", r,
                                        "Verificar físicamente y en consola; no contabilizar como respaldo hasta cerrar la contradicción."))

    # 5) Área inconsistente
    for _, r in df_estado.iterrows():
        if _area_inconsistente(r["planta"], r["area_sistema"]):
            hallazgos.append(_hallazgo("Área/sistema inconsistente", r,
                                        f"Planta={r['planta']} pero Área/Sistema={r['area_sistema']!r}; confirmar con Operaciones."))

    # 6) Registros sin actualización reciente
    limite = dt.datetime.now() - dt.timedelta(days=DIAS_SIN_ACTUALIZAR_ALERTA)
    for _, r in df_estado.iterrows():
        if not r["fecha_hora"]:
            continue
        try:
            fecha = dt.datetime.fromisoformat(str(r["fecha_hora"]))
        except ValueError:
            continue
        if fecha < limite:
            hallazgos.append(_hallazgo("Sin actualización reciente", r,
                                        f"Última evaluación el {fecha.date()}; revisar y actualizar en el próximo turno."))

    # 7) Equipos sin evaluación
    sin_eval = df_estado[df_estado["fecha_hora"].isna()]
    for _, r in sin_eval.iterrows():
        hallazgos.append(_hallazgo("Sin evaluación registrada", r, "Registrar la primera evaluación del equipo."))

    # 8) TAG PI no validado
    if "pi_disponible" in df_estado.columns:
        pi_pend = df_estado[(df_estado["pi_disponible"] == "Sí") & (df_estado["pi_validado"] != "Sí")]
        for _, r in pi_pend.iterrows():
            hallazgos.append(_hallazgo("TAG PI no validado", r,
                                        "Confirmar mapeo TAG equipo -> TAG PI antes de usarlo en el mapa de calor."))

    # 9) Marcados en el catálogo maestro como "Requiere validación"
    marcados = df_estado[df_estado["requiere_validacion"] == "Sí"]
    for _, r in marcados.iterrows():
        hallazgos.append(_hallazgo("Requiere validación (catálogo maestro)", r,
                                    r.get("observacion_calidad") or "Revisar observación de calidad del levantamiento inicial."))

    if not hallazgos:
        return pd.DataFrame(columns=["tipo", "equipment_id", "tag", "planta", "area_sistema", "detalle", "accion_requerida"])
    return pd.DataFrame(hallazgos).sort_values(["tipo", "planta", "tag"]).reset_index(drop=True)


def _hallazgo(tipo: str, fila: pd.Series, accion: str, extra: str = "") -> dict:
    return {
        "tipo": tipo,
        "equipment_id": fila["equipment_id"],
        "tag": fila["tag"],
        "planta": fila["planta"],
        "area_sistema": fila["area_sistema"],
        "detalle": extra,
        "accion_requerida": accion,
    }
