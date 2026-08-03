#!/usr/bin/env python3
"""
Task separati per il bot - può essere chiamato dal scheduler
"""

import os
import sys
import json
import sqlite3
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from agent_log import log_event

# Config
BOT_TOKEN = "8932041955:AAETap342SJ1EmqlK3s_Mo2PLqtJw1QvWJY"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHAT_ID = "508375146"
DB_PATH = "/Users/riccardomoricone/telegram-bot-pc-components/prices.db"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/riccardomoricone/telegram-bot-pc-components/tasks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Componenti target (AMD ONLY + RTX 5080)
TARGET_COMPONENTS = [
    "AMD Ryzen 7 7800X3D",
    "AMD Ryzen 9 7950X3D", 
    "NVIDIA RTX 5080 16GB",
    "AMD Radeon RX 7900 XTX",
    "DDR5 64GB Kit 5600MHz",
    "SSD 2TB NVMe PCIe 4.0",
    "ASUS ROG Strix Z790-E WiFi",
    "Corsair RM1000x 1000W Platinum",
    "Fractal Design Meshify 2",
    "Noctua NH-D15",
    "Noctua NF-A12x25 3-pack"
]

def send_message(text: str, parse_mode: str = "HTML") -> dict:
    """Invia messaggio al bot Telegram"""
    t0 = time.time()
    result = {}
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "parse_mode": parse_mode},
            timeout=30
        )
        result = response.json()
        dur = int((time.time() - t0) * 1000)
        if response.status_code == 200:
            log_event("bot_notify", status="ok", event="message_sent", chat_id=CHAT_ID, latency_ms=dur)
        else:
            log_event("bot_notify", status="error", event="message_sent", chat_id=CHAT_ID, error=result.get("description", "unknown"), status_code=response.status_code, latency_ms=dur)
        return result
    except Exception as e:
        dur = int((time.time() - t0) * 1000)
        log_event("bot_notify", status="error", event="message_sent", chat_id=CHAT_ID, error=str(e)[:120], latency_ms=dur)
        logger.error(f"Errore invio messaggio: {e}")
        return {}

def scrape_amazon(component_name: str) -> List[Dict]:
    """Scansiona Amazon Italia"""
    results = []
    try:
        search_url = f"https://www.amazon.it/s?k={component_name.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        
        response = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        products = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for product in products[:5]:
            try:
                h2 = product.find('h2')
                if h2:
                    a_tag = h2.find('a')
                    if a_tag:
                        name = a_tag.get_text(strip=True) if a_tag.get_text() else ""
                        href = a_tag.get('href', '')
                        href_str = str(href) if href else ""
                        url = f"https://amazon.it{href_str}" if href_str and not href_str.startswith('http') else href_str
                        
                        price_tag = product.find('span', class_='a-price-whole')
                        price = 0.0
                        if price_tag and price_tag.get_text():
                            price_text = price_tag.get_text().replace('.', '').replace(',', '.')
                            try:
                                price = float(price_text)
                            except ValueError:
                                price = 0.0
                        
                        results.append({'name': name, 'price': price, 'url': url, 'source': 'Amazon.it'})
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Errore scraping Amazon: {e}")
    
    return results

