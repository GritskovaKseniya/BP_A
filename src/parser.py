"""
parser.py — Estrae i dati dalle buste paga PDF e li salva in data/payslips.json
"""

import re
import json
import glob
import os
from pathlib import Path

import PyPDF2

# Mappa mese italiano → numero
MESI = {
    "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
    "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
    "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12,
}


def parse_importo(s: str) -> float:
    """Converte '1.962,00' → 1962.0"""
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_text(pdf_path: str) -> str:
    reader = PyPDF2.PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_anagrafica(text: str) -> dict:
    """Estrae i dati anagrafici del dipendente e dell'azienda dal testo del PDF."""

    # Azienda: riga tipo "000083 TECNEST SRL"
    m = re.search(r"\d{5,6}\s+([A-Z][A-Z0-9 '\.&,]+(?:\s+(?:SRL|SPA|SNC|SS|SAS|SCARL|ONLUS))?)\s*\n", text)
    azienda = m.group(1).strip() if m else ""

    # Nome e codice fiscale: riga tipo "0000091 HRYTSKOVA KSENIIA HRYKSN99T53Z138O"
    m = re.search(r"\d{6,7}\s+([A-Z]+(?:\s+[A-Z]+)+)\s+([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])\b", text)
    nome = m.group(1).strip() if m else ""
    codice_fiscale = m.group(2) if m else ""

    # Data assunzione: seconda data nella coppia "DataNascita DataAssunzione"
    m = re.search(r"\d{2}-\d{2}-\d{4}\s+(\d{2}-\d{2}-\d{4})", text)
    data_assunzione = m.group(1) if m else ""

    # Livello e CCNL: "...IMP Livello C3\nInd.Metalmec FRI"
    m = re.search(r"Livello\s+(\w+)[^\n]*\n([^\n\d][^\n]*)", text)
    livello = m.group(1) if m else ""
    ccnl = m.group(2).strip() if m else ""

    return {
        "nome": nome,
        "codice_fiscale": codice_fiscale,
        "azienda": azienda,
        "data_assunzione": data_assunzione,
        "livello": livello,
        "ccnl": ccnl,
    }


