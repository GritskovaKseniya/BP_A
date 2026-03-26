"""
app.py — Entry point: login gate + navigazione.
Avvio: streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Buste Paga",
    page_icon="📊",
    layout="wide",
)

sys.path.insert(0, str(Path(__file__).parent / "src"))
from auth_helper import require_login

require_login()

# Definisce la navigazione — "app" sparisce, rimangono solo le pagine utili
pg = st.navigation(
    [
        st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
        st.Page("pages/2_Admin.py",     title="Amministrazione", icon="⚙️"),
    ],
    position="sidebar",
)
pg.run()
