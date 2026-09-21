"""Motor de reglas operacionales: criticidad individual y redundancia por grupo.

Toda regla vive en config/rules.yaml para que Operaciones pueda revisarla y
ajustarla sin tocar código (sección 9 del encargo). Este módulo sólo sabe
cómo leerla y aplicarla.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import yaml

from core import utils

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    with open(CONFIG_DIR / "rules.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_catalogs() -> dict:
    with open(CONFIG_DIR / "catalogs.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def rule_version() -> str:
    return load_rules().get("rule_version", "0.0.0")


def is_contradiccion(estado: str | None, disponibilidad: str | None) -> bool:
    """Combinaciones estado/disponibilidad que la propia base ya marca como
    inconsistentes (sección 14: 'Equipo Fuera de servicio pero Disponible')."""
    estado = estado or "Sin evaluar"
    disponibilidad = disponibilidad or "Sin evaluar"
    if estado == "Fuera de servicio" and disponibilidad == "Disponible":
        return True
    if estado == "Buena" and disponibilidad == "No disponible":
        return True
    return False


def classify_equipo(estado: str | None, disponibilidad: str | None) -> tuple[str, str, str]:
    """Devuelve (criticidad, prioridad, estado_dato) para un par estado/disponibilidad.

    estado_dato: 'OK' | 'Contradictorio' | 'Pendiente'
    """
    estado = estado or "Sin evaluar"
    disponibilidad = disponibilidad or "Sin evaluar"

    if is_contradiccion(estado, disponibilidad):
        return "Ruta crítica", "P1", "Contradictorio"

    matriz = load_rules().get("clasificacion_individual", {}).get("matriz", [])
    for regla in matriz:
        cond_estado = regla.get("estado")
        cond_disp = regla.get("disponibilidad")
        if cond_estado and cond_estado != estado:
            continue
        if cond_disp and cond_disp != disponibilidad:
            continue
        estado_dato = "Pendiente" if "Sin evaluar" in (estado, disponibilidad) else "OK"
        return regla["criticidad"], regla["prioridad"], estado_dato

    default = load_rules().get("clasificacion_individual", {}).get("default", {})
    return default.get("criticidad", "Verificar"), default.get("prioridad", "P3"), "Pendiente"


def evaluate_redundancy(equipos: list[dict], ultima_evaluacion: dict[str, dict]) -> list[dict]:
    """Calcula el estado de cada grupo de redundancia definido en rules.yaml.

    equipos: filas de la tabla equipos (dict-like) con grupo_redundancia.
    ultima_evaluacion: equipment_id -> fila de evaluación más reciente.

    Retorna una lista de dicts con el detalle por grupo, incluyendo la
    lista de miembros y su disponibilidad actual, para poder hacer drill-down
    en la UI (sección 9 del dashboard PowerBI original).
    """
    grupos_cfg = load_rules().get("grupos_redundancia", {})
    miembros_por_grupo: dict[str, list[dict]] = {}
    for eq in equipos:
        g = eq["grupo_redundancia"]
        if not g:
            continue
        miembros_por_grupo.setdefault(g, []).append(eq)

    resultado = []
    for nombre_grupo, cfg in grupos_cfg.items():
        miembros = miembros_por_grupo.get(nombre_grupo, [])
        detalle_miembros = []
        n_disponibles = 0
        n_evaluados = 0
        for eq in miembros:
            ev = ultima_evaluacion.get(eq["equipment_id"])
            disponibilidad = ev["disponibilidad"] if ev else "Sin evaluar"
            if disponibilidad != "Sin evaluar":
                n_evaluados += 1
            if utils.es_estado_disponible(disponibilidad):
                n_disponibles += 1
            detalle_miembros.append({
                "equipment_id": eq["equipment_id"],
                "tag": eq["tag"],
                "rol_grupo": eq["rol_grupo"],
                "disponibilidad": disponibilidad,
                "estado": ev["estado"] if ev else "Sin evaluar",
            })

        validado = bool(cfg.get("validado", False))
        minimo = cfg.get("minimo_disponible")

        if not validado:
            estado_redundancia = "Pendiente de validación"
        elif minimo is None:
            estado_redundancia = "Pendiente de validación"
        elif n_disponibles < minimo:
            estado_redundancia = "Sin respaldo"
        else:
            estado_redundancia = "Con respaldo"

        resultado.append({
            "grupo": nombre_grupo,
            "planta": cfg.get("planta"),
            "area_sistema": cfg.get("area_sistema"),
            "regla_original": cfg.get("regla_original"),
            "minimo_disponible": minimo,
            "validado": validado,
            "nota": cfg.get("nota", ""),
            "n_miembros": len(miembros),
            "n_disponibles": n_disponibles,
            "n_evaluados": n_evaluados,
            "estado_redundancia": estado_redundancia,
            "miembros": detalle_miembros,
        })
    return resultado
