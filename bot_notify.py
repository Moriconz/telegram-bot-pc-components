#!/usr/bin/env python3
"""
Invia su Telegram un riepilogo prezzi leggendo data.json (prodotto dallo scraper)
e il link alla pagina web su Vercel. Tiene uno storico dei prezzi migliori e
segnala cosa e' cambiato (aumento/diminuzione %) rispetto allo scrape precedente.

Opzione A: messaggio testuale + link alla pagina interattiva + storico variazioni.
Esegui: python bot_notify.py           (salva snapshot, invia report + variazioni)
       python bot_notify.py --test     (invia solo un messaggio di test)
"""
import os
import json
import sqlite3
import argparse
import logging
import requests
from datetime import datetime

# Config (stesse credenziali di simple_bot.py)
BOT_TOKEN = "8932041955:AAETap342SJ1EmqlK3s_Mo2PLqtJw1QvWJY"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHAT_ID = "508375146"
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "data.json")
HISTORY_PATH = os.path.join(BASE, "history.db")
SITE_URL = "https://telegram-bot-pc-components.vercel.app"

# Performance relativa (raster 1440p/4K approx). 100 = RX 7900 XTX di riferimento.
GPU_PERF = {"RTX 5080 16GB": 102, "RX 7900 XTX": 100}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------- Telegram ----------
def send_message(text: str) -> dict:
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
                                "disable_web_page_preview": False},
                          timeout=30)
        return r.json()
    except Exception as e:
        logger.error(f"Errore invio: {e}")
        return {}