def parse_payslip(pdf_path: str) -> dict | None:
    text = extract_text(pdf_path)

    # --- Periodo ---
    m = re.search(
        r"(Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|"
        r"Settembre|Ottobre|Novembre|Dicembre)\s+(\d{4})(\s+AGG\.?)?",
        text,
    )
    if not m:
        return None
    mese_nome = m.group(1)
    anno = int(m.group(2))
    is_aggiustamento = bool(m.group(3))
    mese_num = MESI[mese_nome]
    periodo = f"{anno}-{mese_num:02d}"

    # --- Netto del mese (ultimo importo seguito da €NNNNNN) ---
    nettos = re.findall(r"([\d\.]+),(\d{2})\s+\N{EURO SIGN}\d+", text)
    netto = parse_importo(nettos[-1][0] + "," + nettos[-1][1]) if nettos else 0.0

    # --- Voci del cedolino ---
    def find_voce(codice: str) -> float:
        """Cerca 'CODICE ... importo' nell'ultima colonna."""
        pattern = rf"{re.escape(codice)}\b[^\n]*?([\d\.]+),(\d{{2}})\s*$"
        hit = re.search(pattern, text, re.MULTILINE)
        if hit:
            return parse_importo(hit.group(1) + "," + hit.group(2))
        return 0.0

    # Retribuzione base mensile
    retribuzione = find_voce("Z00001")

    # 13a mensilità (presente solo a dicembre)
    tredicesima = find_voce("Z50000")

    # Contributo IVS (INPS dipendente)  — formato: "Contributo IVS 2.471,00 % 9,19000 227,08"
    m_ivs = re.search(
        r"Contributo IVS\s+[\d\.]+,\d+\s+%\s+[\d,]+\s+([\d\.]+),(\d{2})", text
    )
    ivs = parse_importo(m_ivs.group(1) + "," + m_ivs.group(2)) if m_ivs else 0.0

    # Contributo CIGS
    m_cigs = re.search(
        r"Contributo CIGS\s+[\d\.]+,\d+\s+%\s+[\d,]+\s+([\d\.]+),(\d{2})", text
    )
    cigs = parse_importo(m_cigs.group(1) + "," + m_cigs.group(2)) if m_cigs else 0.0

    # Imponibile IRPEF
    m_imp = re.search(r"F0[26]000\s+Imponibile.*?([\d\.]+),(\d{2})", text)
    imponibile = parse_importo(m_imp.group(1) + "," + m_imp.group(2)) if m_imp else 0.0

    # IRPEF lorda
    m_irpef_l = re.search(r"F0[26]010\s+IRPEF lorda.*?([\d\.]+),(\d{2})", text)
    irpef_lorda = (
        parse_importo(m_irpef_l.group(1) + "," + m_irpef_l.group(2))
        if m_irpef_l
        else 0.0
    )

    # IRPEF ritenuta netta
    m_irpef = re.search(r"F0[36]020\s+Ritenute IRPEF.*?([\d\.]+),(\d{2})", text)
    irpef = parse_importo(m_irpef.group(1) + "," + m_irpef.group(2)) if m_irpef else 0.0

    # Quota TFR mensile
    m_tfr = re.search(r"Quota T\.F\.R\.\s+([\d\.]+),(\d{2})", text)
    quota_tfr = parse_importo(m_tfr.group(1) + "," + m_tfr.group(2)) if m_tfr else 0.0

    # Fondo TFR al 31/12 (progressivo)
    m_fondo = re.search(r"F\.do 31/12\s+([\d\.]+),(\d{2})", text)
    fondo_tfr = (
        parse_importo(m_fondo.group(1) + "," + m_fondo.group(2)) if m_fondo else 0.0
    )

    # --- Progressivi annuali ---
    m_pinps = re.search(r"Imp\.\s+INPS\s+([\d\.]+),(\d{2})", text)
    prog_inps = (
        parse_importo(m_pinps.group(1) + "," + m_pinps.group(2)) if m_pinps else 0.0
    )

    m_pirpef = re.search(r"Imp\.\s+IRPEF\s+([\d\.]+),(\d{2})", text)
    prog_irpef = (
        parse_importo(m_pirpef.group(1) + "," + m_pirpef.group(2)) if m_pirpef else 0.0
    )

    m_pirpef_p = re.search(r"IRPEF pagata\s+([\d\.]+),(\d{2})", text)
    prog_irpef_pagata = (
        parse_importo(m_pirpef_p.group(1) + "," + m_pirpef_p.group(2))
        if m_pirpef_p
        else 0.0
    )

    # --- Ore e giorni lavorati ---
    # Riga: settimane giorni-ord ore-ord giorni-str ore-str  totale-ore  gg-mese
    m_lavoro = re.search(
        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d\.]+),(\d{2})\s+(\d+)\b", text
    )
    settimane = int(m_lavoro.group(1)) if m_lavoro else 0
    giorni_ord = int(m_lavoro.group(2)) if m_lavoro else 0
    ore_lavorate = parse_importo(m_lavoro.group(5) + "," + m_lavoro.group(6)) if m_lavoro else 0.0
    giorni_mese = int(m_lavoro.group(7)) if m_lavoro else 0

    # --- Ferie ---
    m_ferie = re.search(
        r"Ferie\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+GG\.",
        text,
    )
    ferie_residuo_ap = parse_importo(m_ferie.group(1) + "," + m_ferie.group(2)) if m_ferie else 0.0
    ferie_goduto = parse_importo(m_ferie.group(3) + "," + m_ferie.group(4)) if m_ferie else 0.0
    ferie_maturato = parse_importo(m_ferie.group(5) + "," + m_ferie.group(6)) if m_ferie else 0.0
    ferie_saldo = parse_importo(m_ferie.group(7) + "," + m_ferie.group(8)) if m_ferie else 0.0

    # --- Permessi PAR ---
    m_par = re.search(
        r"Perm\.P\.A\.R\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+([\d\.]+),(\d+)\s+ORE",
        text,
    )
    par_residuo_ap = parse_importo(m_par.group(1) + "," + m_par.group(2)) if m_par else 0.0
    par_goduto = parse_importo(m_par.group(3) + "," + m_par.group(4)) if m_par else 0.0
    par_maturato = parse_importo(m_par.group(5) + "," + m_par.group(6)) if m_par else 0.0
    par_saldo = parse_importo(m_par.group(7) + "," + m_par.group(8)) if m_par else 0.0

    # Lordo = netto + trattenute (IVS + CIGS + IRPEF + addizionali)
    # Usiamo retribuzione utile TFR come proxy del lordo mensile
    m_lorda = re.search(r"Retribuzione utile T\.F\.R\.\s+([\d\.]+),(\d{2})", text)
    lordo = (
        parse_importo(m_lorda.group(1) + "," + m_lorda.group(2)) if m_lorda else 0.0
    )

    anagrafica = extract_anagrafica(text)

    return {
        "periodo": periodo,
        "mese": mese_nome,
        "mese_num": mese_num,
        "anno": anno,
        "is_aggiustamento": is_aggiustamento,
        **anagrafica,
        "netto": netto,
        "lordo": lordo,
        "retribuzione": retribuzione,
        "tredicesima": tredicesima,
        "imponibile_irpef": imponibile,
        "irpef_lorda": irpef_lorda,
        "irpef": irpef,
        "ivs": ivs,
        "cigs": cigs,
        "quota_tfr": quota_tfr,
        "fondo_tfr": fondo_tfr,
        "prog_inps": prog_inps,
        "prog_irpef": prog_irpef,
        "prog_irpef_pagata": prog_irpef_pagata,
        "ore_lavorate": ore_lavorate,
        "giorni_lavorati": giorni_ord,
        "giorni_mese": giorni_mese,
        "ferie_saldo": ferie_saldo,
        "ferie_goduto": ferie_goduto,
        "ferie_maturato": ferie_maturato,
        "par_saldo": par_saldo,
        "par_goduto": par_goduto,
        "par_maturato": par_maturato,
    }


