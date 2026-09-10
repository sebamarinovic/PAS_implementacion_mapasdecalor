"""Utilidades compartidas: IDs, turnos, formato de fechas, colores de estado."""
from __future__ import annotations

import datetime as dt
import re

TZ_HOUR_DIA_INICIO = 8   # 08:00 inicio turno Día (ajustable si Operaciones define otro horario)
TZ_HOUR_NOCHE_INICIO = 20  # 20:00 inicio turno Noche


def turno_actual(momento: dt.datetime | None = None) -> str:
    """Determina Día/Noche según hora local. Horario 08:00-19:59 = Día, resto Noche.

    Nota: el horario exacto de cambio de turno no está confirmado por
    Operaciones (04_Catalogos sólo valida los nombres Día/Noche, no el
    horario). Se deja como constante fácil de ajustar arriba.
    """
    momento = momento or dt.datetime.now()
    return "Día" if TZ_HOUR_DIA_INICIO <= momento.hour < TZ_HOUR_NOCHE_INICIO else "Noche"


def fecha_operacional(momento: dt.datetime | None = None) -> dt.date:
    momento = momento or dt.datetime.now()
    return momento.date()


def siguiente_id(prefijo: str, ultimo_numero: int, ancho: int = 6) -> str:
    return f"{prefijo}-{ultimo_numero + 1:0{ancho}d}"


_COLOR_MAP = {
    "Operativo": "#2E7D32",       # verde
    "Degradado": "#F9A825",       # amarillo
    "Verificar": "#9E9E9E",       # gris
    "Ruta crítica": "#C62828",    # rojo
    "Pendiente de validación": "#9E9E9E",
}


def color_por_criticidad(criticidad: str) -> str:
    return _COLOR_MAP.get(criticidad, "#9E9E9E")


def slug(texto: str) -> str:
    texto = texto.strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def es_estado_disponible(disponibilidad: str) -> bool:
    return disponibilidad in ("Disponible", "Disponible con restricción")


# Semáforo del mapa de calor (sección 8): mismo criterio para PDF y Streamlit.
_SEMAFORO_VERDE = "#C8E6C9"
_SEMAFORO_AMARILLO = "#FFF3B0"
_SEMAFORO_ROJO = "#FFCDD2"
_SEMAFORO_GRIS = "#E0E0E0"


def color_semaforo(criticos_pct: float, degradados_pct: float, sin_evaluar_pct: float) -> str:
    if criticos_pct and criticos_pct > 0:
        return _SEMAFORO_ROJO
    if degradados_pct and degradados_pct > 0:
        return _SEMAFORO_AMARILLO
    if sin_evaluar_pct and sin_evaluar_pct >= 50:
        return _SEMAFORO_GRIS
    return _SEMAFORO_VERDE
