#!/usr/bin/env python3
"""Importa un export de avisos SAP (mantenimiento) y los cruza con el
catálogo de equipos PAS, para poder mostrarlos en los informes.

Filtra por "Pto.tbjo.responsable" según config/avisos_sap.yaml
(puntos_trabajo_incluidos) — el resto del archivo se ignora. Por cada
aviso que pasa el filtro:
  - intenta vincularlo a un equipo del catálogo por coincidencia de TAG
    en el texto (core.avisos_sap.match_equipo) -> match_confianza='Alta'
    o 'Sin vincular' (nunca se adivina un TAG que no aparece en el texto).
  - infiere su planta a partir del prefijo de "Ubicación técnica" usando
    el mapeo ya validado en config/avisos_sap.yaml -> planta_inferida, o
    None si el prefijo no tiene evidencia ("Sin identificar planta").

Es seguro volver a ejecutarlo: usa upsert por número de Aviso (idempotente).

Uso:
    python import_avisos_sap.py <ruta_excel.xlsx>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import database as db  # noqa: E402
from core import avisos_sap  # noqa: E402


def _s(valor):
    if pd.isna(valor):
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def main(xlsx_path: str) -> None:
    xlsx_path = Path(xlsx_path)
    cfg = avisos_sap.load_config()
    puntos_incluidos = set(cfg["puntos_trabajo_incluidos"])
    mapeo = cfg["mapeo_ubicacion_tecnica_planta"]

    df = pd.read_excel(xlsx_path, sheet_name="Data")
    df_filtrado = df[df["Pto.tbjo.responsable"].isin(puntos_incluidos)].copy()
    print(f"Avisos totales en el archivo: {len(df)}")
    print(f"Avisos tras filtrar por {sorted(puntos_incluidos)}: {len(df_filtrado)}")

    conn = db.get_connection()
    db.init_schema(conn)
    equipos = [dict(r) for r in db.get_equipos(conn)]
    importado_el = avisos_sap.now_iso()

    n_vinculados = 0
    n_con_planta = 0
    for _, r in df_filtrado.iterrows():
        equipment_id, confianza = avisos_sap.match_equipo(
            r["Descripción"], r["Denom.ubic.técnica"], r["Ubicación técnica"], equipos,
        )
        planta = avisos_sap.inferir_planta(r["Ubicación técnica"], mapeo)
        if equipment_id:
            n_vinculados += 1
        if planta:
            n_con_planta += 1

        db.upsert_aviso_sap(conn, {
            "aviso": _s(r["Aviso"]),
            "prioridad": _s(r["Prioridad"]),
            "creado_el": _s(r["Creado el"]),
            "inicio_deseado": _s(r["Inicio deseado"]),
            "status_sistema": _s(r["Status de sistema"]),
            "status_usuario": _s(r["Status de usuario"]),
            "descripcion": _s(r["Descripción"]),
            "denom_ubicacion_tecnica": _s(r["Denom.ubic.técnica"]),
            "ubicacion_tecnica": _s(r["Ubicación técnica"]),
            "pto_trabajo_responsable": _s(r["Pto.tbjo.responsable"]),
            "denominacion_ejecutor": _s(r["Denominación ejec."]),
            "creado_por": _s(r["Creado por"]),
            "modificado_el": _s(r["Modificado el"]),
            "modificado_por": _s(r["Modificado por"]),
            "equipment_id": equipment_id,
            "match_confianza": confianza,
            "planta_inferida": planta,
            "fuente_archivo": xlsx_path.name,
            "importado_el": importado_el,
        })

    conn.commit()
    print(f"Avisos vinculados a un equipo del catálogo: {n_vinculados}/{len(df_filtrado)}")
    print(f"Avisos con planta identificada: {n_con_planta}/{len(df_filtrado)}")
    print("Listo.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python import_avisos_sap.py <ruta_excel.xlsx>")
        sys.exit(1)
    main(sys.argv[1])
