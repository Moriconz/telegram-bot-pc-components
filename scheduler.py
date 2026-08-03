#!/usr/bin/env python3
"""Scheduler - invia notizie 2 volte al giorno"""

import os
import sys
import time
import logging
from datetime import datetime

# Aggiungi path
sys.path.insert(0, '/Users/riccardomoricone/telegram-bot-pc-components')

from simple_bot import (
    send_message, send_morning_news, send_evening_news,
    init_db, save_price, COMPONENTS
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/riccardomoricone/telegram-bot-pc-components/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = "/Users/riccardomoricone/telegram-bot-pc-components/prices.db"

def init_db():
    """Inizializza database"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component TEXT,
        source TEXT,
        price REAL,
        url TEXT,
        date TEXT
    )''')
    conn.commit()
    conn.close()

def add_sample_data():
    """Aggiunge dati di esempio"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Dati esempio per test
    sample = [
        ("Intel Core i9-14900K", "Amazon.it", 549.99, "https://amazon.it/i9-14900k", today),
        ("Intel Core i9-14900K", "EPrice.it", 539.90, "https://eprice.it/i9-14900k", today),
        ("NVIDIA RTX 4080 16GB", "Amazon.it", 1099.00, "https://amazon.it/rtx4080", today),
        ("DDR5 64GB Kit", "Amazon.it", 349.90, "https://amazon.it/ddr5-64gb", today),
        ("SSD 2TB NVMe", "EPrice.it", 179.90, "https://eprice.it/ssd-2tb", today),
    ]
    
    for row in sample:
        c.execute('INSERT INTO prices VALUES (NULL,?,?,?,?,?)', row)
    
    conn.commit()
    conn.close()

def run_scheduler():
    """Esegue il scheduler"""
    logger.info("Scheduler avviato")
    
    init_db()
    add_sample_data()
    
    # Invia messaggio di avvio
    send_message("<b>✅ Bot Telegram attivo!</b>")
    send_message("<i>Invierò notizie alle 08:00 e 20:00</i>")
    
    last_morning = None
    last_evening = None
    
    while True:
        try:
            now = datetime.now()
            hour = now.hour
            date_key = now.date()
            
            # 08:00 - Notizie mattutine
            if hour == 8 and last_morning != date_key:
                logger.info("Invio notizie mattutine")
                send_morning_news()
                last_morning = date_key
            
            # 20:00 - Notizie serali
            if hour == 20 and last_evening != date_key:
                logger.info("Invio notizie serali")
                send_evening_news()
                last_evening = date_key
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            logger.info("Scheduler terminato")
            break
        except Exception as e:
            logger.error(f"Errore: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_scheduler()