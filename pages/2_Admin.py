"""
pages/2_Admin.py — Pagina di amministrazione: upload PDF, verifica dati, override.
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st

from auth_helper import require_login
from github_helper import commit_file

st.set_page_config(page_title="Admin — Buste Paga", page_icon="⚙️", layout="wide")
require_login()

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
DATA_FILE = ROOT / "data" / "payslips.json"
OVERRIDES_FILE = ROOT / "data" / "overrides.json"
DOC_DIR = ROOT / "doc"

ANAGRAFICA_COLS = ["nome", "azienda", "livello", "ccnl", "data_assunzione", "codice_fiscale"]
ANAGRAFICA_LABELS = {
    "nome": "Nome",
    "azienda": "Azienda",
    "livello": "Livello",
    "ccnl": "CCNL",
    "data_assunzione": "Data assunzione",
    "codice_fiscale": "Codice fiscale",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_payslips() -> list[dict]:
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_payslips(records: list[dict]):
    content = json.dumps(records, ensure_ascii=False, indent=2)
    commit_file("data/payslips.json", content, "Admin: aggiorna payslips.json")
    st.cache_data.clear()


def load_overrides() -> dict:
    if OVERRIDES_FILE.exists():
        with open(OVERRIDES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_overrides(overrides: dict):
    content = json.dumps(overrides, ensure_ascii=False, indent=2)
    commit_file("data/overrides.json", content, "Admin: aggiorna overrides.json")
    st.cache_data.clear()


def merge_overrides(record: dict, overrides: dict) -> dict:
    """Applica gli override a un singolo record."""
    result = dict(record)
    for col, val in overrides.get("global", {}).items():
        if not result.get(col):
            result[col] = val
    for col, val in overrides.get(record.get("periodo", ""), {}).items():
        result[col] = val
    return result


def record_status(record: dict) -> tuple[str, str]:
    """Ritorna (emoji, testo) sullo stato dell'anagrafica."""
    missing = [ANAGRAFICA_LABELS[c] for c in ANAGRAFICA_COLS if not record.get(c)]
    if not missing:
        return "✅", "OK"
    return "⚠️", f"Mancanti: {', '.join(missing)}"


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("## ⚙️ Amministrazione — Buste Paga")
st.divider()

tab_upload, tab_docs, tab_dipendente, tab_override = st.tabs([
    "📤 Upload PDF", "📋 Documenti", "👤 Dati dipendente", "🔧 Override attivi"
])

# ===========================================================================
# TAB 1 — Upload PDF
# ===========================================================================
with tab_upload:
    st.markdown("### Carica nuove buste paga")

    anno_upload = st.selectbox(
        "Anno di riferimento",
        options=list(range(2022, 2030)),
        index=list(range(2022, 2030)).index(2026),
        key="anno_upload",
    )

    uploaded_files = st.file_uploader(
        "Seleziona PDF (puoi caricare più file)",
        type="pdf",
        accept_multiple_files=True,
        key="pdf_uploader",
    )

    if uploaded_files:
        import parser as p

        previews = []
        for uf in uploaded_files:
            # Salva temporaneamente per il parsing
            tmp_dir = Path(tempfile.mkdtemp())
            tmp_path = tmp_dir / uf.name
            tmp_path.write_bytes(uf.read())

            result = p.parse_payslip(str(tmp_path))

            if result:
                previews.append((uf.name, result, tmp_path))
                emoji, stato = record_status(result)
                st.success(
                    f"**{uf.name}** — {result['periodo']} — "
                    f"netto €{result['netto']:,.0f} lordo €{result['lordo']:,.0f} — {emoji} {stato}"
                )
            else:
                st.error(f"**{uf.name}** — parsing fallito: nessun dato estratto.")

        if previews:
            st.divider()
            if st.button("Conferma e salva", type="primary", key="btn_save_upload"):
                records = load_payslips()
                by_period = {r["periodo"]: r for r in records}

                saved = 0
                for fname, result, tmp_path in previews:
                    by_period[result["periodo"]] = result
                    # Copia il PDF nella cartella doc/{anno}
                    dest_dir = DOC_DIR / str(anno_upload)
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    (dest_dir / fname).write_bytes(tmp_path.read_bytes())
                    saved += 1

                new_records = sorted(by_period.values(), key=lambda x: (x["anno"], x["mese_num"]))
                save_payslips(new_records)
                st.success(f"{saved} cedolino/i salvati con successo.")
                st.rerun()


