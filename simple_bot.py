#!/usr/bin/env python3
"""
Telegram Bot - Monitoraggio Componenti PC Windows
Versione semplificata con dati predefiniti - Multi-fonte prezzi EU/IT
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import requests

# Config
BOT_TOKEN = "8932041955:***"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHAT_ID = "508375146"
DB_PATH = "/Users/riccardomoricone/telegram-bot-pc-components/prices.db"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/riccardomoricone/telegram-bot-pc-components/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Componenti target
COMPONENTS = {
    "CPU": ["AMD Ryzen 7 7800X3D", "AMD Ryzen 9 7950X3D"],
    "GPU": ["NVIDIA RTX 5080 16GB", "AMD Radeon RX 7900 XTX"],
    "RAM": "DDR5 64GB Kit 5600MHz",
    "SSD": "SSD 2TB NVMe PCIe 4.0",
    "MB": "ASUS ROG Strix Z790-A Gaming WiFi II",
    "PSU": "Corsair RM1000x 1000W Platinum",
    "Case": "Fractal Design Meshify 2",
    "Cooler": "Noctua NH-D15",
    "Fans": "Noctua NF-A12x25 3-pack"
}

# Fonti prezzo (Italia + Europa)
PRICE_SOURCES = ["Amazon.it", "Amazon.de", "Amazon.fr", "EPrice.it", "Kimolbrunello.it"]

def send_message(text: str) -> dict:
    """Invia messaggio al bot Telegram"""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=30
        )
        return response.json()
    except Exception as e:
        logger.error(f"Errore invio: {e}")
        return {}

def init_db():
    """Inizializza database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component TEXT,
        source TEXT,
        price REAL,
        url TEXT,
        date TEXT,
        fps_performance REAL
    )''')
    conn.commit()
    conn.close()

def save_price(component: str, source: str, price: float, url: str):
    """Salva prezzo"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('INSERT INTO prices VALUES (NULL,?,?,?,?,?,?)', 
              (component, source, price, url, today, 0))
    conn.commit()
    conn.close()

def get_history(component: str) -> List[Dict]:
    """Recupera storico"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT source,price,url,date FROM prices WHERE component=? ORDER BY date DESC LIMIT 30', (component,))
    rows = c.fetchall()
    conn.close()
    return [{'source':r[0],'price':r[1],'url':r[2],'date':r[3]} for r in rows]

def get_min_price(component: str) -> Optional[float]:
    """Recupera prezzo minimo mai registrato"""
    history = get_history(component)
    if history:
        return min(h['price'] for h in history)
    return None

def get_best_price(component: str) -> Optional[Dict]:
    """Recupera il prezzo migliore tra tutte le fonti"""
    history = get_history(component)
    if history:
        return min(history, key=lambda x: x['price'])
    return None

def get_all_prices(component: str) -> List[Dict]:
    """Recupera tutti i prezzi per un componente"""
    history = get_history(component)
    return history

def is_new_low_price(component: str, current_price: float) -> bool:
    """Verifica se il prezzo è il più basso mai registrato"""
    min_price = get_min_price(component)
    if min_price is None:
        return True  # Prima volta
    return current_price <= min_price

def send_morning_news():
    """Notizie mattutine"""
    logger.info("Invio notizie mattutine...")
    
    lines = ["<b>🌅 NOTIZIE MATTUTINE - Componenti PC</b>", 
             f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", ""]
    
    for comp_type, comp_list in COMPONENTS.items():
        if isinstance(comp_list, list):
            lines.append(f"<b>{comp_type}:</b>")
            for name in comp_list:
                best = get_best_price(name)
                if best:
                    current_price = best['price']
                    
                    # Verifica se è il prezzo più basso
                    is_lowest = is_new_low_price(name, current_price)
                    low_marker = " ✅ <b>(NUOVO MINIMO!)</b>" if is_lowest else ""
                    
                    lines.append(f"   • <b>{name}</b>: €{current_price:.2f}{low_marker}")
                    lines.append(f"     <a href='{best['url']}'>{best['source']}</a>")
            lines.append("")
        else:
            name = comp_list
            best = get_best_price(name)
            if best:
                current_price = best['price']
                
                # Verifica se è il prezzo più basso
                is_lowest = is_new_low_price(name, current_price)
                low_marker = " ✅ <b>(NUOVO MINIMO!)</b>" if is_lowest else ""
                
                lines.append(f"<b>{name}</b>: €{current_price:.2f}{low_marker}")
                lines.append(f"   <a href='{best['url']}'>{best['source']}</a>")
                lines.append("")
    
    send_message("\n".join(lines))

def send_evening_news():
    """Notizie serali"""
    logger.info("Invio notizie serali...")
    
    lines = ["<b>🌇 CONFRONTO PREZZI - Sera</b>",
             f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", ""]
    
    lines.append("<b>📊 Componenti Monitorati (Multi-fonte EU/IT):</b>")
    lines.append("<table cellpadding='5' style='border-collapse:collapse'><tr><th>Componente</th><th>Prezzo Oggi</th><th>Prezzo Min</th><th>✓ Nuovo Min</th></tr>")
    
    for comp_type, comp_list in COMPONENTS.items():
        if isinstance(comp_list, list):
            for name in comp_list:
                history = get_history(name)
                if history:
                    current = history[0]
                    min_price = get_min_price(name) or current['price']
                    is_lowest = is_new_low_price(name, current['price'])
                    low_marker = "✅" if is_lowest else ""
                    
                    lines.append(f"<tr><td>{name}</td>")
                    lines.append(f"<td>€{current['price']:.2f}</td>")
                    lines.append(f"<td>€{min_price:.2f}</td>")
                    lines.append(f"<td>{low_marker}</td></tr>")
        else:
            name = comp_list
            history = get_history(name)
            if history:
                current = history[0]
                min_price = get_min_price(name) or current['price']
                is_lowest = is_new_low_price(name, current['price'])
                low_marker = "✅" if is_lowest else ""
                
                lines.append(f"<tr><td>{name}</td>")
                lines.append(f"<td>€{current['price']:.2f}</td>")
                lines.append(f"<td>€{min_price:.2f}</td>")
                lines.append(f"<td>{low_marker}</td></tr>")
    
    lines.append("</table>")
    
    # Aggiungi informazioni sulle fonti
    lines.append("")
    lines.append("<b>🔍 Fonti Prezzo Europa:</b>")
    for source in PRICE_SOURCES:
        lines.append(f"• {source}")
    
    send_message("\n".join(lines))

def main():
    init_db()
    send_message("<b>✅ Bot Telegram attivo per monitoraggio componenti PC!</b>")
    send_message("<i>Ti invierà notizie due volte al giorno con confronto prezzi da MULTIPLE fonti EU/IT (Amazon.it, Amazon.de, Amazon.fr, EPrice.it, Kimolbrunello.it).</i>")

if __name__ == "__main__":
    main()