def load_all(doc_dir: str) -> list[dict]:
    pattern = os.path.join(doc_dir, "**", "*.pdf")
    files = glob.glob(pattern, recursive=True)

    raw = []
    for f in files:
        data = parse_payslip(f)
        if data:
            raw.append(data)

    # Deduplica: per ogni periodo tieni l'aggiustamento se presente,
    # altrimenti il cedolino ordinario.
    by_period: dict[str, dict] = {}
    for entry in raw:
        p = entry["periodo"]
        if p not in by_period:
            by_period[p] = entry
        else:
            # Preferisci l'aggiustamento (ha più voci complete per la 13a)
            if entry["is_aggiustamento"]:
                by_period[p] = entry

    # Ordina cronologicamente
    result = sorted(by_period.values(), key=lambda x: (x["anno"], x["mese_num"]))
    return result


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    doc_dir = root / "doc"
    out_file = root / "data" / "payslips.json"
    out_file.parent.mkdir(exist_ok=True)

    records = load_all(str(doc_dir))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Estratti {len(records)} cedolini -> {out_file}")
    for r in records:
        print(
            f"  {r['periodo']}  netto={r['netto']:>8.2f}  lordo={r['lordo']:>8.2f}"
            f"  irpef={r['irpef']:>7.2f}  ivs={r['ivs']:>7.2f}  tfr={r['quota_tfr']:>6.2f}"
        )
