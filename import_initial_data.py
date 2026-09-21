#!/usr/bin/env python3
"""Importa el levantamiento inicial PAS al SQLite local (sección 17).

Lee data/source/PAS_SharePoint_Implementacion_v1.xlsx (hojas
01_Equipos_Maestro y 02_Evaluaciones_Init), normaliza nombres de columnas
y carga:
  - catálogo maestro de 163 equipos -> tabla `equipos`
  - las 163 evaluaciones iniciales del levantamiento de Leonardo Paredes /
    Eleazar Avendaño -> tabla `evaluaciones` (append-only, idempotente)

REGLAS DE ESTE SCRIPT (no negociables, ver sección 1 y 20 del encargo):
  - NO elimina información existente.
  - NO corrige automáticamente TAGs ni inconsistencias operacionales.
  - Si el dato de origen contradice el catálogo, se importa TAL CUAL y
    queda visible en Control de Calidad (core/validators.py).
  - Es seguro volver a ejecutarlo: el catálogo se actualiza (upsert) y las
    evaluaciones iniciales no se duplican (INSERT OR IGNORE por
    evaluation_id).

Uso:
    python import_initial_data.py [ruta_excel_opcional.xlsx]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import database as db  # noqa: E402
from core import analytics, validators  # noqa: E402

DEFAULT_SOURCE = ROOT / "data" / "source" / "PAS_SharePoint_Implementacion_v1.xlsx"
RULE_VERSION_INICIAL = "levantamiento-inicial-v1"


def _s(valor):
    """Convierte NaN de pandas en None; deja el resto tal cual (no corrige)."""
    if pd.isna(valor):
        return None
    return valor


def cargar_equipos(xlsx_path: Path) -> list[dict]:
    df = pd.read_excel(xlsx_path, sheet_name="01_Equipos_Maestro")
    equipos = []
    for _, r in df.iterrows():
        equipos.append({
            "equipment_id": _s(r["EquipmentID"]),
            "legacy_id": _s(r["LegacyRecordID"]),
            "planta": _s(r["Planta"]),
            "area_sistema": _s(r["AreaSistema"]),
            "tag": _s(r["TAG"]),
            "tipo_elemento": _s(r["TipoElemento"]),
            "descripcion": _s(r["ServicioDescripcion"]),
            "grupo_redundancia": _s(r["GrupoRedundancia"]),
            "rol_grupo": _s(r["RolGrupo"]),
            "regla_grupo": _s(r["ReglaGrupo"]),
            "activo": _s(r["Activo"]) or "Sí",
            "requiere_validacion": _s(r["RequiereValidacion"]) or "No",
            "observacion_calidad": _s(r["ObservacionCalidad"]),
            "fuente_origen": _s(r["FuenteOrigen"]),
            "pi_tag": None,
            "pi_variable": None,
            "pi_unidad": None,
            "pi_disponible": "No",
            "pi_validado": "No",
        })
    return equipos


def cargar_evaluaciones_iniciales(xlsx_path: Path) -> list[dict]:
    df = pd.read_excel(xlsx_path, sheet_name="02_Evaluaciones_Init")
    evaluaciones = []
    for _, r in df.iterrows():
        fecha_eval = _s(r["FechaEvaluacion"])
        fecha_hora = fecha_eval.isoformat() if hasattr(fecha_eval, "isoformat") else str(fecha_eval)

        estado_dato_origen = (_s(r["EstadoDato"]) or "").strip()
        if estado_dato_origen == "Contradictorio":
            estado_dato = "Contradictorio"
        elif estado_dato_origen == "Falta responsable":
            estado_dato = "Falta responsable"
        else:
            estado_dato = "OK"

        usuario = _s(r["EvaluadoPor"]) or "Sin responsable (levantamiento inicial)"

        evaluaciones.append({
            "evaluation_id": _s(r["EvaluationID"]),
            "equipment_id": _s(r["EquipmentID"]),
            "fecha_hora": fecha_hora,
            "tipo_turno": _s(r["TipoTurno"]),
            "codigo_turno": _s(r["CodigoTurno"]),
            "usuario": usuario,
            "estado": _s(r["EstadoActual"]),
            "disponibilidad": _s(r["Disponibilidad"]),
            "modo_operacion": _s(r["ModoOperacion"]),
            "criticidad": _s(r["CriticidadInicial"]),
            "prioridad": _s(r["PrioridadInicial"]),
            "hallazgo": _s(r["Hallazgo"]),
            "aviso_sap": _s(r["OT_SAP"]),
            "ot": None,  # el origen consolida OT y Aviso SAP en un solo campo
            "evidencia": _s(r["EvidenciaURL"]),
            "comentario": None,
            "rule_version": RULE_VERSION_INICIAL,
            "estado_dato": estado_dato,
            "fuente": _s(r["FuenteLevantamiento"]) or "Levantamiento inicial",
        })
    return evaluaciones


def main() -> None:
    xlsx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not xlsx_path.exists():
        print(f"ERROR: no se encontró el archivo fuente: {xlsx_path}")
        sys.exit(1)

    conn = db.get_connection()
    db.init_schema(conn)

    equipos = cargar_equipos(xlsx_path)
    for eq in equipos:
        db.upsert_equipo(conn, eq)
    conn.commit()
    print(f"Equipos cargados/actualizados: {len(equipos)}")

    evaluaciones = cargar_evaluaciones_iniciales(xlsx_path)
    insertadas = 0
    for ev in evaluaciones:
        existe = conn.execute(
            "SELECT 1 FROM evaluaciones WHERE evaluation_id = ?", (ev["evaluation_id"],)
        ).fetchone()
        if existe:
            continue
        db.insert_evaluacion(conn, ev)
        insertadas += 1
    conn.commit()
    print(f"Evaluaciones iniciales insertadas: {insertadas} (de {len(evaluaciones)} en el archivo fuente)")

    df_estado = analytics.build_estado_df(conn)
    hallazgos = validators.run_quality_checks(df_estado)
    print(f"Hallazgos de control de calidad detectados: {len(hallazgos)}")
    if not hallazgos.empty:
        resumen = hallazgos["tipo"].value_counts()
        for tipo, n in resumen.items():
            print(f"  - {tipo}: {n}")

    print(f"\nBase de datos lista en: {db.DB_PATH}")


if __name__ == "__main__":
    main()
