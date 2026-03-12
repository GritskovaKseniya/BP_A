"""
dashboard.py — Cruscotto buste paga (Streamlit + Plotly)
Avvio: streamlit run src/dashboard.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configurazione pagina
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Cruscotto Buste Paga",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "payslips.json"
DOC_DIR = ROOT / "doc"

@st.cache_data
def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        # Esegui il parser al volo
        sys.path.insert(0, str(ROOT / "src"))
        import parser as p
        records = p.load_all(str(DOC_DIR))
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        with open(DATA_FILE, encoding="utf-8") as f:
            records = json.load(f)

    df = pd.DataFrame(records)
    df["data"] = pd.to_datetime(df["periodo"] + "-01")
    df["etichetta"] = df["mese"] + " " + df["anno"].astype(str)
    df = df.sort_values("data").reset_index(drop=True)
    return df


df = load_data()

# ---------------------------------------------------------------------------
# Costanti dipendente (dal primo record)
# ---------------------------------------------------------------------------
NOME = "Hrytskova Kseniia"
AZIENDA = "TECNEST SRL"
LIVELLO = "Impiegata C3 — CCNL Ind. Metalmeccanica FRI"
DATA_ASSUNZIONE = "03/10/2022"

# ---------------------------------------------------------------------------
# Stile custom (CSS)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .kpi-box {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }
    .kpi-label { color: #a6adc8; font-size: 13px; margin-bottom: 4px; }
    .kpi-value { color: #cdd6f4; font-size: 26px; font-weight: 700; }
    .kpi-delta { font-size: 12px; margin-top: 4px; }
    .delta-pos { color: #a6e3a1; }
    .delta-neg { color: #f38ba8; }
    .delta-neu { color: #a6adc8; }
    .section-title {
        font-size: 17px;
        font-weight: 600;
        color: #cdd6f4;
        border-left: 4px solid #89b4fa;
        padding-left: 10px;
        margin: 24px 0 12px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_THEME = "plotly_dark"
COLORS = {
    "netto": "#a6e3a1",
    "lordo": "#89b4fa",
    "irpef": "#f38ba8",
    "ivs": "#fab387",
    "tfr": "#f9e2af",
    "ferie": "#89dceb",
    "par": "#cba6f7",
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(f"## 📊 Cruscotto Buste Paga — {NOME}")
col_h1, col_h2, col_h3, col_h4 = st.columns(4)
col_h1.markdown(f"**Azienda:** {AZIENDA}")
col_h2.markdown(f"**Livello:** {LIVELLO}")
col_h3.markdown(f"**Data assunzione:** {DATA_ASSUNZIONE}")
col_h4.markdown(f"**Cedolini analizzati:** {len(df)}")

st.divider()

# ---------------------------------------------------------------------------
# Filtro anno (sidebar)
# ---------------------------------------------------------------------------
anni = sorted(df["anno"].unique())
anni_sel = st.sidebar.multiselect("Anno", anni, default=anni)
df_f = df[df["anno"].isin(anni_sel)].copy()

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------

def kpi_card(label: str, value: float, prev: float | None = None, fmt: str = "€{:.2f}") -> str:
    v_str = fmt.format(value)
    delta_html = ""
    if prev is not None and prev > 0:
        diff = value - prev
        pct = diff / prev * 100
        arrow = "▲" if diff >= 0 else "▼"
        cls = "delta-pos" if diff >= 0 else "delta-neg"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {abs(diff):,.2f} ({pct:+.1f}%)</div>'
    return (
        f'<div class="kpi-box">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{v_str}</div>'
        f'{delta_html}'
        f"</div>"
    )


ultimo = df_f.iloc[-1] if len(df_f) > 0 else None
penultimo = df_f.iloc[-2] if len(df_f) > 1 else None

st.markdown('<div class="section-title">KPI — Ultimo cedolino</div>', unsafe_allow_html=True)
kc1, kc2, kc3, kc4, kc5 = st.columns(5)

if ultimo is not None:
    kc1.markdown(
        kpi_card("Netto del mese", ultimo["netto"], penultimo["netto"] if penultimo is not None else None),
        unsafe_allow_html=True,
    )
    kc2.markdown(
        kpi_card("Lordo del mese", ultimo["lordo"], penultimo["lordo"] if penultimo is not None else None),
        unsafe_allow_html=True,
    )
    kc3.markdown(
        kpi_card("IRPEF trattenuta", ultimo["irpef"], penultimo["irpef"] if penultimo is not None else None),
        unsafe_allow_html=True,
    )
    kc4.markdown(
        kpi_card("Totale netto YTD", df_f[df_f["anno"] == ultimo["anno"]]["netto"].sum()),
        unsafe_allow_html=True,
    )
    kc5.markdown(
        kpi_card("Fondo TFR", ultimo["fondo_tfr"]),
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Grafico 1 — Evoluzione mensile: netto, lordo, IRPEF, IVS
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Evoluzione mensile — Retribuzione e trattenute</div>', unsafe_allow_html=True)

fig1 = go.Figure()
for campo, label, color in [
    ("netto", "Netto", COLORS["netto"]),
    ("lordo", "Lordo (Ret. utile TFR)", COLORS["lordo"]),
    ("irpef", "IRPEF ritenuta", COLORS["irpef"]),
    ("ivs", "Contributo IVS", COLORS["ivs"]),
]:
    fig1.add_trace(
        go.Scatter(
            x=df_f["etichetta"],
            y=df_f[campo],
            name=label,
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=7),
            hovertemplate=f"<b>{label}</b><br>%{{x}}<br>€%{{y:,.2f}}<extra></extra>",
        )
    )

fig1.update_layout(
    template=PLOTLY_THEME,
    height=380,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title="",
    yaxis_title="Euro (€)",
    hovermode="x unified",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig1, use_container_width=True)

# ---------------------------------------------------------------------------
# Grafico 2 — Ore lavorate + Giorni lavorati
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Ore e giorni lavorati per mese</div>', unsafe_allow_html=True)

col_g2a, col_g2b = st.columns(2)

with col_g2a:
    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=df_f["etichetta"],
            y=df_f["ore_lavorate"],
            name="Ore lavorate",
            marker_color=COLORS["lordo"],
            hovertemplate="<b>Ore</b>: %{y}<extra></extra>",
        )
    )
    fig2.update_layout(
        template=PLOTLY_THEME,
        height=300,
        title_text="Ore lavorate",
        showlegend=False,
        margin=dict(l=0, r=0, t=36, b=0),
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_g2b:
    fig3 = go.Figure()
    fig3.add_trace(
        go.Bar(
            x=df_f["etichetta"],
            y=df_f["giorni_lavorati"],
            name="Giorni lavorati",
            marker_color=COLORS["par"],
            hovertemplate="<b>Giorni</b>: %{y}<extra></extra>",
        )
    )
    fig3.update_layout(
        template=PLOTLY_THEME,
        height=300,
        title_text="Giorni lavorati",
        showlegend=False,
        margin=dict(l=0, r=0, t=36, b=0),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------------------------------------------------------
# Grafico 3 — TFR: quota mensile + fondo cumulativo
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">TFR — Quota mensile e fondo accumulato</div>', unsafe_allow_html=True)

fig4 = go.Figure()
fig4.add_trace(
    go.Bar(
        x=df_f["etichetta"],
        y=df_f["quota_tfr"],
        name="Quota TFR mensile",
        marker_color=COLORS["tfr"],
        yaxis="y1",
        hovertemplate="<b>Quota TFR</b>: €%{y:,.2f}<extra></extra>",
    )
)
fig4.add_trace(
    go.Scatter(
        x=df_f["etichetta"],
        y=df_f["fondo_tfr"],
        name="Fondo TFR (31/12)",
        mode="lines+markers",
        line=dict(color="#cba6f7", width=2, dash="dot"),
        marker=dict(size=7),
        yaxis="y2",
        hovertemplate="<b>Fondo TFR</b>: €%{y:,.2f}<extra></extra>",
    )
)
fig4.update_layout(
    template=PLOTLY_THEME,
    height=320,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(title="Quota mensile (€)"),
    yaxis2=dict(title="Fondo cumulativo (€)", overlaying="y", side="right"),
    hovermode="x unified",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# Grafico 4 — Saldo Ferie e PAR nel tempo
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Saldo Ferie e Permessi PAR</div>', unsafe_allow_html=True)

col_g4a, col_g4b = st.columns(2)

with col_g4a:
    fig5 = go.Figure()
    fig5.add_trace(
        go.Scatter(
            x=df_f["etichetta"],
            y=df_f["ferie_saldo"],
            name="Saldo ferie (GG)",
            mode="lines+markers+text",
            fill="tozeroy",
            fillcolor="rgba(137,220,235,0.15)",
            line=dict(color=COLORS["ferie"], width=2),
            marker=dict(size=7),
            text=df_f["ferie_saldo"].round(1).astype(str),
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate="<b>Ferie saldo</b>: %{y:.2f} GG<extra></extra>",
        )
    )
    fig5.update_layout(
        template=PLOTLY_THEME,
        height=300,
        title_text="Saldo ferie (giorni)",
        showlegend=False,
        yaxis_title="Giorni",
        margin=dict(l=0, r=0, t=36, b=0),
    )
    st.plotly_chart(fig5, use_container_width=True)

with col_g4b:
    fig6 = go.Figure()
    fig6.add_trace(
        go.Scatter(
            x=df_f["etichetta"],
            y=df_f["par_saldo"],
            name="Saldo PAR (ore)",
            mode="lines+markers+text",
            fill="tozeroy",
            fillcolor="rgba(203,166,247,0.15)",
            line=dict(color=COLORS["par"], width=2),
            marker=dict(size=7),
            text=df_f["par_saldo"].round(1).astype(str),
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate="<b>PAR saldo</b>: %{y:.2f} ORE<extra></extra>",
        )
    )
    fig6.update_layout(
        template=PLOTLY_THEME,
        height=300,
        title_text="Saldo permessi PAR (ore)",
        showlegend=False,
        yaxis_title="Ore",
        margin=dict(l=0, r=0, t=36, b=0),
    )
    st.plotly_chart(fig6, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabella progressivi annuali
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Progressivi annuali cumulativi</div>', unsafe_allow_html=True)

# Seleziona ultimo record per anno
prog_df = (
    df_f.sort_values("data")
    .groupby("anno")
    .last()
    .reset_index()[["anno", "prog_inps", "prog_irpef", "prog_irpef_pagata"]]
    .rename(
        columns={
            "anno": "Anno",
            "prog_inps": "Imponibile INPS (€)",
            "prog_irpef": "Imponibile IRPEF (€)",
            "prog_irpef_pagata": "IRPEF pagata (€)",
        }
    )
)
st.dataframe(
    prog_df.style.format(
        {
            "Imponibile INPS (€)": "{:,.2f}",
            "Imponibile IRPEF (€)": "{:,.2f}",
            "IRPEF pagata (€)": "{:,.2f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Tabella dettaglio cedolini
# ---------------------------------------------------------------------------
with st.expander("Dettaglio cedolini — tabella completa"):
    cols_show = [
        "etichetta", "netto", "lordo", "imponibile_irpef",
        "irpef", "ivs", "cigs", "quota_tfr", "fondo_tfr",
        "ore_lavorate", "giorni_lavorati", "ferie_saldo", "par_saldo",
    ]
    rename = {
        "etichetta": "Periodo",
        "netto": "Netto (€)",
        "lordo": "Lordo (€)",
        "imponibile_irpef": "Imponibile IRPEF (€)",
        "irpef": "IRPEF (€)",
        "ivs": "IVS/INPS (€)",
        "cigs": "CIGS (€)",
        "quota_tfr": "Quota TFR (€)",
        "fondo_tfr": "Fondo TFR (€)",
        "ore_lavorate": "Ore lav.",
        "giorni_lavorati": "GG lav.",
        "ferie_saldo": "Ferie saldo (GG)",
        "par_saldo": "PAR saldo (h)",
    }
    det = df_f[cols_show].rename(columns=rename)
    money_cols = [c for c in det.columns if "€" in c]
    fmt = {c: "{:,.2f}" for c in money_cols}
    st.dataframe(det.style.format(fmt), use_container_width=True, hide_index=True)
