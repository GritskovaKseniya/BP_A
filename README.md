# BP_A — Cruscotto Buste Paga

Dashboard interattivo per analizzare l'andamento mensile delle buste paga: retribuzione, trattenute, TFR, ferie e permessi PAR.

## Requisiti

- Python 3.10+
- Dipendenze: `pip install -r requirements.txt`

## Avvio

```bash
# 1. (Opzionale) Rigenera i dati estratti dai PDF
python src/parser.py

# 2. Avvia il cruscotto
streamlit run src/dashboard.py
```

Il browser si aprirà automaticamente su `http://localhost:8501`.

## Struttura

```
BP_A/
├── doc/             # Buste paga PDF  ← escluso dal repo
├── data/            # Dati estratti (JSON)  ← escluso dal repo
├── src/
│   ├── parser.py    # Estrae i dati dai PDF → data/payslips.json
│   └── dashboard.py # Cruscotto Streamlit + Plotly
└── requirements.txt
```

## Sezioni del cruscotto

| Sezione | Contenuto |
|---|---|
| KPI cards | Netto, Lordo, IRPEF, Totale netto YTD, Fondo TFR |
| Evoluzione mensile | Netto / Lordo / IRPEF / IVS nel tempo |
| Ore e giorni | Ore e giorni lavorati per mese |
| TFR | Quota mensile + fondo cumulativo |
| Ferie & PAR | Saldo giorni ferie e ore permessi PAR |
| Progressivi annuali | Imponibile INPS/IRPEF e IRPEF pagata |
| Tabella dettaglio | Tutti i valori cedolino per cedolino |

Il filtro per anno è nella sidebar sinistra.

## Aggiungere nuove buste paga

Copia i PDF nella cartella `doc/` e riesegui il parser:

```bash
python src/parser.py
```

Il cruscotto rileva automaticamente i nuovi cedolini al prossimo avvio.