# ===========================================================================
# TAB 2 — Documenti
# ===========================================================================
with tab_docs:
    st.markdown("### Elenco cedolini estratti")

    records = load_payslips()
    overrides = load_overrides()

    if not records:
        st.info("Nessun cedolino trovato. Carica dei PDF nel tab Upload.")
    else:
        rows = []
        for r in reversed(records):  # più recenti in cima
            merged = merge_overrides(r, overrides)
            emoji, stato = record_status(merged)
            rows.append({
                "Periodo": r["periodo"],
                "Mese": r.get("mese", ""),
                "Anno": r.get("anno", ""),
                "Nome": merged.get("nome", ""),
                "Azienda": merged.get("azienda", ""),
                "Livello": merged.get("livello", ""),
                "Stato": f"{emoji} {stato}",
                "_periodo": r["periodo"],
            })

        df_docs = pd.DataFrame(rows)
        st.dataframe(
            df_docs.drop(columns=["_periodo"]),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.markdown("#### Re-parse di un cedolino")
        st.caption("Disponibile solo se il PDF è presente nella cartella doc/ locale.")

        periodi_disponibili = []
        for r in records:
            anno = r.get("anno", "")
            pdf_dir = DOC_DIR / str(anno)
            if pdf_dir.exists() and any(pdf_dir.glob("*.pdf")):
                periodi_disponibili.append(r["periodo"])

        if periodi_disponibili:
            periodo_sel = st.selectbox("Seleziona periodo", periodi_disponibili, key="reparse_periodo")

            if st.button("Esegui re-parse", key="btn_reparse"):
                import parser as p
                record_orig = next((r for r in records if r["periodo"] == periodo_sel), None)
                anno_sel = record_orig["anno"] if record_orig else None
                pdf_dir = DOC_DIR / str(anno_sel)
                pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []

                found = None
                for pdf in pdf_files:
                    parsed = p.parse_payslip(str(pdf))
                    if parsed and parsed["periodo"] == periodo_sel:
                        found = parsed
                        break

                if found:
                    st.success(f"Re-parse completato: netto €{found['netto']:,.0f} lordo €{found['lordo']:,.0f}")
                    emoji, stato = record_status(found)
                    st.info(f"Stato anagrafica: {emoji} {stato}")

                    if st.button("Sostituisci record esistente", key="btn_confirm_reparse"):
                        by_period = {r["periodo"]: r for r in records}
                        by_period[periodo_sel] = found
                        new_records = sorted(by_period.values(), key=lambda x: (x["anno"], x["mese_num"]))
                        save_payslips(new_records)
                        st.success("Record aggiornato.")
                        st.rerun()
                else:
                    st.error(f"Nessun PDF trovato per il periodo {periodo_sel} in {pdf_dir}")
        else:
            st.info("Nessun PDF trovato in doc/. Carica i PDF tramite il tab Upload per abilitare il re-parse.")


# ===========================================================================
# TAB 3 — Dati dipendente
# ===========================================================================
with tab_dipendente:
    st.markdown("### Dati anagrafici — verifica e correzione")

    records = load_payslips()
    overrides = load_overrides()

    if not records:
        st.info("Nessun dato disponibile.")
    else:
        # Prendi l'ultimo record come base, con override applicati
        last_record = merge_overrides(records[-1], overrides)
        global_ov = overrides.get("global", {})

        st.caption("I valori mostrati vengono dall'ultimo cedolino, con eventuali override applicati. Modifica e salva per correggere errori di parsing.")

        col_a, col_b = st.columns(2)
        new_vals = {}
        for i, col in enumerate(ANAGRAFICA_COLS):
            label = ANAGRAFICA_LABELS[col]
            current = global_ov.get(col) or last_record.get(col, "")
            container = col_a if i % 2 == 0 else col_b
            new_vals[col] = container.text_input(label, value=current, key=f"anag_{col}")

        st.divider()
        applica_a = st.radio(
            "Applica a",
            ["Tutti i cedolini (global)", "Solo un periodo specifico"],
            key="applica_radio",
        )

        periodo_specifico = None
        if applica_a == "Solo un periodo specifico":
            periodi = [r["periodo"] for r in records]
            periodo_specifico = st.selectbox("Periodo", periodi, key="anag_periodo")

        if st.button("Salva correzioni", type="primary", key="btn_save_anag"):
            overrides = load_overrides()
            changed = {k: v for k, v in new_vals.items() if v.strip()}

            if applica_a == "Tutti i cedolini (global)":
                overrides["global"] = {**overrides.get("global", {}), **changed}
            else:
                overrides[periodo_specifico] = {**overrides.get(periodo_specifico, {}), **changed}

            save_overrides(overrides)
            st.success("Correzioni salvate e dashboard aggiornata.")
            st.rerun()

        # Mostra confronto parser vs override
        with st.expander("Confronto: parser vs override attivo"):
            rows_cmp = []
            for col in ANAGRAFICA_COLS:
                parser_val = last_record.get(col, "")
                ov_val = global_ov.get(col, "")
                rows_cmp.append({
                    "Campo": ANAGRAFICA_LABELS[col],
                    "Parser": parser_val,
                    "Override": ov_val,
                    "Valore finale": ov_val if ov_val else parser_val,
                })
            st.dataframe(pd.DataFrame(rows_cmp), use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 4 — Override attivi
# ===========================================================================
with tab_override:
    st.markdown("### Override attivi")

    overrides = load_overrides()

    if not overrides:
        st.info("Nessun override attivo.")
    else:
        st.json(overrides)

        st.divider()
        st.markdown("#### Elimina un override")
        chiavi = list(overrides.keys())
        chiave_del = st.selectbox("Chiave da eliminare", chiavi, key="del_override_key")

        if st.button("Elimina", type="secondary", key="btn_del_override"):
            overrides.pop(chiave_del, None)
            save_overrides(overrides)
            st.success(f"Override '{chiave_del}' eliminato.")
            st.rerun()
