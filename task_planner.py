#!/usr/bin/env python3
"""
Task Planner — motore decisionale dell'agente autonomo.
Decide ordine di esecuzione, retry policies, e quando abortire un task.

Logica:
- Legge agent_log.jsonl per capire lo stato recente
- Se un task è fallito 3+ volte in 1h, lo marca come "degraded"
- Se lo scraper è "degraded" per un TLD, passa a retry con user-agent diversi
- Espone decide_next_task() e should_retry(task, tld, component)
"""

import os, json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "agent_log.jsonl")

# Configurazione retry
MAX_RETRIES = 3
FAILURE_WINDOW_MINUTES = 60  # finestra temporale per contare i fallimenti

# Sequenza prioritaria di task giornalieri
DAILY_TASK_SEQUENCE = [
    "scraper_eu",
    "bot_notify_morning",
    "bot_notify_evening",
]

# User-Agent pool per retry anti-WAF (rotazione)
UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


def _read_recent_events(window_minutes: int = FAILURE_WINDOW_MINUTES) -> List[dict]:
    """Legge gli ultimi N minuti di eventi dal log."""
    if not os.path.exists(LOG_PATH):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    events = []
    with open(LOG_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["ts"])
                if ts >= cutoff:
                    events.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return events


def _count_failures(task: str, **filters) -> int:
    """Conta fallimenti recenti per un task con filtri opzionali (tld, component)."""
    events = _read_recent_events()
    failures = 0
    for e in events:
        if e.get("task") != task:
            continue
        if e.get("status") not in ("error", "warn"):
            continue
        # Match filters
        match = True
        for k, v in filters.items():
            if e.get(k) != v:
                match = False
                break
        if match:
            failures += 1
    return failures


def should_retry(tld: str, component: str, attempt: int = 0) -> Tuple[bool, int]:
    """
    Decide se un retry è consentito per lo scraper su un (tld, component).

    Returns:
        (should_retry, next_ua_index)
    """
    if attempt >= MAX_RETRIES:
        return (False, 0)

    failures = _count_failures("scraper", tld=tld, component=component)
    if failures >= MAX_RETRIES * 2:
        # Troppi fallimenti: probabilmente WAF persistente
        return (False, 0)

    ua_index = min(attempt, len(UA_POOL) - 1)
    return (True, ua_index)


def get_ua_pool() -> List[str]:
    """Ritorna il pool di user-agent per retry."""
    return UA_POOL.copy()


def decide_next_task() -> Tuple[Optional[str], Dict]:
    """
    Decide quale task eseguire ora, in base allo stato del log.

    Returns:
        (task_name, context_dict)
        - task_name = None se non è il momento di alcun task
    """
    from datetime import datetime as dt
    now = dt.now()
    hour = now.hour
    weekday = now.weekday()  # noqa: E501
    events = _read_recent_events()

    # Controlla se siamo in orario di invio notizie
    is_morning = hour == 8
    is_evening = hour == 20

    # Controlla se un task è appena stato eseguito (anti-double-run)
    task_keys = {
        "scraper_eu": [e for e in events if e.get("task") == "scraper" and e.get("status") == "start"],
        "bot_notify_morning": [e for e in events if e.get("event") == "morning_news"],
        "bot_notify_evening": [e for e in events if e.get("event") == "evening_news"],
    }

    # Se siamo alle 8:00 e non è ancora stato eseguito stasera...
    if is_morning:
        # Controlla se bot_notify_morning è stato eseguito negli ultimi 90 minuti
        recent_morning = [
            e for e in events
            if e.get("event") == "morning_news" and e.get("status") == "end"
        ]
        if not recent_morning:
            return ("bot_notify_morning", {"hour": hour, "weekday": weekday})

    if is_evening:
        recent_evening = [
            e for e in events
            if e.get("event") == "evening_news" and e.get("status") == "end"
        ]
        if not recent_evening:
            return ("bot_notify_evening", {"hour": hour, "weekday": weekday})

    # Se nessun task programmato, controlla se lo scraper ha bisogno di retry
    # (esegui scraper ogni ora durante la giornata se fallito)
    if hour in range(8, 23):
        recent_scraper = [
            e for e in events
            if e.get("task") == "scraper" and e.get("status") == "start"
        ]
        # Se non è mai stato eseguito oggi, o se c'erano errori recenti
        if not recent_scraper:
            return ("scraper_eu", {"hour": hour, "weekday": weekday})
        # Check errors
        scraper_errors = [e for e in events if e.get("task") == "scraper" and e.get("status") == "error"]
        if len(scraper_errors) > 0:
            return ("scraper_eu", {"hour": hour, "weekday": weekday, "force_retry": True})

    return (None, {})


def get_health_status() -> Dict:
    """
    Ritorna un riepilogo di salute del sistema per la dashboard.
    """
    events = _read_recent_events(window_minutes=1440)  # 24h

    health = {
        "last_24h": {},
        "failures_by_task": defaultdict(int),
        "success_rate": {},
    }

    total_by_task = defaultdict(int)
    ok_by_task = defaultdict(int)

    for e in events:
        task = e.get("task", "unknown")
        total_by_task[task] += 1
        if e.get("status") == "ok" or e.get("status") == "end":
            ok_by_task[task] += 1
        if e.get("status") in ("error", "warn"):
            health["failures_by_task"][task] += 1

    for task in total_by_task:
        health["success_rate"][task] = round(
            ok_by_task[task] / total_by_task[task] * 100, 1
        ) if total_by_task[task] > 0 else 0.0

    health["last_24h"]["total_events"] = len(events)
    health["last_24h"]["components_scraped"] = sum(
        1 for e in events if e.get("event") == "scraped"
    )
    health["last_24h"]["messages_sent"] = sum(
        1 for e in events if e.get("event") == "message_sent"
    )

    return dict(health)


if __name__ == "__main__":
    print("🔍 Task Planner — status:")
    print(json.dumps(get_health_status(), indent=2))
    print("\n⏭  Next task:", decide_next_task())
    ua, idx = should_retry("it", "RTX 5080 16GB", attempt=0)
    print(f"  Retry per it/RTX5080 (attempt 0): {ua} → UA #{idx}")
