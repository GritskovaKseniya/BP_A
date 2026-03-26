"""
app.py — Entry point dell'applicazione multi-page.
Avvio: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Buste Paga",
    page_icon="📊",
    layout="wide",
)

# Importa il gate di autenticazione
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from auth_helper import require_login

require_login()

# Se autenticato, mostra landing con navigazione
st.markdown("## 📊 Buste Paga — Benvenuto")
st.markdown("Usa la **sidebar** per navigare tra le sezioni.")

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_Dashboard.py", label="Dashboard", icon="📊")
with col2:
    st.page_link("pages/2_Admin.py", label="Amministrazione", icon="⚙️")
