"""Generación de informes PDF (ReportLab) — sección 12 y 13 del encargo.

Un único conjunto de funciones sirve tanto para el informe por área como
para el consolidado PAS: la diferencia es sólo el DataFrame que se les pasa
(filtrado por planta o completo).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from core import analytics, rules, utils

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

_STYLES = getSampleStyleSheet()
_STYLES.add(ParagraphStyle(name="PASTitulo", fontSize=18, leading=22, spaceAfter=6, textColor=colors.HexColor("#1B2A4A")))
_STYLES.add(ParagraphStyle(name="PASSubtitulo", fontSize=11, textColor=colors.HexColor("#555555"), spaceAfter=12))
_STYLES.add(ParagraphStyle(name="PASSeccion", fontSize=13, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#1B2A4A")))
_STYLES.add(ParagraphStyle(name="PASTexto", fontSize=9.5, leading=13))

_COLOR_ROJO = colors.HexColor("#FFCDD2")


def _fila_color(criticos_pct: float, degradados_pct: float, sin_evaluar_pct: float):
    return colors.HexColor(utils.color_semaforo(criticos_pct, degradados_pct, sin_evaluar_pct))


def _tabla_kpis(kpis: dict) -> Table:
    data = [
        ["Disponibilidad", "Evaluados", "Críticos", "Fuera de servicio", "Pend. validación", "Avisos SAP"],
        [
            f"{kpis['disponibilidad_pct']}%",
            f"{kpis['evaluados']}/{kpis['total_equipos']}",
            kpis["criticos"],
            kpis["fuera_servicio"],
            kpis["pendientes_validacion"],
            kpis["avisos_sap_abiertos"],
        ],
    ]
    t = Table(data, colWidths=[2.9 * cm] * 6)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 13),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _tabla_heatmap(df_agg: pd.DataFrame, columna_nombre: str, etiqueta: str) -> Table:
    header = [etiqueta, "N° equipos", "% Disponibilidad", "% Críticos", "% Degradados", "% Sin evaluar"]
    data = [header]
    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]
    for i, (_, r) in enumerate(df_agg.iterrows(), start=1):
        data.append([
            r[columna_nombre], int(r["n_equipos"]), f"{r['disponibilidad_pct']}%",
            f"{r['criticos_pct']}%", f"{r['degradados_pct']}%", f"{r['sin_evaluar_pct']}%",
        ])
        estilos.append(("BACKGROUND", (0, i), (-1, i), _fila_color(r["criticos_pct"], r["degradados_pct"], r["sin_evaluar_pct"])))
    t = Table(data, colWidths=[4.2 * cm, 2.3 * cm, 2.8 * cm, 2.3 * cm, 2.5 * cm, 2.5 * cm])
    t.setStyle(TableStyle(estilos))
    return t


def _tabla_equipos(df: pd.DataFrame, columnas: list[str], encabezados: list[str], vacio_texto: str) -> Table | Paragraph:
    if df.empty:
        return Paragraph(vacio_texto, _STYLES["PASTexto"])
    data = [encabezados] + df[columnas].astype(str).values.tolist()
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6FA")]),
    ]))
    return t


def _resumen_ejecutivo(kpis: dict, kpis_planta: pd.DataFrame, redundancia: list[dict]) -> str:
    if kpis_planta.empty:
        peor = None
    else:
        peor = kpis_planta.sort_values("criticos_pct", ascending=False).iloc[0]

    partes = []
    if peor is not None and peor["criticos_pct"] > 0:
        partes.append(
            f"{peor['planta_visible']} presenta la mayor concentración de condiciones críticas del "
            f"periodo, con {peor['criticos_n']} equipo(s) en ruta crítica sobre {peor['n_equipos']} evaluados."
        )
    else:
        partes.append("No se observan concentraciones críticas relevantes en el periodo evaluado.")

    pendientes_grupo = [g for g in redundancia if g["estado_redundancia"] == "Pendiente de validación"]
    if pendientes_grupo:
        partes.append(
            f"Existen {len(pendientes_grupo)} grupo(s) de redundancia cuya regla operacional aún "
            "no ha sido validada por Operaciones; se recomienda priorizar su revisión."
        )
    if kpis["pendientes_validacion"] > 0:
        partes.append(
            f"Se registran {kpis['pendientes_validacion']} equipo(s) con datos pendientes de "
            "validación (duplicados, contradicciones u observaciones de calidad abiertas)."
        )
    return " ".join(partes)


def _construir_documento(output_path: Path, titulo: str, turno: str | None, responsable: str | None,
                          df_estado: pd.DataFrame, redundancia: list[dict],
                          agg_df: pd.DataFrame, agg_columna: str, agg_etiqueta: str,
                          df_comparacion: dict | None = None) -> Path:
    kpis = analytics.kpis_generales(df_estado)
    kpis_planta = analytics.kpis_por_planta(df_estado)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                             topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    story = []
    story.append(Paragraph(titulo, _STYLES["PASTitulo"]))
    meta = f"Fecha: {dt.date.today().isoformat()}  |  Turno: {turno or 'Consolidado'}  |  Responsable: {responsable or 'No indicado'}"
    story.append(Paragraph(meta, _STYLES["PASSubtitulo"]))

    story.append(Paragraph("Indicadores clave", _STYLES["PASSeccion"]))
    story.append(_tabla_kpis(kpis))

    story.append(Paragraph("Mapa de calor", _STYLES["PASSeccion"]))
    story.append(_tabla_heatmap(agg_df, agg_columna, agg_etiqueta))

    story.append(Paragraph("Resumen ejecutivo", _STYLES["PASSeccion"]))
    story.append(Paragraph(_resumen_ejecutivo(kpis, kpis_planta, redundancia), _STYLES["PASTexto"]))

    story.append(Paragraph("Equipos críticos (Ruta crítica)", _STYLES["PASSeccion"]))
    criticos = df_estado[df_estado["criticidad"] == "Ruta crítica"]
    story.append(_tabla_equipos(
        criticos, ["tag", "planta", "area_sistema", "estado", "disponibilidad", "hallazgo", "aviso_sap"],
        ["TAG", "Planta", "Área", "Estado", "Disponibilidad", "Hallazgo", "SAP"],
        "Sin equipos en ruta crítica en el periodo evaluado."))

    story.append(Paragraph("Equipos fuera de servicio", _STYLES["PASSeccion"]))
    fs = df_estado[df_estado["estado"] == "Fuera de servicio"]
    story.append(_tabla_equipos(
        fs, ["tag", "planta", "area_sistema", "disponibilidad", "hallazgo", "aviso_sap"],
        ["TAG", "Planta", "Área", "Disponibilidad", "Hallazgo", "SAP"],
        "Sin equipos fuera de servicio en el periodo evaluado."))

    story.append(Paragraph("Sistemas con pérdida de redundancia", _STYLES["PASSeccion"]))
    sin_respaldo = [g for g in redundancia if g["estado_redundancia"] == "Sin respaldo"]
    pendiente_val = [g for g in redundancia if g["estado_redundancia"] == "Pendiente de validación"]
    if sin_respaldo:
        data = [["Grupo", "Planta", "Disponibles", "Mínimo requerido"]]
        for g in sin_respaldo:
            data.append([g["grupo"], g["planta"], g["n_disponibles"], g["minimo_disponible"]])
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), _COLOR_ROJO),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Sin pérdida de redundancia confirmada en grupos ya validados.", _STYLES["PASTexto"]))
    story.append(Paragraph(
        f"Nota: {len(pendiente_val)} grupo(s) de redundancia tienen su regla operacional "
        "'Pendiente de validación' y no se clasifican automáticamente (ver Administración / Reglas).",
        _STYLES["PASTexto"]))

    story.append(Paragraph("Hallazgos relevantes", _STYLES["PASSeccion"]))
    con_hallazgo = df_estado[df_estado["hallazgo"].fillna("").astype(str).str.strip() != ""]
    story.append(_tabla_equipos(
        con_hallazgo, ["tag", "planta", "estado", "hallazgo"],
        ["TAG", "Planta", "Estado", "Hallazgo"], "Sin hallazgos registrados en el periodo."))

    story.append(Paragraph("Avisos SAP", _STYLES["PASSeccion"]))
    con_sap = df_estado[df_estado["aviso_sap"].fillna("").astype(str).str.strip() != ""]
    story.append(_tabla_equipos(
        con_sap, ["tag", "planta", "estado", "aviso_sap", "ot"],
        ["TAG", "Planta", "Estado", "Aviso SAP", "OT"], "Sin avisos SAP abiertos en el periodo."))

    story.append(Paragraph("Pendientes de validación", _STYLES["PASSeccion"]))
    pend = df_estado[(df_estado["requiere_validacion"] == "Sí") | (df_estado["estado_dato"] != "OK")]
    story.append(_tabla_equipos(
        pend, ["tag", "planta", "estado_dato", "observacion_calidad"],
        ["TAG", "Planta", "Estado del dato", "Observación"], "Sin pendientes de validación."))

    if df_comparacion:
        story.append(Paragraph("Comparación con el periodo anterior", _STYLES["PASSeccion"]))
        texto = (
            f"Nuevos críticos: {len(df_comparacion['nuevos_criticos'])} · "
            f"Recuperados: {len(df_comparacion['recuperados'])} · "
            f"Permanecen críticos: {len(df_comparacion['permanecen_criticos'])} · "
            f"Cambios de disponibilidad: {df_comparacion['cambios_disponibilidad']}"
        )
        story.append(Paragraph(texto, _STYLES["PASTexto"]))

    doc.build(story)
    return output_path


def informe_area(conn, planta: str, responsable: str | None = None, turno: str | None = None,
                  df_comparacion: dict | None = None) -> Path:
    df = analytics.build_estado_df(conn)
    df_planta = df[df["planta"] == planta].copy()
    equipos = df.to_dict("records")
    ultimas = {r["equipment_id"]: r for r in df.to_dict("records")}
    redundancia = rules.evaluate_redundancy(equipos, ultimas)
    redundancia = [g for g in redundancia if g["planta"] == planta]
    agg = analytics.heatmap_area_df(df_planta)

    catalogos = rules.load_catalogs()
    nombre_visible = catalogos.get("plantas_nombre_visible", {}).get(planta, planta)
    fecha = dt.date.today().strftime("%Y%m%d")
    output_path = REPORTS_DIR / f"Informe_{utils.slug(planta)}_{fecha}.pdf"
    return _construir_documento(
        output_path, f"Informe PAS — {nombre_visible}", turno, responsable,
        df_planta, redundancia, agg, "area_sistema", "Área / Sistema", df_comparacion,
    )


def informe_consolidado(conn, responsable: str | None = None, turno: str | None = None,
                         df_comparacion: dict | None = None) -> Path:
    df = analytics.build_estado_df(conn)
    equipos = df.to_dict("records")
    ultimas = {r["equipment_id"]: r for r in equipos}
    redundancia = rules.evaluate_redundancy(equipos, ultimas)
    agg = analytics.kpis_por_planta(df)

    fecha = dt.date.today().strftime("%Y%m%d")
    output_path = REPORTS_DIR / f"Informe_Consolidado_PAS_{fecha}.pdf"
    return _construir_documento(
        output_path, "Informe Consolidado PAS", turno, responsable,
        df, redundancia, agg, "planta_visible", "Planta", df_comparacion,
    )
