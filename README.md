# BP_A — Cruscotto Buste Paga

Dashboard interattivo per analizzare l'andamento mensile delle buste paga: retribuzione, trattenute, TFR, ferie e permessi PAR.

## Requisiti

- Python 3.10+
- Dipendenze: `pip install -r requirements.txt`

## Avvio locale

```bash
# 1. (Opzionale) Rigenera i dati estratti dai PDF
python src/parser.py

# 2. Avvia l'app
streamlit run app.py
```

Il browser si aprirà automaticamente su `http://localhost:8501`.
Login: utente `admin`, password configurata in `auth.yaml`.

## Struttura

```
BP_A/
├── app.py               # Entry point (login gate)
├── auth.yaml            # Credenziali bcrypt-hashate
├── pages/
│   ├── 1_Dashboard.py   # Cruscotto principale
│   └── 2_Admin.py       # Pannello admin (upload, verifica, override)
├── src/
│   ├── parser.py        # Estrae i dati dai PDF → data/payslips.json
│   ├── auth_helper.py   # Login con streamlit-authenticator
│   └── github_helper.py # Commit su GitHub per persistenza Cloud
├── data/
│   ├── payslips.json    # Dati estratti (incluso nel repo)
│   └── overrides.json   # Correzioni manuali anagrafica
├── doc/                 # Buste paga PDF  ← escluso dal repo
└── requirements.txt
```

## Sezioni del cruscotto

| Sezione | Contenuto |
|---|---|
| KPI cards | Netto, Lordo, IRPEF, RAL, Totale netto YTD, Fondo TFR |
| Aumenti | Variazione nominale e reale (inflazione ISTAT NIC) |
| Evoluzione mensile | Netto / Lordo / IRPEF / IVS nel tempo |
| Ore e giorni | Ore e giorni lavorati per mese |
| TFR | Quota mensile + fondo cumulativo |
| Ferie & PAR | Saldo giorni ferie e ore permessi PAR |
| Progressivi annuali | Imponibile INPS/IRPEF e IRPEF pagata |
| Tabella dettaglio | Tutti i valori cedolino per cedolino |

## Pannello Admin

Accessibile dalla sidebar dopo il login. Permette di:
- **Upload** nuove buste paga PDF con parsing automatico
- **Verificare** i dati estratti cedolino per cedolino
- **Correggere** i dati anagrafici (nome, azienda, livello, CCNL…)
- **Re-parsare** un cedolino se il PDF è disponibile in locale

## Deploy su Streamlit Community Cloud

1. **Main file path:** `app.py`
2. **Secrets** (Settings → Secrets):
   ```toml
   GITHUB_TOKEN = "ghp_..."   # Personal Access Token con scope repo
   GITHUB_REPO  = "GritskovaKseniya/BP_A"
   COOKIE_KEY   = "stringa-random-32-caratteri"
   ```
3. Il pannello Admin committa automaticamente le modifiche nel repo per sopravvivere ai redeploy.

## Aggiungere nuove buste paga

Via **pannello Admin → Upload PDF** (consigliato), oppure in locale:

```bash
# Copia i PDF in doc/{anno}/ e riesegui il parser
python src/parser.py
```
