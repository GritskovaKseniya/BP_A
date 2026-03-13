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
# Sezione Aumenti — nominale e reale (inflazione ISTAT NIC)
# ---------------------------------------------------------------------------

# Inflazione ISTAT NIC media annua (variazione % vs anno precedente)
INFLAZIONE_ISTAT: dict[int, float] = {
    2022: 8.7,
    2023: 5.7,
    2024: 1.0,
    2025: 1.5,   # stima preliminare
    2026: 1.4,   # stima preliminare
}

st.markdown('<div class="section-title">Aumenti — variazione nominale e reale (inflazione ISTAT NIC)</div>', unsafe_allow_html=True)

# Media netto per anno (solo mesi ordinari, no aggiustamenti)
media_netto_anno = (
    df[~df["is_aggiustamento"]]
    .groupby("anno")["netto"]
    .mean()
    .reset_index()
    .rename(columns={"netto": "media_netto"})
    .sort_values("anno")
)

rows_aum = []
for i, row in media_netto_anno.iterrows():
    anno = row["anno"]
    media = row["media_netto"]
    if i == 0:
        rows_aum.append({
            "Anno": anno,
            "Media netto (€)": media,
            "Δ nominale %": None,
            "Inflazione %": INFLAZIONE_ISTAT.get(anno),
            "Δ reale %": None,
        })
    else:
        prev_media = media_netto_anno.iloc[i - 1]["media_netto"]
        delta_nom = (media - prev_media) / prev_media * 100
        infl = INFLAZIONE_ISTAT.get(anno, 0.0)
        delta_reale = delta_nom - infl
        rows_aum.append({
            "Anno": anno,
            "Media netto (€)": media,
            "Δ nominale %": delta_nom,
            "Inflazione %": infl,
            "Δ reale %": delta_reale,
        })

df_aum = pd.DataFrame(rows_aum)

# KPI: incremento totale dal primo all'ultimo anno disponibile
anni_completi = df_aum.dropna(subset=["Δ nominale %"])
if len(anni_completi) > 0:
    tot_nom = df_aum["Δ nominale %"].dropna().sum()
    tot_infl = df_aum["Inflazione %"].dropna().sum()
    tot_reale = df_aum["Δ reale %"].dropna().sum()

    anno_inizio = int(df_aum["Anno"].iloc[0])
    anno_fine = int(df_aum["Anno"].iloc[-1])

    ka1, ka2, ka3 = st.columns(3)
    ka1.markdown(
        kpi_card(f"Aumento nominale cumulato ({anno_inizio}→{anno_fine})", tot_nom, fmt="{:+.1f}%"),
        unsafe_allow_html=True,
    )
    ka2.markdown(
        kpi_card(f"Inflazione cumulata ({anno_inizio}→{anno_fine})", tot_infl, fmt="{:.1f}%"),
        unsafe_allow_html=True,
    )
    ka3.markdown(
        kpi_card(f"Aumento reale cumulato ({anno_inizio}→{anno_fine})", tot_reale, fmt="{:+.1f}%"),
        unsafe_allow_html=True,
    )

# Grafico barre affiancate: nominale vs reale per anno
df_aum_plot = df_aum.dropna(subset=["Δ nominale %"]).copy()
fig_aum = go.Figure()
fig_aum.add_trace(go.Bar(
    x=df_aum_plot["Anno"].astype(str),
    y=df_aum_plot["Δ nominale %"],
    name="Δ nominale %",
    marker_color=COLORS["lordo"],
    text=df_aum_plot["Δ nominale %"].map("{:+.1f}%".format),
    textposition="outside",
    hovertemplate="<b>Nominale</b>: %{y:+.2f}%<extra></extra>",
))
fig_aum.add_trace(go.Bar(
    x=df_aum_plot["Anno"].astype(str),
    y=df_aum_plot["Δ reale %"],
    name="Δ reale % (nominale − inflazione)",
    marker_color=df_aum_plot["Δ reale %"].apply(
        lambda v: COLORS["netto"] if v >= 0 else COLORS["irpef"]
    ),
    text=df_aum_plot["Δ reale %"].map("{:+.1f}%".format),
    textposition="outside",
    hovertemplate="<b>Reale</b>: %{y:+.2f}%<extra></extra>",
))
fig_aum.add_trace(go.Scatter(
    x=df_aum_plot["Anno"].astype(str),
    y=df_aum_plot["Inflazione %"],
    name="Inflazione ISTAT NIC %",
    mode="lines+markers",
    line=dict(color="#f9e2af", width=2, dash="dot"),
    marker=dict(size=8, symbol="diamond"),
    hovertemplate="<b>Inflazione</b>: %{y:.1f}%<extra></extra>",
))
fig_aum.add_hline(y=0, line_width=1, line_color="#585b70")
fig_aum.update_layout(
    template=PLOTLY_THEME,
    height=360,
    barmode="group",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_title="Anno",
    yaxis_title="Variazione %",
    hovermode="x unified",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig_aum, use_container_width=True)

# Tabella dettaglio
st.dataframe(
    df_aum.style.format({
        "Media netto (€)": "{:,.2f}",
        "Δ nominale %": lambda v: f"{v:+.2f}%" if v is not None else "—",
        "Inflazione %": lambda v: f"{v:.1f}%" if v is not None else "—",
        "Δ reale %": lambda v: f"{v:+.2f}%" if v is not None else "—",
    }).applymap(
        lambda v: "color: #a6e3a1" if isinstance(v, float) and v > 0
                  else ("color: #f38ba8" if isinstance(v, float) and v < 0 else ""),
        subset=["Δ reale %"],
    ),
    use_container_width=True,
    hide_index=True,
)

st.caption("Inflazione ISTAT NIC (Indice Nazionale dei prezzi al Consumo) — media annua. Fonte: Istat. Il Δ reale misura quanto l'aumento di stipendio ha superato (o non raggiunto) il costo della vita.")

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
