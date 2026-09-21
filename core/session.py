"""Helpers compartidos entre páginas Streamlit: conexión cacheada y
widgets repetidos (identificación de turno)."""
from __future__ import annotations

import streamlit as st

from core import database as db
from core import rules, utils


@st.cache_resource
def get_conn():
    conn = db.get_connection()
    db.init_schema(conn)
    return conn


def sidebar_identidad() -> tuple[str, str, str]:
    """Widgets de identificación de turno, visibles en toda la app.
    Se guardan en session_state para no repetir el ingreso entre páginas."""
    st.sidebar.markdown("### Identificación de turno")
    usuario = st.sidebar.text_input(
        "Jefe de Turno / Operador", key="usuario_actual",
        placeholder="Nombre y apellido",
    )
    tipos = rules.load_catalogs()["tipo_turno"]
    default_turno = utils.turno_actual()
    tipo_turno = st.sidebar.selectbox(
        "Tipo de turno", tipos, index=tipos.index(default_turno), key="tipo_turno_actual",
    )
    codigos = rules.load_catalogs()["codigo_turno"]
    codigo_turno = st.sidebar.selectbox("Código turno / cuadrilla", codigos, key="codigo_turno_actual")
    return usuario, tipo_turno, codigo_turno
