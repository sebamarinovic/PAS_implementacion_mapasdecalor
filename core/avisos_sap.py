"""Carga y consulta de avisos SAP (mantenimiento) cruzados con el catálogo
de equipos PAS.

Los avisos SAP se cargan por lote desde un export Excel (ver
import_avisos_sap.py) filtrando por "Pto.tbjo.responsable" según
config/avisos_sap.yaml. Cada aviso se intenta vincular a un equipo del
catálogo (match_confianza='Alta') y se infiere su planta a partir del
prefijo de "Ubicación técnica" (planta_inferida) usando el mapeo validado
en el mismo YAML. Cuando no hay evidencia suficiente para ninguna de las
dos cosas, quedan sin vincular / sin identificar — nunca se adivina.
"""
from __future__ import annotations

import re
import datetime as dt
from pathlib import Path

import yaml

from core import database as db

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_config() -> dict:
    with open(CONFIG_DIR / "avisos_sap.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalizar(texto: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(texto or "").upper())


def match_equipo(descripcion: str, denom_ubicacion: str, ubicacion_tecnica: str,
                  equipos: list[dict]) -> tuple[str | None, str]:
    """Busca, entre los equipos del catálogo, si el TAG (normalizado, sin
    guiones/paréntesis) aparece dentro del texto del aviso SAP. Exige TAGs
    de al menos 4 caracteres para evitar falsos positivos.

    Si el texto menciona TAGs de más de un equipo distinto (ej. la
    Descripción nombra un TAG y la Ubicación técnica nombra otro — se vio
    en el archivo real: aviso con "TV-26039" en la descripción pero
    "TV-25039" en la ubicación técnica), no se elige uno arbitrariamente:
    se devuelve sin vincular y confianza='Ambigua' para que quede visible
    en vez de asociarse silenciosamente al TAG equivocado.

    Devuelve (equipment_id o None, 'Alta' | 'Ambigua' | 'Sin vincular')."""
    texto = _normalizar(f"{descripcion} {denom_ubicacion} {ubicacion_tecnica}")
    encontrados = []
    for eq in equipos:
        tag_norm = _normalizar(eq["tag"])
        if tag_norm and len(tag_norm) >= 4 and tag_norm in texto:
            encontrados.append(eq)
    tags_distintos = {e["tag"] for e in encontrados}
    if len(tags_distintos) == 1:
        return encontrados[0]["equipment_id"], "Alta"
    if len(tags_distintos) > 1:
        return None, "Ambigua"
    return None, "Sin vincular"


def inferir_planta(ubicacion_tecnica: str, mapeo: dict) -> str | None:
    """Usa sólo los primeros 3 segmentos de la Ubicación técnica (ej.
    'CHFU-AC-PA3') para buscar en el mapeo validado. Sin match -> None."""
    partes = str(ubicacion_tecnica or "").split("-")
    prefijo = "-".join(partes[:3])
    entrada = mapeo.get(prefijo)
    return entrada["planta"] if entrada else None


def avisos_por_planta(conn, planta: str):
    """DataFrame de avisos SAP cuya planta_inferida coincide, o cuyo equipo
    vinculado pertenece a esa planta (para cubrir el caso en que el TAG
    matcheó un equipo pero el prefijo de ubicación técnica no estaba en el
    mapeo)."""
    import pandas as pd
    df = db.get_avisos_sap_df(conn)
    if df.empty:
        return df
    equipos = pd.read_sql_query("SELECT equipment_id, planta AS planta_equipo, tag FROM equipos", conn)
    df = df.merge(equipos, on="equipment_id", how="left")
    mask = (df["planta_inferida"] == planta) | (df["planta_equipo"] == planta)
    return df[mask].copy()


def avisos_todos(conn):
    """DataFrame con todos los avisos SAP cargados, con la planta del
    equipo vinculado (si existe) como columna 'planta_equipo' adicional a
    'planta_inferida'."""
    import pandas as pd
    df = db.get_avisos_sap_df(conn)
    if df.empty:
        return df
    equipos = pd.read_sql_query("SELECT equipment_id, planta AS planta_equipo, tag FROM equipos", conn)
    return df.merge(equipos, on="equipment_id", how="left")


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")
