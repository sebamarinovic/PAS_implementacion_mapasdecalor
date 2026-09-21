"""Generación de informes PDF (ReportLab) — sección 12 y 13 del encargo.

Un único conjunto de funciones sirve tanto para el informe por área como
para el consolidado PAS: la diferencia es sólo el DataFrame que se les pasa
(filtrado por planta o completo).

Diseño: franja de marca superior + pie de página con numeración en cada
hoja (canvas callbacks _encabezado_pie), KPIs como tiles coloreados por
semáforo, dos gráficos vectoriales (reportlab.graphics, sin dependencias
extra) y tablas con ancho fijo + celdas que envuelven texto largo para que
nada se corte ni se salga de la página.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie

from core import analytics, avisos_sap, rules, utils

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

_AZUL = colors.HexColor("#1B2A4A")
_AZUL_CLARO = colors.HexColor("#3E5C8A")
_GRIS_TEXTO = colors.HexColor("#555555")
_GRIS_LINEA = colors.HexColor("#CCCCCC")
_VERDE = colors.HexColor("#2E7D32")
_AMARILLO = colors.HexColor("#F9A825")
_GRIS = colors.HexColor("#9E9E9E")
_ROJO = colors.HexColor("#C62828")

_CRITICIDAD_COLOR = {
    "Operativo": _VERDE, "Degradado": _AMARILLO, "Verificar": _GRIS, "Ruta crítica": _ROJO,
}
_ANCHO_UTIL = 18 * cm  # A4 (21cm) - 1.5cm de margen a cada lado

_STYLES = getSampleStyleSheet()
_STYLES.add(ParagraphStyle(name="PASTitulo", fontSize=19, leading=23, spaceAfter=2, textColor=colors.white, fontName="Helvetica-Bold"))
_STYLES.add(ParagraphStyle(name="PASSubtitulo", fontSize=10, textColor=colors.HexColor("#CBD5E8"), spaceAfter=0))
_STYLES.add(ParagraphStyle(name="PASSeccion", fontSize=13, spaceBefore=16, spaceAfter=6, textColor=_AZUL, fontName="Helvetica-Bold"))
_STYLES.add(ParagraphStyle(name="PASTexto", fontSize=9.5, leading=13))
_STYLES.add(ParagraphStyle(name="PASCelda", fontSize=7.6, leading=9.5, fontName="Helvetica"))
_STYLES.add(ParagraphStyle(name="PASCeldaHead", fontSize=7.8, leading=10, textColor=colors.white, fontName="Helvetica-Bold"))
_STYLES.add(ParagraphStyle(name="PASKpiValor", fontSize=17, leading=20, alignment=TA_CENTER, fontName="Helvetica-Bold", textColor=_AZUL))
_STYLES.add(ParagraphStyle(name="PASKpiLabel", fontSize=8, leading=10, alignment=TA_CENTER, textColor=_GRIS_TEXTO))


def _safe(v) -> str:
    """None/NaN -> '' en vez del literal 'None' (bug detectado en la v1 del informe)."""
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v)


def _fila_color(criticos_pct: float, degradados_pct: float, sin_evaluar_pct: float):
    return colors.HexColor(utils.color_semaforo(criticos_pct, degradados_pct, sin_evaluar_pct))


# ---------------------------------------------------------------------------
# Encabezado / pie de página (se dibujan en el canvas, en cada hoja)
# ---------------------------------------------------------------------------

def _hacer_encabezado_pie(titulo: str, meta: str):
    def _dibujar(canvas, doc):
        canvas.saveState()
        ancho, alto = A4
        # Franja de marca superior
        canvas.setFillColor(_AZUL)
        canvas.rect(0, alto - 2.6 * cm, ancho, 2.6 * cm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(1.5 * cm, alto - 1.55 * cm, titulo)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#CBD5E8"))
        canvas.drawString(1.5 * cm, alto - 2.15 * cm, meta)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(ancho - 1.5 * cm, alto - 1.55 * cm, "PAS · División Chuquicamata")
        canvas.drawRightString(ancho - 1.5 * cm, alto - 1.95 * cm, "GCP-2 · GCP-4 · CAP-3 · CAP-4 · Aguas")

        # Pie de página
        canvas.setStrokeColor(_GRIS_LINEA)
        canvas.line(1.5 * cm, 1.3 * cm, ancho - 1.5 * cm, 1.3 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_GRIS_TEXTO)
        canvas.drawString(1.5 * cm, 0.9 * cm, f"Generado {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · Documento operacional interno")
        canvas.drawRightString(ancho - 1.5 * cm, 0.9 * cm, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()
    return _dibujar


# ---------------------------------------------------------------------------
# KPIs como tiles coloreados
# ---------------------------------------------------------------------------

def _tiles_kpis(kpis: dict) -> Table:
    definiciones = [
        ("Disponibilidad", f"{kpis['disponibilidad_pct']}%", kpis["disponibilidad_pct"] < 70),
        ("Evaluados", f"{kpis['evaluados']}/{kpis['total_equipos']}", False),
        ("Críticos", str(kpis["criticos"]), kpis["criticos"] > 0),
        ("Fuera de servicio", str(kpis["fuera_servicio"]), kpis["fuera_servicio"] > 0),
        ("Pend. validación", str(kpis["pendientes_validacion"]), kpis["pendientes_validacion"] > 0),
        ("Avisos SAP", str(kpis["avisos_sap_abiertos"]), False),
    ]
    valores = [Paragraph(v, _STYLES["PASKpiValor"]) for _, v, _ in definiciones]
    labels = [Paragraph(l.upper(), _STYLES["PASKpiLabel"]) for l, _, _ in definiciones]
    ancho_col = _ANCHO_UTIL / 6
    t = Table([valores, labels], colWidths=[ancho_col] * 6, rowHeights=[1.05 * cm, 0.6 * cm])
    estilos = [
        ("BOX", (0, 0), (-1, -1), 0.6, _GRIS_LINEA),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]
    for i, (_, _, alerta) in enumerate(definiciones):
        if alerta:
            estilos.append(("BACKGROUND", (i, 0), (i, 1), colors.HexColor("#FFF1F1")))
    t.setStyle(TableStyle(estilos))
    return t


# ---------------------------------------------------------------------------
# Mapa de calor (tabla con semáforo de fondo)
# ---------------------------------------------------------------------------

def _tabla_heatmap(df_agg: pd.DataFrame, columna_nombre: str, etiqueta: str) -> Table:
    header = [etiqueta, "N° equipos", "% Disponibilidad", "% Críticos", "% Degradados", "% Sin evaluar"]
    data = [header]
    estilos = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, _GRIS_LINEA),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i, (_, r) in enumerate(df_agg.iterrows(), start=1):
        data.append([
            _safe(r[columna_nombre]), int(r["n_equipos"]), f"{r['disponibilidad_pct']}%",
            f"{r['criticos_pct']}%", f"{r['degradados_pct']}%", f"{r['sin_evaluar_pct']}%",
        ])
        estilos.append(("BACKGROUND", (0, i), (-1, i), _fila_color(r["criticos_pct"], r["degradados_pct"], r["sin_evaluar_pct"])))
    anchos = [_ANCHO_UTIL * f for f in (0.30, 0.14, 0.16, 0.14, 0.13, 0.13)]
    t = Table(data, colWidths=anchos)
    t.setStyle(TableStyle(estilos))
    return t


# ---------------------------------------------------------------------------
# Gráficos vectoriales (reportlab.graphics — sin dependencias adicionales)
# ---------------------------------------------------------------------------

def _grafico_criticidad(df_estado: pd.DataFrame) -> Drawing:
    orden = ["Operativo", "Degradado", "Verificar", "Ruta crítica"]
    counts = df_estado["criticidad"].value_counts()
    valores = [int(counts.get(c, 0)) for c in orden]
    total = sum(valores) or 1

    d = Drawing(_ANCHO_UTIL, 4.6 * cm)
    pie = Pie()
    pie.x, pie.y = 10, 8
    pie.width = pie.height = 4.3 * cm
    pie.data = valores
    pie.labels = None
    pie.simpleLabels = False
    pie.sideLabels = False
    pie.slices.strokeColor = colors.white
    pie.slices.strokeWidth = 1
    for i, c in enumerate(orden):
        pie.slices[i].fillColor = _CRITICIDAD_COLOR[c]
    d.add(pie)

    leyenda_x = 5.6 * cm
    for i, c in enumerate(orden):
        y = 3.6 * cm - i * 0.65 * cm
        d.add(_cuadro_leyenda(leyenda_x, y, _CRITICIDAD_COLOR[c]))
        pct = round(100 * valores[i] / total, 1)
        d.add(_texto(leyenda_x + 0.5 * cm, y, f"{c}: {valores[i]}  ({pct}%)"))
    return d


def _cuadro_leyenda(x, y, color):
    from reportlab.graphics.shapes import Rect
    return Rect(x, y, 0.35 * cm, 0.35 * cm, fillColor=color, strokeColor=None)


def _texto(x, y, texto, size=8.5, color=colors.black):
    from reportlab.graphics.shapes import String
    return String(x, y + 0.05 * cm, texto, fontSize=size, fillColor=color, fontName="Helvetica")


def _grafico_barras_disponibilidad(agg_df: pd.DataFrame, columna_nombre: str) -> Drawing:
    """Barras horizontales de % disponibilidad (nombres de área largos se
    leen mejor en horizontal que en un gráfico de barras vertical)."""
    filas = agg_df.sort_values("disponibilidad_pct").reset_index(drop=True)
    n = len(filas)
    alto = max(3.2, 0.62 * n + 1.0) * cm

    d = Drawing(_ANCHO_UTIL, alto)
    chart = HorizontalBarChart()
    chart.x = 2.6 * cm
    chart.y = 0.4 * cm
    chart.width = _ANCHO_UTIL - 3.4 * cm
    chart.height = alto - 1.0 * cm
    chart.data = [filas["disponibilidad_pct"].tolist()]
    chart.categoryAxis.categoryNames = [str(v)[:18] for v in filas[columna_nombre]]
    chart.categoryAxis.labels.fontSize = 7.5
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 25
    chart.valueAxis.labels.fontSize = 7.5
    chart.bars.strokeColor = None
    chart.barWidth = 8
    chart.groupSpacing = 6
    for i, pct in enumerate(filas["disponibilidad_pct"]):
        color = _VERDE if pct >= 80 else (_AMARILLO if pct >= 50 else _ROJO)
        chart.bars[(0, i)].fillColor = color
    d.add(chart)
    return d


# ---------------------------------------------------------------------------
# Tablas de equipos (con wrap de texto largo, sin desbordar la página)
# ---------------------------------------------------------------------------

def _p(texto: str, encabezado: bool = False) -> Paragraph:
    return Paragraph(_safe(texto), _STYLES["PASCeldaHead"] if encabezado else _STYLES["PASCelda"])


def _tabla_equipos(df: pd.DataFrame, columnas: list[str], encabezados: list[str],
                    anchos_pct: list[float], vacio_texto: str) -> Table | Paragraph:
    if df.empty:
        return Paragraph(vacio_texto, _STYLES["PASTexto"])
    data = [[_p(h, encabezado=True) for h in encabezados]]
    for _, fila in df.iterrows():
        data.append([_p(fila[c]) for c in columnas])
    anchos = [_ANCHO_UTIL * pct for pct in anchos_pct]
    t = Table(data, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
                          df_comparacion: dict | None = None,
                          df_avisos_sap: pd.DataFrame | None = None) -> Path:
    kpis = analytics.kpis_generales(df_estado)
    kpis_planta = analytics.kpis_por_planta(df_estado)

    meta = f"Fecha: {dt.date.today().isoformat()}   ·   Turno: {turno or 'Consolidado'}   ·   Responsable: {responsable or 'No indicado'}"
    dibujar_marco = _hacer_encabezado_pie(titulo, meta)

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                             topMargin=3.1 * cm, bottomMargin=1.7 * cm,
                             leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    story = []

    story.append(Paragraph("Indicadores clave", _STYLES["PASSeccion"]))
    story.append(_tiles_kpis(kpis))

    story.append(Paragraph("Mapa de calor", _STYLES["PASSeccion"]))
    story.append(_tabla_heatmap(agg_df, agg_columna, agg_etiqueta))

    story.append(Paragraph("Distribución de criticidad", _STYLES["PASSeccion"]))
    story.append(_grafico_criticidad(df_estado))

    if len(agg_df) > 1:
        story.append(Paragraph(f"Disponibilidad por {agg_etiqueta.lower()}", _STYLES["PASSeccion"]))
        story.append(_grafico_barras_disponibilidad(agg_df, agg_columna))

    story.append(Paragraph("Resumen ejecutivo", _STYLES["PASSeccion"]))
    story.append(Paragraph(_resumen_ejecutivo(kpis, kpis_planta, redundancia), _STYLES["PASTexto"]))

    story.append(Paragraph("Equipos críticos (Ruta crítica)", _STYLES["PASSeccion"]))
    criticos = df_estado[df_estado["criticidad"] == "Ruta crítica"]
    story.append(_tabla_equipos(
        criticos, ["tag", "planta", "area_sistema", "estado", "disponibilidad", "hallazgo", "aviso_sap"],
        ["TAG", "Planta", "Área", "Estado", "Disponib.", "Hallazgo", "SAP"],
        [0.11, 0.10, 0.15, 0.13, 0.13, 0.30, 0.08],
        "Sin equipos en ruta crítica en el periodo evaluado."))

    story.append(Paragraph("Equipos fuera de servicio", _STYLES["PASSeccion"]))
    fs = df_estado[df_estado["estado"] == "Fuera de servicio"]
    story.append(_tabla_equipos(
        fs, ["tag", "planta", "area_sistema", "disponibilidad", "hallazgo", "aviso_sap"],
        ["TAG", "Planta", "Área", "Disponib.", "Hallazgo", "SAP"],
        [0.12, 0.11, 0.17, 0.14, 0.38, 0.08],
        "Sin equipos fuera de servicio en el periodo evaluado."))

    story.append(Paragraph("Sistemas con pérdida de redundancia", _STYLES["PASSeccion"]))
    sin_respaldo = [g for g in redundancia if g["estado_redundancia"] == "Sin respaldo"]
    pendiente_val = [g for g in redundancia if g["estado_redundancia"] == "Pendiente de validación"]
    if sin_respaldo:
        data = [[_p("Grupo", True), _p("Planta", True), _p("Disponibles", True), _p("Mínimo requerido", True)]]
        for g in sin_respaldo:
            data.append([_p(g["grupo"]), _p(g["planta"]), _p(str(g["n_disponibles"])), _p(str(g["minimo_disponible"]))])
        t = Table(data, colWidths=[_ANCHO_UTIL * f for f in (0.35, 0.25, 0.2, 0.2)])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFCDD2")),
            ("GRID", (0, 0), (-1, -1), 0.4, _GRIS_LINEA),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
        ["TAG", "Planta", "Estado", "Hallazgo"],
        [0.14, 0.14, 0.17, 0.55],
        "Sin hallazgos registrados en el periodo."))

    story.append(Paragraph("Avisos SAP (registrados por el Jefe de Turno)", _STYLES["PASSeccion"]))
    con_sap = df_estado[df_estado["aviso_sap"].fillna("").astype(str).str.strip() != ""]
    story.append(_tabla_equipos(
        con_sap, ["tag", "planta", "estado", "aviso_sap", "ot"],
        ["TAG", "Planta", "Estado", "Aviso SAP", "OT"],
        [0.16, 0.16, 0.2, 0.24, 0.24],
        "Sin avisos SAP abiertos en el periodo."))

    story.append(Paragraph("Avisos SAP (carga masiva de mantenimiento)", _STYLES["PASSeccion"]))
    if df_avisos_sap is not None and not df_avisos_sap.empty:
        tabla_sap = df_avisos_sap.copy()
        tabla_sap["equipo_vinculado"] = tabla_sap.apply(
            lambda r: r["tag"] if pd.notna(r.get("tag"))
            else ("Ambiguo (revisar)" if r.get("match_confianza") == "Ambigua" else "Sin vincular"),
            axis=1)
        tabla_sap["fecha_creado"] = pd.to_datetime(tabla_sap["creado_el"]).dt.strftime("%d-%m-%Y")
        story.append(_tabla_equipos(
            tabla_sap, ["aviso", "descripcion", "fecha_creado", "status_sistema", "equipo_vinculado"],
            ["Aviso", "Descripción", "Creado", "Estado", "Equipo"],
            [0.12, 0.4, 0.13, 0.15, 0.2],
            "Sin avisos SAP cargados para este ámbito."))
        story.append(Paragraph(
            "Fuente: carga masiva desde export SAP (import_avisos_sap.py), filtrada por punto de "
            "trabajo responsable. 'Equipo' indica el TAG del catálogo PAS vinculado por coincidencia "
            "de texto, o 'Sin vincular' cuando el aviso no menciona un TAG identificable — no implica "
            "que el aviso no sea real, sólo que no se pudo asociar automáticamente a un equipo puntual.",
            _STYLES["PASTexto"]))
    else:
        story.append(Paragraph("Sin avisos SAP cargados para este ámbito.", _STYLES["PASTexto"]))

    story.append(Paragraph("Pendientes de validación", _STYLES["PASSeccion"]))
    pend = df_estado[(df_estado["requiere_validacion"] == "Sí") | (df_estado["estado_dato"] != "OK")]
    story.append(_tabla_equipos(
        pend, ["tag", "planta", "estado_dato", "observacion_calidad"],
        ["TAG", "Planta", "Estado del dato", "Observación"],
        [0.13, 0.13, 0.17, 0.57],
        "Sin pendientes de validación."))

    if df_comparacion:
        story.append(Paragraph("Comparación con el periodo anterior", _STYLES["PASSeccion"]))
        texto = (
            f"Nuevos críticos: {len(df_comparacion['nuevos_criticos'])} · "
            f"Recuperados: {len(df_comparacion['recuperados'])} · "
            f"Permanecen críticos: {len(df_comparacion['permanecen_criticos'])} · "
            f"Cambios de disponibilidad: {df_comparacion['cambios_disponibilidad']}"
        )
        story.append(Paragraph(texto, _STYLES["PASTexto"]))

    doc.build(story, onFirstPage=dibujar_marco, onLaterPages=dibujar_marco)
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
    df_sap = avisos_sap.avisos_por_planta(conn, planta)
    return _construir_documento(
        output_path, f"Informe PAS — {nombre_visible}", turno, responsable,
        df_planta, redundancia, agg, "area_sistema", "Área / Sistema", df_comparacion,
        df_avisos_sap=df_sap,
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
    df_sap = avisos_sap.avisos_todos(conn)
    return _construir_documento(
        output_path, "Informe Consolidado PAS", turno, responsable,
        df, redundancia, agg, "planta_visible", "Planta", df_comparacion,
        df_avisos_sap=df_sap,
    )
