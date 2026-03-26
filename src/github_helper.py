"""
github_helper.py — Commit di file nel repo GitHub per persistenza su Streamlit Cloud.
Se GITHUB_TOKEN non è disponibile, scrive solo su filesystem locale.
"""

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent


def _get_repo():
    try:
        from github import Github
        token = st.secrets["GITHUB_TOKEN"]
        repo_name = st.secrets["GITHUB_REPO"]
        return Github(token).get_repo(repo_name)
    except Exception:
        return None


def commit_file(repo_path: str, content: str, message: str) -> bool:
    """
    Scrive `content` nel file `repo_path` (relativo alla root del repo)
    e committa su GitHub. Ritorna True se il commit è riuscito,
    False se ha scritto solo localmente.
    """
    # Scrivi sempre anche in locale
    local_path = ROOT / repo_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding="utf-8")

    repo = _get_repo()
    if repo is None:
        return False  # solo locale

    try:
        try:
            existing = repo.get_contents(repo_path)
            repo.update_file(repo_path, message, content, existing.sha)
        except Exception:
            repo.create_file(repo_path, message, content)
        return True
    except Exception as e:
        st.warning(f"Salvataggio locale OK, ma commit GitHub fallito: {e}")
        return False


def read_file(repo_path: str) -> str | None:
    """
    Legge il contenuto di un file dal repo GitHub.
    Fallback: legge dal filesystem locale.
    """
    repo = _get_repo()
    if repo is not None:
        try:
            return repo.get_contents(repo_path).decoded_content.decode("utf-8")
        except Exception:
            pass

    local_path = ROOT / repo_path
    if local_path.exists():
        return local_path.read_text(encoding="utf-8")
    return None
