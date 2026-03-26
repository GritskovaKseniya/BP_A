"""
auth_helper.py — Login gate con streamlit-authenticator.
"""

from pathlib import Path

import streamlit as st
import yaml

AUTH_FILE = Path(__file__).parent.parent / "auth.yaml"

_authenticator = None


def _get_authenticator():
    global _authenticator
    if _authenticator is not None:
        return _authenticator

    import streamlit_authenticator as stauth

    with open(AUTH_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # La cookie key può essere sovrascritta da st.secrets
    try:
        config["cookie"]["key"] = st.secrets["COOKIE_KEY"]
    except (KeyError, FileNotFoundError):
        pass  # usa la chiave in auth.yaml (ok per sviluppo locale)

    _authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return _authenticator


def require_login():
    """
    Mostra il form di login se l'utente non è autenticato.
    Chiama st.stop() se il login non è andato a buon fine,
    impedendo il rendering del resto della pagina.
    """
    auth = _get_authenticator()

    # Inizializza le chiavi di session state richieste da streamlit-authenticator 0.4.x
    for key in ["logout", "authentication_status", "name", "username"]:
        if key not in st.session_state:
            st.session_state[key] = None

    auth.login()

    status = st.session_state.get("authentication_status")

    if status is True:
        with st.sidebar:
            st.divider()
            st.caption(f"👤 {st.session_state.get('name', '')}")
            auth.logout("Esci", location="sidebar")
        return  # autenticato — lascia continuare la pagina

    if status is False:
        st.error("Credenziali non valide.")

    st.stop()
