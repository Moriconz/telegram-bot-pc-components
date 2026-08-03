# 🏗️ Architettura — Telegram Price Bot PC Components

## Panoramica

Sistema agentico autonomo per il monitoraggio prezzi componenti PC su Amazon EU (IT/DE/ES/FR/NL/PL).
L'agente gira 2x al giorno (08:00 e 20:00) via cron, scraping live con Playwright, invia report Telegram
e rende visibili metriche/dashboard in tempo reale.

## Stack

```
telegram-bot-pc-components/
├── scraper.py              # Scraping Playwright EU (6 TLDs, ASIN-based)
├── bot_tasks.py            # Task Telegram: morning_news, evening_news, fetch_prices
├── bot_notify.py           # Notifica Telegram dedicata
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

## Componenti chiave

### 1. Agent Logger (`agent_log.py`)
- Scrive eventi JSONL in `logs/agent_log.jsonl`
- Formato: `{"ts", "task", "status", **fields}`
- Task: `scraper`, `bot_notify`, `cron`, `api`
- Status: `ok`, `warn`, `error`, `info`, `start`, `end`

### 2. Task Planner (`task_planner.py`)
- `decide_next_task()` — decide quale task eseguire (morning_news / evening_news / scraper_eu)
- `should_retry(tld, component, attempt)` — retry logic con rotazione User-Agent (5 UAs)
- `get_health_status()` — metriche aggregate 24h
- MAX_RETRIES = 3, FAILURE_WINDOW = 60 minuti

### 3. Scraping con retry (`scraper.py`)
- Playwright headless su Amazon EU
- Retry automatico con User-Agent diversi su 403 WAF
- Pulizia outlier (2.5x / 0.4x mediana)
- Logging strutturato per ogni attempt

### 4. Dashboard (`pages/index.js` + API)
- `/api/dashboard/health` — stato aggregato, recent activity, success rate per task
- `/api/dashboard/failure-map` — success rate per TLD marketplace
- `/api/dashboard/metrics` — componenti OK vs falliti, pool UA
- Frontend Next.js con refresh automatico ogni 2 minuti

## Flusso operativo (cron → dashboard)

```
cron_job.sh (ogni 10 min, 8-23)
  ↓
task_planner.decide_next_task()
  ↓
[bot_tasks.py morning_news]   OR   [scraper.py]
  ↓                              ↓
agent_log.log_event() ← logging strutturato
  ↓
Telegram message + data.json   Amazon EU prices (6 TLD)
  ↓
Dashboard Next.js ← /api/dashboard/*
```

## Auto-recovery

Se lo scraper su un TLD fallisce 3 volte, il Task Planner:
1. Ruota User-Agent (5 disponibili)
2. Ritenta scraping
3. Se persiste, logga `max_retries_exceeded` e marca il componente come fallito
4. Notifica visibile in dashboard (failure map rossa)
