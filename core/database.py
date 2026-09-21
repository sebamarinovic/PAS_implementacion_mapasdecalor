"""Capa de acceso a datos SQLite para PAS.

Diseñada para que el resto de la aplicación (páginas Streamlit, reglas,
analítica, informes) nunca escriba SQL directamente. El día que esto se
migre a SharePoint/SQL Server/API corporativa, sólo este archivo debería
cambiar (ver sección 3 y 10 del encargo).

Tablas:
  equipos            -> catálogo maestro (1 fila por equipo, TABLA 1)
  evaluaciones        -> histórico append-only por turno (TABLA 2)
  cierres_turno       -> snapshot/cierre de cada turno (sección 7)
  auditoria           -> trazabilidad de cambios (sección 16)
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS equipos (
    equipment_id        TEXT PRIMARY KEY,
    legacy_id           INTEGER,
    planta              TEXT NOT NULL,
    area_sistema        TEXT NOT NULL,
    tag                 TEXT NOT NULL,
    tipo_elemento       TEXT,
    descripcion         TEXT,
    grupo_redundancia   TEXT,
    rol_grupo           TEXT,
    regla_grupo         TEXT,
    activo              TEXT DEFAULT 'Sí',
    requiere_validacion TEXT DEFAULT 'No',
    observacion_calidad TEXT,
    fuente_origen       TEXT,
    pi_tag              TEXT,
    pi_variable         TEXT,
    pi_unidad           TEXT,
    pi_disponible       TEXT DEFAULT 'No',
    pi_validado         TEXT DEFAULT 'No'
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    evaluation_id   TEXT PRIMARY KEY,
    equipment_id    TEXT NOT NULL REFERENCES equipos(equipment_id),
    fecha_hora      TEXT NOT NULL,
    tipo_turno      TEXT,
    codigo_turno    TEXT,
    usuario         TEXT,
    estado          TEXT,
    disponibilidad  TEXT,
    modo_operacion  TEXT,
    criticidad      TEXT,
    prioridad       TEXT,
    hallazgo        TEXT,
    aviso_sap       TEXT,
    ot              TEXT,
    evidencia       TEXT,
    comentario      TEXT,
    rule_version    TEXT,
    estado_dato     TEXT DEFAULT 'OK',
    fuente          TEXT DEFAULT 'App',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_eval_equipo_fecha
    ON evaluaciones(equipment_id, fecha_hora DESC);

CREATE TABLE IF NOT EXISTS cierres_turno (
    shift_id            TEXT PRIMARY KEY,
    fecha_operacional   TEXT NOT NULL,
    tipo_turno          TEXT NOT NULL,
    codigo_turno        TEXT,
    jefe_responsable    TEXT,
    cobertura_pct       REAL,
    criticos_abiertos   INTEGER,
    pendientes_validar  INTEGER,
    estado_cierre       TEXT DEFAULT 'Cerrado',
    fecha_hora_cierre   TEXT
);

CREATE TABLE IF NOT EXISTS auditoria (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla           TEXT,
    registro_id     TEXT,
    usuario         TEXT,
    fecha_hora      TEXT,
    accion          TEXT,
    campo           TEXT,
    valor_anterior  TEXT,
    valor_nuevo     TEXT
);

CREATE TABLE IF NOT EXISTS avisos_sap (
    aviso                     TEXT PRIMARY KEY,
    prioridad                 TEXT,
    creado_el                 TEXT,
    inicio_deseado            TEXT,
    status_sistema            TEXT,
    status_usuario            TEXT,
    descripcion               TEXT,
    denom_ubicacion_tecnica   TEXT,
    ubicacion_tecnica         TEXT,
    pto_trabajo_responsable   TEXT,
    denominacion_ejecutor     TEXT,
    creado_por                TEXT,
    modificado_el             TEXT,
    modificado_por            TEXT,
    equipment_id              TEXT REFERENCES equipos(equipment_id),
    match_confianza           TEXT DEFAULT 'Sin vincular',
    planta_inferida           TEXT,
    fuente_archivo            TEXT,
    importado_el              TEXT
);
CREATE INDEX IF NOT EXISTS idx_avisos_sap_planta
    ON avisos_sap(planta_inferida);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# EQUIPOS
# ---------------------------------------------------------------------------

def upsert_equipo(conn: sqlite3.Connection, equipo: dict) -> None:
    cols = [
        "equipment_id", "legacy_id", "planta", "area_sistema", "tag",
        "tipo_elemento", "descripcion", "grupo_redundancia", "rol_grupo",
        "regla_grupo", "activo", "requiere_validacion", "observacion_calidad",
        "fuente_origen", "pi_tag", "pi_variable", "pi_unidad", "pi_disponible",
        "pi_validado",
    ]
    valores = [equipo.get(c) for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c != "equipment_id"])
    conn.execute(
        f"""INSERT INTO equipos ({','.join(cols)}) VALUES ({placeholders})
            ON CONFLICT(equipment_id) DO UPDATE SET {updates}""",
        valores,
    )


def get_equipos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM equipos ORDER BY planta, area_sistema, tag").fetchall()


def get_equipo(conn: sqlite3.Connection, equipment_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM equipos WHERE equipment_id = ?", (equipment_id,)
    ).fetchone()


# ---------------------------------------------------------------------------
# EVALUACIONES (append-only: nunca se hace UPDATE ni DELETE)
# ---------------------------------------------------------------------------

def insert_evaluacion(conn: sqlite3.Connection, ev: dict) -> None:
    cols = [
        "evaluation_id", "equipment_id", "fecha_hora", "tipo_turno", "codigo_turno",
        "usuario", "estado", "disponibilidad", "modo_operacion", "criticidad",
        "prioridad", "hallazgo", "aviso_sap", "ot", "evidencia", "comentario",
        "rule_version", "estado_dato", "fuente", "created_at",
    ]
    ev = {**ev}
    ev.setdefault("created_at", now_iso())
    valores = [ev.get(c) for c in cols]
    conn.execute(
        f"INSERT INTO evaluaciones ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        valores,
    )


def get_evaluaciones_df(conn: sqlite3.Connection):
    """Todas las evaluaciones como DataFrame (para análisis con pandas)."""
    import pandas as pd  # import local: database.py no depende de pandas en el resto del módulo
    return pd.read_sql_query("SELECT * FROM evaluaciones", conn)


def get_historial_equipo(conn: sqlite3.Connection, equipment_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM evaluaciones WHERE equipment_id = ? ORDER BY fecha_hora ASC, evaluation_id ASC",
        (equipment_id,),
    ).fetchall()


def siguiente_evaluation_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT evaluation_id FROM evaluaciones WHERE evaluation_id LIKE 'EV-%' ORDER BY evaluation_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "EV-000001"
    try:
        n = int(row["evaluation_id"].split("-")[-1])
    except ValueError:
        n = 0
    return f"EV-{n + 1:06d}"


# ---------------------------------------------------------------------------
# CIERRES DE TURNO
# ---------------------------------------------------------------------------

def insert_cierre_turno(conn: sqlite3.Connection, cierre: dict) -> None:
    cols = [
        "shift_id", "fecha_operacional", "tipo_turno", "codigo_turno",
        "jefe_responsable", "cobertura_pct", "criticos_abiertos",
        "pendientes_validar", "estado_cierre", "fecha_hora_cierre",
    ]
    valores = [cierre.get(c) for c in cols]
    conn.execute(
        f"INSERT INTO cierres_turno ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
        valores,
    )


def get_cierres_turno(conn: sqlite3.Connection, limite: int = 30) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM cierres_turno ORDER BY fecha_hora_cierre DESC LIMIT ?", (limite,)
    ).fetchall()


def siguiente_shift_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT shift_id FROM cierres_turno WHERE shift_id LIKE 'SHIFT-%' ORDER BY shift_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return "SHIFT-000001"
    n = int(row["shift_id"].split("-")[-1])
    return f"SHIFT-{n + 1:06d}"


# ---------------------------------------------------------------------------
# AUDITORÍA
# ---------------------------------------------------------------------------

def log_auditoria(conn: sqlite3.Connection, tabla: str, registro_id: str, usuario: str,
                   accion: str, campo: str = "", valor_anterior: str = "", valor_nuevo: str = "") -> None:
    conn.execute(
        """INSERT INTO auditoria (tabla, registro_id, usuario, fecha_hora, accion, campo, valor_anterior, valor_nuevo)
           VALUES (?,?,?,?,?,?,?,?)""",
        (tabla, registro_id, usuario, now_iso(), accion, campo, valor_anterior, valor_nuevo),
    )


def get_auditoria(conn: sqlite3.Connection, limite: int = 200) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM auditoria ORDER BY fecha_hora DESC LIMIT ?", (limite,)
    ).fetchall()


# ---------------------------------------------------------------------------
# AVISOS SAP (carga masiva desde exportación SAP, ver import_avisos_sap.py)
# ---------------------------------------------------------------------------

def upsert_aviso_sap(conn: sqlite3.Connection, aviso: dict) -> None:
    cols = [
        "aviso", "prioridad", "creado_el", "inicio_deseado", "status_sistema",
        "status_usuario", "descripcion", "denom_ubicacion_tecnica", "ubicacion_tecnica",
        "pto_trabajo_responsable", "denominacion_ejecutor", "creado_por", "modificado_el",
        "modificado_por", "equipment_id", "match_confianza", "planta_inferida",
        "fuente_archivo", "importado_el",
    ]
    valores = [aviso.get(c) for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c != "aviso"])
    conn.execute(
        f"""INSERT INTO avisos_sap ({','.join(cols)}) VALUES ({placeholders})
            ON CONFLICT(aviso) DO UPDATE SET {updates}""",
        valores,
    )


def get_avisos_sap_df(conn: sqlite3.Connection):
    import pandas as pd
    return pd.read_sql_query("SELECT * FROM avisos_sap", conn)
