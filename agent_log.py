#!/usr/bin/env python3
"""
Agent Logger — strutturato, centralizzato per il Telegram Price Bot Agent.
Ogni riga = un evento JSONL in /logs/agent_log.jsonl

Uso:
    from agent_log import log_event
    log_event("scraper", status="ok", tld="it", component="RTX 5080", price=1299.0, latency_ms=3240)
    log_event("bot_notify", event="message_sent", chat_id=508375146)
    log_event("cron", event="tick_start", job="morning_news")
    log_event("cron", event="tick_end",   job="morning_news", status="ok", duration_s=23)
"""

import os, json, threading
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_PATH = os.path.join(LOG_DIR, "agent_log.jsonl")

_lock = threading.Lock()

def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)

def log_event(task: str, status: str = "info", **fields) -> None:
    """Logga un evento strutturato in JSONL.

    Args:
        task: chiave primaria — "scraper", "bot_notify", "cron", "api", "dashboard", "health_check"
        status: "ok", "warn", "error", "info", "start", "end"
        **fields: qualsiasi campo aggiuntivo (price, tld, component, error, duration_ms, ...)
    """
    _ensure_dir()

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": task,
        "status": status,
    }
    entry.update(fields)

    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))

    with _lock:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def read_last_events(n: int = 100):
    """Legge le ultime n righe del log (per dashboard/CLI)."""
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as fh:
        lines = fh.readlines()[-n:]
    return [json.loads(l) for l in lines if l.strip()]


if __name__ == "__main__":
    # quick smoke test
    log_event("test", status="info", msg="agent_log.py caricato correttamente")
    print(f"✅ Log scritto in {LOG_PATH}")
    print(f"Ultimi eventi: {read_last_events(3)}")