# ---------- Storico prezzi ----------
def init_history():
    conn = sqlite3.connect(HISTORY_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        component TEXT,
        best_price REAL,
        best_source TEXT
    )''')
    conn.commit()
    conn.close()


def save_snapshot(d):
    """Salva lo snapshot dei prezzi migliori per ogni componente."""
    conn = sqlite3.connect(HISTORY_PATH)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for name, comp in d["components"].items():
        rows = [(s, v["price_eur"]) for s, v in comp["prices"].items()
                if v.get("price_eur") is not None]
        if not rows:
            continue
        rows.sort(key=lambda x: x[1])
        best_src, best_pr = rows[0]
        c.execute("INSERT INTO snapshots (ts, component, best_price, best_source) VALUES (?,?,?,?)",
                  (ts, name, best_pr, best_src))
    conn.commit()
    conn.close()


def get_previous_best():
    """Ritorna {component: (price, source)} dello snapshot piu' recente precedente."""
    conn = sqlite3.connect(HISTORY_PATH)
    c = conn.cursor()
    # trova lo snapshot piu' recente
    c.execute("SELECT ts FROM snapshots GROUP BY ts ORDER BY ts DESC LIMIT 1")
    row = c.fetchone()
    if not row:
        conn.close()
        return {}
    latest_ts = row[0]
    c.execute("SELECT ts FROM snapshots GROUP BY ts ORDER BY ts DESC LIMIT 2")
    rows = c.fetchall()
    if len(rows) < 2:
        conn.close()
        return {}  # solo uno snapshot, niente confronto
    prev_ts = rows[1][0]
    c.execute("SELECT component, best_price, best_source FROM snapshots WHERE ts=?", (prev_ts,))
    prev = {r[0]: (r[1], r[2]) for r in c.fetchall()}
    conn.close()
    return prev


def compute_changes(d):
    """Confronta prezzi attuali con lo snapshot precedente.
    Ritorna lista di dict ordinati per variazione assoluta decrescente:
    {name, old, new, delta, pct, direction}"""
    prev = get_previous_best()
    changes = []
    for name, comp in d["components"].items():
        rows = [(s, v["price_eur"]) for s, v in comp["prices"].items()
                if v.get("price_eur") is not None]
        if not rows:
            continue
        rows.sort(key=lambda x: x[1])
        new_src, new_pr = rows[0]
        if name not in prev:
            continue
        old_pr, old_src = prev[name]
        if old_pr is None:
            continue
        delta = new_pr - old_pr
        if abs(delta) < 0.005:
            continue
        pct = (delta / old_pr) * 100 if old_pr else 0
        changes.append({
            "name": name, "old": old_pr, "new": new_pr,
            "delta": delta, "pct": pct,
            "direction": "up" if delta > 0 else "down",
            "old_src": old_src, "new_src": new_src,
        })
    changes.sort(key=lambda x: -abs(x["delta"]))
    return changes


# ---------- Calcolo totali ----------
# Performance relativa (raster gaming 1440p/4K approx). 100 = RX 7900 XTX di riferimento.
GPU_PERF = {"RTX 5080 16GB": 102, "RX 7900 XTX": 100}
# Performance relativa CPU (gaming). 100 = Ryzen 7 7800X3D (miglior value per gaming).
CPU_PERF = {"Ryzen 7 7800X3D": 100, "Ryzen 9 7950X3D": 112}

def _pick_best(group_rows, perf_map):
    """Tra piu' varianti della stessa categoria, ritorna la migliore per prezzo/performance."""
    group_rows.sort(key=lambda x: -x[3])
    return group_rows[0]

def compute_totals(d, apply_combos=True):
    """Ritorna (lista totali ordinata, grande_totale, gpu_scelta).
    GPU e CPU contate UNA volta ciascuna: la migliore per frame/€ (o prezzo/perf).
    Applica i COMBO (bundle) se apply_combos e il loro prezzo < somma dei singoli migliori."""
    out = []
    gpu = []
    cpu = []
    for name, c in d["components"].items():
        ps = [v["price_eur"] for v in c["prices"].values() if v.get("price_eur") is not None]
        if not ps:
            continue
        # La licenza Windows la gestisce l'utente: esclusa dal totale PC.
        if "Windows" in name:
            continue
        best = min(ps)
        qty = c.get("qty", 1)
        if c["category"] == "GPU":
            perf = GPU_PERF.get(name, 100)
            gpu.append((name, best, perf, perf / best))
        elif c["category"] == "CPU":
            perf = CPU_PERF.get(name, 100)
            cpu.append((name, best, perf, perf / best))
        else:
            out.append((name, best * qty))
    # GPU: migliore per frame/€
    if gpu:
        gpu.sort(key=lambda x: -x[3])
        win = gpu[0]
        out.append((win[0] + " (scelta per frame/€)", win[1]))
    # CPU: migliore per prezzo/performance (value)
    if cpu:
        cpu.sort(key=lambda x: -x[3])
        win = cpu[0]
        out.append((win[0] + " (scelta per value)", win[1]))

    # --- Applica COMBO se convenienti ---
    if apply_combos:
        # I nomi dei componenti nel totale hanno suffissi (es. " (scelta per value)"),
        # quindi i target del combo si cercano per PREFISSO. Per evitare doppi conteggi,
        # un componente coperto da un combo non puo' essere riusato da un altro.
        best_by_name = {n: p for n, p in out}
        covered = set()
        applied = []
        for combo in d.get("combos", []):
            # Trova le righe il cui nome inizia con uno dei target
            matched_rows = []
            for t in combo.get("replaces", []):
                hit = [r for r in out if r[0].startswith(t) and r[0] not in covered]
                matched_rows.extend(hit)
            if len(matched_rows) < len(combo.get("replaces", [])):
                continue  # non tutti i componenti del combo sono disponibili
            single_sum = sum(p for _, p in matched_rows)
            combo_price = combo.get("price_eur") or combo.get("price")
            if combo_price is None:
                continue
            if combo_price < single_sum - 0.01:  # conviene davvero
                for r in matched_rows:
                    out = [row for row in out if row is not r]
                    covered.add(r[0])
                label = f"COMBO {combo['id']} (risparmio €{single_sum - combo_price:.0f})"
                out.append((label, round(combo_price, 2)))
                applied.append(combo["id"])

    out.sort(key=lambda x: x[1])
    return out, sum(p for _, p in out), (gpu[0][0] if gpu else None)


# ---------- Report ----------
def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def build_report(d):
    totals, grand, gpu_win = compute_totals(d)
    lines = []
    lines.append("<b>💻 Prezzi Componenti PC — Europa</b>")
    lines.append(f"💰 <b>TOTALE PC completo: €{grand:.2f}</b>")
    lines.append(f"🎯 GPU scelta (frame/€): <b>{gpu_win}</b>")
    # Combo (bundle) applicate
    combo_rows = [n for n, _ in totals if n.startswith("COMBO")]
    if combo_rows:
        lines.append("")
        lines.append("📦 <b>Combo convienienti:</b>")
        for n in combo_rows:
            lines.append("  • " + n)
    # PC pre-assemblati: confrontati col costo dei COMPONENTI SINGOLI (senza combo),
    # perche' un pre-assemblato e' un'alternativa al "comprali singoli", non al bundle.
    # Usa compute_totals SENZA combo come soglia (una sola GPU + una sola CPU scelta).
    _, single_sum, _ = compute_totals(d, apply_combos=False)
    prebuilt = d.get("prebuilt", [])
    alive = [p for p in prebuilt if not p.get("broken") and p.get("price") is not None]
    under = [p for p in alive if p["price"] <= single_sum]
    if under:
        lines.append("")
        lines.append(f"🖥️ <b>PC pre-assemblati equivalenti (sotto €{single_sum:.0f} dei singoli):</b>")
        for p in sorted(under, key=lambda x: x["price"]):
            tag = " ⭐migliore" if p["price"] == min(x["price"] for x in under) else ""
            lines.append(f"  • <a href='{p['url']}'>{p['name']}</a> — €{p['price']:.0f}{tag}")
    lines.append("")
    lines.append(f"📊 Dettaglio completo: <a href='{SITE_URL}'>telegram-bot-pc-components.vercel.app</a>")
    return "\n".join(lines)


# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="invia solo messaggio di test")
    args = ap.parse_args()

    init_history()

    if args.test:
        res = send_message("<b>🧪 Test Bot</b>\nCollegamento alla pagina web attivo. "
                           f"Pagina: {SITE_URL}")
        print("Test inviato:", res.get("ok"))
        return

    d = load_data()
    save_snapshot(d)
    text = build_report(d)
    res = send_message(text)
    print("Report inviato:", res.get("ok"))


if __name__ == "__main__":
    main()