def get_price_history(component: str) -> List[Dict]:
    """Recupera storico prezzi"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT source, price, url, date FROM prices
        WHERE component = ? ORDER BY date DESC LIMIT 30
    ''', (component,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{'source': r[0], 'price': r[1], 'url': r[2], 'date': r[3]} for r in rows]

def get_min_price(component: str) -> Optional[float]:
    """Recupera prezzo minimo mai registrato"""
    history = get_price_history(component)
    if history:
        return min(h['price'] for h in history)
    return None

def is_new_low_price(component: str, current_price: float) -> bool:
    """Verifica se il prezzo è il più basso mai registrato"""
    min_price = get_min_price(component)
    if min_price is None:
        return True
    return current_price <= min_price

def save_price(component: str, source: str, price: float, url: str):
    """Salva prezzo nel database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        INSERT INTO prices
        (component, source, price, url, date) VALUES (?, ?, ?, ?, ?)
    ''', (component, source, price, url, today))
    
    conn.commit()
    conn.close()

def send_startup_message():
    """Invia messaggio di avvio"""
    log_event("bot_notify", status="start", event="startup_message")
    send_message("<b>✅ Bot Telegram attivo per monitoraggio componenti PC!</b>")
    send_message("<i>Ti invierà notizie due volte al giorno con confronto prezzi AMD Only.</i>")
    log_event("bot_notify", status="end", event="startup_message")

def fetch_and_save_prices():
    """Recupera e salva tutti i prezzi"""
    log_event("bot_notify", status="start", event="fetch_prices", n_components=len(TARGET_COMPONENTS))
    t0 = time.time()
    for comp_name in TARGET_COMPONENTS:
        logger.info(f"Cerco prezzi per: {comp_name}")
        prices = []
        prices.extend(scrape_amazon(comp_name))
        log_event("bot_notify", status="info", event="scraped", component=comp_name, n_results=len(prices))

        if prices:
            prices.sort(key=lambda x: x['price'])
            best = prices[0]
            save_price(comp_name, best['source'], best['price'], best['url'])
    dur = int((time.time() - t0))
    log_event("bot_notify", status="end", event="fetch_prices", duration_s=dur)

def send_morning_news():
    """Invia notizie mattutine"""
    log_event("bot_notify", status="start", event="morning_news")
    logger.info("Invio notizie mattutine...")
    fetch_and_save_prices()
    
    lines = ["<b>🌅 NOTIZIE MATTUTINE - Componenti PC (AMD Only)</b>",
             f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", ""]
    
    for name in TARGET_COMPONENTS:
        history = get_price_history(name)
        if history:
            best = history[0]
            current_price = best['price']
            
            # Verifica se è il prezzo più basso
            is_lowest = is_new_low_price(name, current_price)
            low_marker = " ✅" if is_lowest else ""
            
            lines.append(f"<b>{name}</b>: €{current_price:.2f}{low_marker}")
            lines.append(f"   <a href='{best['url']}'>{best['source']}</a>")
            lines.append("")
    
    send_message("\n".join(lines))

def send_evening_news():
    """Invia notizie serali"""
    log_event("bot_notify", status="start", event="evening_news")
    logger.info("Invio notizie serali...")
    fetch_and_save_prices()
    
    lines = ["<b>🌇 CONFRONTO PREZZI - Sera (AMD Only)</b>",
             f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", ""]
    
    lines.append("<b>📊 Prezzi Oggi vs Prezzo Minimo</b>")
    lines.append("<table cellpadding='5' cellspacing='0'><tr><th>Componente</th><th>Oggi</th><th>Min</th><th>Nuovo Min</th></tr>")
    
    for name in TARGET_COMPONENTS:
        history = get_price_history(name)
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
    send_message("\n".join(lines))

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python bot_tasks.py <task_name>")
        sys.exit(1)
    
    task_name = sys.argv[1]
    
    tasks = {
        "send_startup_message": send_startup_message,
        "morning_news": send_morning_news,
        "evening_news": send_evening_news,
        "fetch_prices": fetch_and_save_prices,
    }
    
    if task_name in tasks:
        t0 = time.time()
        try:
            tasks[task_name]()
            dur = int((time.time() - t0))
            log_event("bot_notify", status="end", event="task_complete", task_name=task_name, duration_s=dur)
        except Exception as e:
            dur = int((time.time() - t0))
            log_event("bot_notify", status="error", event="task_failed", task_name=task_name, error=str(e)[:120], duration_s=dur)
            raise
    else:
        log_event("bot_notify", status="error", event="task_unknown", task_name=task_name)
        print(f"Task sconosciuto: {task_name}")
        sys.exit(1)

if __name__ == "__main__":
    main()