"""Líneas de proceso PAS (gas -> ácido) y su diagrama de mapa de calor.

Los datos viven en config/process_lines.yaml con su procedencia
documentada explícitamente: no forman parte del Excel original, fueron
indicados directamente por Sebastián y una parte (enfriamiento cruzado)
está pendiente de confirmación operacional — ver ese archivo.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import yaml

from core import rules, utils

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "process_lines.yaml"

_GRIS_PENDIENTE = "#9E9E9E"


@lru_cache(maxsize=1)
def load_process_lines() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        datos = yaml.safe_load(f)
    nombres = rules.load_catalogs().get("plantas_nombre_visible", {})
    for linea in datos["lineas_proceso"]:
        linea["etapas_visible"] = [nombres.get(p, p) for p in linea["etapas"]]
    for rel in datos["enfriamiento_cruzado"]:
        rel["enfria_a_visible"] = nombres.get(rel["enfria_a"], rel["enfria_a"])
    return datos


def _color_planta(kpp: pd.DataFrame, planta: str) -> str:
    fila = kpp[kpp["planta"] == planta]
    if fila.empty:
        return _GRIS_PENDIENTE
    r = fila.iloc[0]
    return utils.color_semaforo(r["criticos_pct"], r["degradados_pct"], r["sin_evaluar_pct"])


def _caja(fig: go.Figure, x: float, y: float, w: float, h: float, texto: str, color: str, borde: str = "#33415c"):
    fig.add_shape(
        type="rect", x0=x - w / 2, x1=x + w / 2, y0=y - h / 2, y1=y + h / 2,
        line=dict(color=borde, width=1.5), fillcolor=color, layer="above",
    )
    fig.add_annotation(x=x, y=y, text=f"<b>{texto}</b>", showarrow=False, font=dict(size=13, color="#12213d"))


def _flecha(fig: go.Figure, x0, y0, x1, y1, punteada: bool, color: str, etiqueta: str = ""):
    fig.add_annotation(
        x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1.1, arrowwidth=2, arrowcolor=color,
        text="", standoff=6,
    )
    if etiqueta:
        fig.add_annotation(
            x=(x0 + x1) / 2, y=(y0 + y1) / 2 + 0.28, text=etiqueta, showarrow=False,
            font=dict(size=10, color=color),
        )


_AZUL_ENFRIAMIENTO = "#3E5C8A"


def grafico_lineas_proceso(kpp: pd.DataFrame) -> go.Figure:
    """Diagrama: GCP-2->CAP-3 y GCP-4->CAP-4 (líneas de proceso) + torres
    de enfriamiento cruzado (líneas azules, confirmadas por documentos de
    ingeniería SP916744-53200-48EC-S0001 — ver config/process_lines.yaml)."""
    datos = load_process_lines()
    fig = go.Figure()

    y_linea1, y_linea2 = 4.0, 1.3
    x_gcp, x_cap, x_torre = 1.3, 4.3, 7.3
    caja_w, caja_h = 1.9, 0.9

    _caja(fig, x_gcp, y_linea1, caja_w, caja_h, "GCP-2", _color_planta(kpp, "GCP2"))
    _caja(fig, x_cap, y_linea1, caja_w, caja_h, "CAP-3", _color_planta(kpp, "CAP3"))
    _flecha(fig, x_gcp + caja_w / 2, y_linea1, x_cap - caja_w / 2, y_linea1, punteada=False, color="#1B2A4A")

    _caja(fig, x_gcp, y_linea2, caja_w, caja_h, "GCP-4", _color_planta(kpp, "GCP4"))
    _caja(fig, x_cap, y_linea2, caja_w, caja_h, "CAP-4", _color_planta(kpp, "CAP4"))
    _flecha(fig, x_gcp + caja_w / 2, y_linea2, x_cap - caja_w / 2, y_linea2, punteada=False, color="#1B2A4A")

    # Torres de enfriamiento cruzado (confirmadas por SP916744-53200-48EC-S0001)
    _caja(fig, x_torre, y_linea1, 2.3, 0.75, "Torre Enf. 2/3", "#EDEFF3", borde=_AZUL_ENFRIAMIENTO)
    _caja(fig, x_torre, y_linea2, 2.3, 0.75, "Torre Enf. 4", "#EDEFF3", borde=_AZUL_ENFRIAMIENTO)

    # Cruce: Torre 2/3 enfría CAP-4 (fila inferior); Torre 4 enfría CAP-3 (fila superior)
    fig.add_annotation(
        x=x_cap + caja_w / 2 + 0.05, y=y_linea2, ax=x_torre - 1.15, ay=y_linea1,
        xref="x", yref="y", axref="x", ayref="y", showarrow=True,
        arrowhead=2, arrowsize=1, arrowwidth=1.6, arrowcolor=_AZUL_ENFRIAMIENTO,
        text="", standoff=6,
    )
    fig.add_annotation(
        x=x_cap + caja_w / 2 + 0.05, y=y_linea1, ax=x_torre - 1.15, ay=y_linea2,
        xref="x", yref="y", axref="x", ayref="y", showarrow=True,
        arrowhead=2, arrowsize=1, arrowwidth=1.6, arrowcolor=_AZUL_ENFRIAMIENTO,
        text="", standoff=6,
    )
    fig.add_annotation(
        x=(x_cap + x_torre) / 2 + 0.3, y=(y_linea1 + y_linea2) / 2, text="enfriamiento cruzado · confirmado",
        showarrow=False, font=dict(size=9.5, color=_AZUL_ENFRIAMIENTO), textangle=0,
    )

    fig.update_xaxes(visible=False, range=[0, 9])
    fig.update_yaxes(visible=False, range=[0, 5.3])
    fig.update_layout(
        height=340, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
