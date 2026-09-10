"""Componentes visuales compartidos entre páginas Streamlit: tarjetas del
mapa de calor (HTML/CSS, sin recorte de texto) y gráficos Plotly
reutilizados entre Resumen, Mapa de Calor e Historial.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import analytics, utils

CRIT_COLOR = {
    "Operativo": "#2E7D32", "Degradado": "#F9A825", "Verificar": "#9E9E9E", "Ruta crítica": "#C62828",
}


def render_tarjetas_calor(agg_df: pd.DataFrame, columna_nombre: str) -> None:
    """Tarjetas HTML coloreadas por semáforo. Reemplaza el heatmap Plotly
    anterior, cuyo texto en una sola línea se recortaba/superponía entre
    celdas en pantallas angostas."""
    if agg_df.empty:
        st.info("Sin datos para mostrar.")
        return
    # Nota: todo el HTML se arma en líneas únicas, sin indentación. Un
    # bloque indentado dentro de st.markdown(unsafe_allow_html=True) se
    # interpreta como bloque de código Markdown y se muestra como texto
    # crudo en vez de renderizarse (bug real detectado y corregido aquí).
    tarjetas = []
    for _, r in agg_df.sort_values(columna_nombre).iterrows():
        color = utils.color_semaforo(r["criticos_pct"], r["degradados_pct"], r["sin_evaluar_pct"])
        cuerpo = (
            f"Disponibilidad&nbsp;<b>{r['disponibilidad_pct']}%</b><br>"
            f"Críticos&nbsp;<b>{r['criticos_pct']}%</b><br>"
            f"Degradados&nbsp;<b>{r['degradados_pct']}%</b><br>"
            f"Sin evaluar&nbsp;<b>{r['sin_evaluar_pct']}%</b>"
        )
        tarjetas.append(
            f'<div style="flex:1 1 170px;min-width:160px;background:{color};border-radius:10px;'
            f'padding:14px 14px;box-shadow:0 1px 3px rgba(0,0,0,0.15);">'
            f'<div style="font-weight:700;font-size:1.05rem;color:#12213d;">{r[columna_nombre]}</div>'
            f'<div style="font-size:0.78rem;color:#33415c;margin-bottom:10px;">{int(r["n_equipos"])} equipos</div>'
            f'<div style="font-size:0.82rem;line-height:1.65;color:#1a1a1a;">{cuerpo}</div>'
            f'</div>'
        )
    html = '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:6px;">' + "".join(tarjetas) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def grafico_distribucion_criticidad(df: pd.DataFrame) -> go.Figure:
    """Torta (donut) con la distribución PAS por criticidad."""
    valores_dict = analytics.distribucion_criticidad(df)
    orden = [c for c in analytics.CRITICIDAD_ORDEN if valores_dict[c] > 0]
    valores = [valores_dict[c] for c in orden]
    fig = go.Figure(go.Pie(
        labels=orden, values=valores, hole=0.55,
        marker=dict(colors=[CRIT_COLOR[c] for c in orden], line=dict(color="white", width=1)),
        textinfo="percent", hovertemplate="%{label}: %{value} equipos (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    return fig


def grafico_criticidad_por_planta(df: pd.DataFrame) -> go.Figure:
    """Barras apiladas: composición de criticidad de cada planta."""
    tabla = analytics.distribucion_criticidad_por_planta(df)
    fig = go.Figure()
    for c in analytics.CRITICIDAD_ORDEN:
        fig.add_trace(go.Bar(
            name=c, x=tabla["planta_visible"], y=tabla[c],
            marker_color=CRIT_COLOR[c],
            hovertemplate=f"{c}: " + "%{y} equipos<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", height=320, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="N° equipos",
    )
    return fig


def grafico_redundancia(redundancia: list[dict]) -> go.Figure | None:
    """Barras horizontales: equipos disponibles vs. total de miembros por
    grupo de redundancia, coloreadas según su estado."""
    if not redundancia:
        return None
    grupos = [g["grupo"] for g in redundancia]
    miembros = [g["n_miembros"] for g in redundancia]
    disponibles = [g["n_disponibles"] for g in redundancia]
    color_estado = {"Sin respaldo": "#C62828", "Con respaldo": "#2E7D32", "Pendiente de validación": "#9E9E9E"}
    colores = [color_estado.get(g["estado_redundancia"], "#9E9E9E") for g in redundancia]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=grupos, x=miembros, orientation="h", name="Miembros del grupo",
        marker_color="#E3E7EF", hovertemplate="Miembros: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=grupos, x=disponibles, orientation="h", name="Disponibles ahora",
        marker_color=colores, hovertemplate="Disponibles: %{x}<extra></extra>",
    ))
    fig.update_layout(
        barmode="overlay", height=70 + 32 * len(grupos), margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="N° equipos",
    )
    return fig


def grafico_tendencia(tendencia_df: pd.DataFrame) -> go.Figure | None:
    """Línea de tendencia de % disponibilidad y % críticos por fecha
    operacional (sección 13). Con pocos turnos registrados tendrá pocos
    puntos; queda listo para mostrar la evolución real turno a turno."""
    if tendencia_df.empty or len(tendencia_df) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=tendencia_df["fecha"], y=tendencia_df["disponibilidad_pct"],
        mode="lines+markers", name="% Disponibilidad", line=dict(color="#2E7D32", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=tendencia_df["fecha"], y=tendencia_df["criticos_pct"],
        mode="lines+markers", name="% Críticos", line=dict(color="#C62828", width=2),
    ))
    fig.update_layout(
        height=280, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="%", yaxis_range=[0, 100],
    )
    return fig
