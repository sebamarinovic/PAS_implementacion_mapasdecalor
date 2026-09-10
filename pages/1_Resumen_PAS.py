import streamlit as st

from core.session import get_conn, sidebar_identidad
from core import ui_resumen

st.set_page_config(page_title="PAS · Resumen", page_icon="🟢", layout="wide")

sidebar_identidad()
ui_resumen.render(get_conn())
