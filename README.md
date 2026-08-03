# 🤖 Componenti PC Windows — Agente Autonomo
## Monitoraggio prezzi componenti PC su Amazon EU (IT/DE/ES/FR/NL/PL)

---

## 🚀 Setup Rapido

### 1. Installa dipendenze Python
```bash
pip install playwright flask beautifulsoup4 lxml requests
playwright install chromium
```

### 2. Installa dipendenze Node.js (dashboard)
```bash
npm install
```

### 3. Avvia l'API + Dashboard (sviluppo)
```bash
# Terminale 1 — API Flask (porta 5000)
python api.py

# Terminale 2 — Dashboard Next.js (porta 3000)
npx next dev
```

### 4. Avvia cron (produzione)
```bash
# Aggiungi al crontab:
crontab -e
# */10 8-23 * * * /Users/riccardomoricone/telegram-bot-pc-components/cron_job.sh
```

### 5. Esegui manualmente
```bash
python bot_tasks.py morning_news    # Invio notizie mattutine
python bot_tasks.py evening_news    # Confronto prezzi serale
python scraper.py                    # Scraping EU manuale
python task_planner.py              # Mostra stato agente + health
```

---

## 🏗️ Architettura Agente

```
telegram-bot-pc-components/
├── scraper.py              # Scraping Playwright EU (6 TLDs, ASIN-based)
├── bot_tasks.py            # Task Telegram: morning_news, evening_news, fetch_prices
├── api.py                  # API Flask + Dashboard REST endpoints
├── pages/
│   └── index.js            # Dashboard Next.js (React) — stato agente in tempo reale
├── agent_log.py            # 📝 Logging strutturato JSONL centralizzato
├── task_planner.py         # 🧠 Task scheduler + retry logic + health monitoring
├── cron_job.sh             # 🕐 Cron wrapper con task planner integration
├── requirements.txt
└── logs/
    └── agent_log.jsonl     # Event log (JSONL): timestamp, task, status, metrics
```

Vedi [ARCHITECTURE.md](./ARCHITECTURE.md) per dettagli.

---

## 🤖 Componenti dell'Agente Autonomo

| Modulo | Funzione |
|---|---|
| **agent_log.py** | Logging strutturato JSONL — ogni azione è un evento `{ts, task, status, ...}` |
| **task_planner.py** | Decide cosa fare, retry con rotazione UA, health status |
| **scraper.py** | Scraping Playwright con retry automatico + pulizia outlier |
| **bot_tasks.py** | Invio notizie Telegram + logging task lifecycle |
| **api.py** | API REST per prezzi + dashboard metriche |
| **pages/index.js** | Dashboard Next.js — visibilità in tempo reale |

---

## 📊 Dashboard

La dashboard (http://localhost:3000) mostra:

- **📈 Stato Sistema (24h)**: eventi totali, messaggi inviati, componenti OK/falliti, pool UA
- **🗺️ Mappa Guasti per Marketplace**: success rate % per ogni TLD (Amazon.it, .de, .fr, etc.)
- **📈 Success Rate per Task**: aggregato per scraper/bot_notify/cron
- **⚡ Ultima Attività**: stream di eventi JSONL in tempo reale
- **Refresh automatico ogni 2 minuti**

### API Endpoints Dashboard

| Endpoint | Descrizione |
|---|---|
| `/api/dashboard/health` | Stato aggregato, recent activity, success rate per task |
| `/api/dashboard/failure-map` | Success rate e fallimenti per ogni TLD marketplace |
| `/api/dashboard/metrics` | Componenti con prezzo vs falliti, pool UA disponibile |

---

## 🔄 Auto-Recovery & Retry Logic

Se lo scraper fallisce su un marketplace:
1. **Prova 3 volte** con **User-Agent diverso** (5 UA disponibili)
2. Logga ogni tentativo via `agent_log` (`attempt`, `latency_ms`, `error`)
3. Se persiste → `max_retries_exceeded` + marcatura nella **failure map** (rosso)
4. Il **next run** vede il guasto e riprova automaticamente

---

## 📊 Componenti Monitorati

- **CPU AMD**: Ryzen 7 7800X3D, Ryzen 9 7950X3D
- **GPU**: RTX 5080 16GB, RX 7900 XTX
- **RAM**: DDR5 64GB Kit 5600MHz
- **SSD**: 990 PRO 2TB NVMe PCIe 4.0
- **Motherboard**: ASUS Z790-A WiFi II
- **PSU**: Corsair RM1000x
- **Case**: Fractal Meshify 2
- **Cooler**: Noctua NH-D15, Noctua NF-A12x25 3-pack

## 🌍 Fonti Prezzo

- Amazon.it, Amazon.de, Amazon.es, Amazon.fr, Amazon.nl, Amazon.pl

## 📈 API Endpoints

| Endpoint | Descrizione |
|---|---|
| `/api/prices` | Tutti i prezzi |
| `/api/prices/{component}` | Prezzi per componente |
| `/api/best-price/{component}` | Miglior prezzo |
| `/api/components` | Lista componenti |
| `/api/dashboard/health` | Stato agente 24h |
| `/api/dashboard/failure-map` | Guasti per marketplace |
| `/api/dashboard/metrics` | Metriche aggregate |
