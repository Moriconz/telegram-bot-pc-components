#!/usr/bin/env python3
"""
Telegram Bot per monitoraggio componenti PC Windows
Invia notizie due volte al giorno su componenti con prezzi e storici
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

# Config
BOT_TOKEN = "8932041955:AAETap342SJ1EmqlK3s_Mo2PLqtJw1QvWJY"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHAT_ID = "508375146"

# Componenti target (ispirati al PC gaming ma diversi)
TARGET_COMPONENTS = {
    "cpu": {
        "name": "Intel Core i9-14900K",
        "min_price": 500,
        "max_price": 600,
        "required": True
    },
    "gpu": {
        "name": "NVIDIA RTX 4080 16GB",
        "min_price": 1000,
        "max_price": 1200,
        "required": True
    },
    "ram": {
        "name": "DDR5 64GB Kit (2x32GB) 5600MHz",
        "min_price": 300,
        "max_price": 400,
        "required": True
    },
    "ssd": {
        "name": "SSD 2TB NVMe PCIe 4.0",
        "min_price": 150,
        "max_price": 200,
        "required": True
    },
    "motherboard": {
        "name": "Motherboard Z790 ATX",
        "min_price": 250,
        "max_price": 350,
        "required": False
    },
    "psu": {
        "name": "Alimentatore 1000W 80+ Gold",
        "min_price": 150,
        "max_price": 200,
        "required": False
    },
    "case": {
        "name": "Case ATX Mid Tower con buona ventilazione",
        "min_price": 100,
        "max_price": 150,
        "required": False
    }
}

# Fonti prezzo (Italia)
PRICE_SOURCES = [
    "https://www.amazon.it",
    "https://www.eprice.it",
    "https://www.subito.it",
    "https://www.kimolbrunello.it",
    "https://www.pcbox.it",
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/riccardomoricone/telegram-bot-pc-components/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database setup
DB_PATH = "/Users/riccardomoricone/telegram-bot-pc-components/prices.db"

def init_db():
    """Inizializza il database SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            source TEXT NOT NULL,
            price REAL NOT NULL,
            url TEXT NOT NULL,
            date TEXT NOT NULL,
            seller_rating REAL,
            seller_name TEXT,
            UNIQUE(component, source, date)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            message_id INTEGER,
            sent_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def send_message(text: str, parse_mode: str = "HTML") -> dict:
    """Invia messaggio al bot Telegram"""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": parse_mode
            },
            timeout=30
        )
        return response.json()
    except Exception as e:
        logger.error(f"Errore invio messaggio: {e}")
        return {}

def send_photo_with_caption(photo_url: str, caption: str) -> dict:
    """Invia foto con didascalia"""
    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "HTML"
            },
            timeout=30
        )
        return response.json()
    except Exception as e:
        logger.error(f"Errore invio foto: {e}")
        return {}

def scrape_amazon_it(component_name: str) -> List[Dict]:
    """Scansiona Amazon Italia per componenti"""
    results = []
    try:
        search_url = f"https://www.amazon.it/s?k={component_name.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
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
                        url = f"https://amazon.it{href}" if href and not href.startswith('http') else href
                        
                        price_tag = product.find('span', class_='a-price-whole')
                        price = 0.0
                        if price_tag and price_tag.get_text():
                            price_text = price_tag.get_text().replace('.', '').replace(',', '.')
                            try:
                                price = float(price_text)
                            except ValueError:
                                price = 0.0
                        
                        results.append({
                            'name': name,
                            'price': price,
                            'url': url,
                            'source': 'Amazon.it'
                        })
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Errore scraping Amazon: {e}")
    
    return results

def scrape_eprice(component_name: str) -> List[Dict]:
    """Scansiona EPrice per componenti"""
    results = []
    try:
        search_url = f"https://www.eprice.it/prodotti/{component_name.replace(' ', '-')}"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        
        response = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        products = soup.find_all('article', class_='product-card')
        
        for product in products[:5]:
            try:
                title = product.find('h3')
                if title:
                    name = title.get_text(strip=True)
                    a_tag = title.find('a')
                    url = a_tag.get('href', '') if a_tag else ""
                    if url and not url.startswith('http'):
                        url = f"https://eprice.it{url}"
                    
                    price_tag = product.find('span', class_='price')
                    if price_tag:
                        price_text = price_tag.get_text().replace('€', '').replace(',', '.')
                        try:
                            price = float(price_text)
                        except ValueError:
                            continue
                        
                        results.append({
                            'name': name,
                            'price': price,
                            'url': url,
                            'source': 'EPrice.it'
                        })
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Errore scraping EPrice: {e}")
    
    return results

def get_price_history(component: str) -> List[Dict]:
    """Recupera storico prezzi dal database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT source, price, url, date, seller_rating, seller_name
        FROM price_history
        WHERE component = ?
        ORDER BY date DESC
        LIMIT 30
    ''', (component,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'source': row[0],
            'price': row[1],
            'url': row[2],
            'date': row[3],
            'seller_rating': row[4],
            'seller_name': row[5]
        }
        for row in rows
    ]

def save_price(component: str, source: str, price: float, url: str, 
               seller_rating: Optional[float] = None, seller_name: Optional[str] = None):
    """Salva prezzo nel database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        INSERT OR REPLACE INTO price_history
        (component, source, price, url, date, seller_rating, seller_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (component, source, price, url, today, seller_rating, seller_name))
    
    conn.commit()
    conn.close()

def check_price_oscillations(component: str) -> Dict:
    """Analizza oscillazioni prezzi"""
    history = get_price_history(component)
    
    if len(history) < 2:
        return {'change': 0.0, 'change_percent': 0.0, 'trend': 'insufficient_data'}
    
    today_price = history[0]['price']
    yesterday_price = history[1]['price']
    
    change = today_price - yesterday_price
    change_percent = (change / yesterday_price * 100) if yesterday_price > 0 else 0.0
    
    if change_percent > 5:
        trend = 'price_increase'
    elif change_percent < -5:
        trend = 'price_decrease'
    else:
        trend = 'stable'
    
    return {
        'change': change,
        'change_percent': change_percent,
        'trend': trend,
        'today_price': today_price,
        'yesterday_price': yesterday_price
    }

def generate_price_chart_html(component: str) -> str:
    """Genera HTML per grafico prezzi"""
    history = get_price_history(component)
    
    if not history:
        return "<p>Nessun dato storico disponibile</p>"
    
    dates = [h['date'] for h in history[-15:]]
    prices = [h['price'] for h in history[-15:]]
    
    if not dates:
        return "<p>Nessun dato disponibile</p>"
    
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price if max_price != min_price else 1
    
    width = 400
    height = 200
    margin = 30
    
    chart_width = width - 2 * margin
    chart_height = height - 2 * margin
    
    points = []
    for i, price in enumerate(prices):
        x = margin + (i / (len(prices) - 1)) * chart_width if len(prices) > 1 else margin
        y = height - margin - ((price - min_price) / price_range) * chart_height
        points.append(f"{x},{y}")
    
    points_str = " L ".join(points)
    
    html = f'''
    <div style="font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 15px; border-radius: 10px; margin: 10px 0;">
        <h4 style="margin: 0 0 10px 0; color: #00d4ff;">📊 Storico Prezzi: {component}</h4>
        <svg width="{width}" height="{height}">
            <polyline points="{points_str}" fill="none" stroke="#00d4ff" stroke-width="2"/>
            <circle cx="{margin}" cy="{height - margin - ((prices[-1] - min_price) / price_range) * chart_height}" r="4" fill="#ff6b6b"/>
        </svg>
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #888;">
            <span>{dates[0]}</span>
            <span>{dates[-1]}</span>
        </div>
        <div style="margin-top: 5px; font-size: 12px;">
            <span style="color: #4ecdc4;">Min: €{min_price:.2f}</span>
            <span style="color: #ff6b6b; margin-left: 15px;">Max: €{max_price:.2f}</span>
        </div>
    </div>
    '''
    return html

def generate_pdf_report(component: str, prices: List[Dict]) -> bytes:
    """Genera PDF con report dettagliato"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    import io
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    styles = getSampleStyleSheet()
    story = []
    
    title = Paragraph(f"<b>📊 Report Componente: {component}</b>", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 10))
    
    date_p = Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    story.append(date_p)
    story.append(Spacer(1, 10))
    
    if prices:
        data = [['Fonte', 'Prezzo', 'Data', 'Link']]
        for p in prices[:20]:
            link = f'<a href="{p["url"]}">{p["source"]}</a>'
            data.append([p['source'], f"€{p['price']:.2f}", p['date'], link])
        
        table = Table(data, colWidths=[100*mm, 40*mm, 40*mm, 60*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

async def fetch_all_prices():
    """Recupera tutti i prezzi dalle fonti"""
    all_prices = {}
    
    for comp_type, comp_info in TARGET_COMPONENTS.items():
        logger.info(f"Cerco prezzi per: {comp_info['name']}")
        
        prices = []
        prices.extend(scrape_amazon_it(comp_info['name']))
        prices.extend(scrape_eprice(comp_info['name']))
        
        if prices:
            prices.sort(key=lambda x: x['price'])
            best = prices[0]
            
            save_price(
                comp_info['name'],
                best['source'],
                best['price'],
                best['url']
            )
            
            all_prices[comp_type] = {
                'component': comp_info['name'],
                'best_price': best['price'],
                'best_source': best['source'],
                'best_url': best['url'],
                'all_prices': prices[:5]
            }
    
    return all_prices

async def send_morning_news():
    """Invia notizie mattutine"""
    logger.info("Invio notizie mattutine...")
    
    prices = await fetch_all_prices()
    
    report_lines = ["<b>🌅 NOTIZIE MATTUTINE - Componenti PC Windows</b>"]
    report_lines.append(f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>")
    report_lines.append("")
    
    for comp_type, data in prices.items():
        if data:
            osc = check_price_oscillations(data['component'])
            trend_emoji = "📈" if osc['trend'] == 'price_increase' else "📉" if osc['trend'] == 'price_decrease' else "➡️"
            
            report_lines.append(f"<b>{trend_emoji} {data['component']}</b>")
            report_lines.append(f"   Prezzo migliore: <b>€{data['best_price']:.2f}</b> su {data['best_source']}")
            report_lines.append(f"   <a href='{data['best_url']}'>Dettagli prodotto</a>")
            if osc['trend'] != 'insufficient_data':
                report_lines.append(f"   Variazione: {osc['change_percent']:+.2f}%")
            report_lines.append("")
    
    send_message("\n".join(report_lines))

async def send_evening_news():
    """Invia notizie serali con confronto prezzi"""
    logger.info("Invio notizie serali...")
    
    prices = await fetch_all_prices()
    
    report_lines = ["<b>🌇 CONFRONTO PREZZI SERE - Componenti PC Windows</b>"]
    report_lines.append(f"<i>{datetime.now().strftime('%d/%m/%Y %H:%M')}</i>")
    report_lines.append("")
    
    report_lines.append("<b>📊 Confronto Prezzi</b>")
    report_lines.append("<table cellpadding='5' cellspacing='0'>")
    report_lines.append("<tr><th>Componente</th><th>Miglior Prezzo</th><th>Fonte</th><th>Trend</th></tr>")
    
    for comp_type, data in prices.items():
        if data:
            osc = check_price_oscillations(data['component'])
            trend = "📈" if osc['trend'] == 'price_increase' else "📉" if osc['trend'] == 'price_decrease' else "➡️"
            
            report_lines.append(f"<tr><td>{data['component']}</td>")
            report_lines.append(f"<td><b>€{data['best_price']:.2f}</b></td>")
            report_lines.append(f"<td>{data['best_source']}</td>")
            report_lines.append(f"<td>{trend}</td></tr>")
    
    report_lines.append("</table>")
    report_lines.append("")
    
    report_lines.append("<b>💡 Consigli per l'acquisto:</b>")
    for comp_type, data in prices.items():
        if data:
            min_price = TARGET_COMPONENTS[comp_type]['min_price']
            max_price = TARGET_COMPONENTS[comp_type]['max_price']
            if data['best_price'] > min_price * 0.8:
                if data['best_price'] <= max_price:
                    report_lines.append(f"✅ {data['component']}: Prezzo ottimale!")
                else:
                    report_lines.append(f"⚠️ {data['component']}: Prezzo alto, attendi offerte")
    
    send_message("\n".join(report_lines))
    
    for comp_type, data in prices.items():
        if data:
            pdf_bytes = generate_pdf_report(data['component'], data['all_prices'])
            pdf_path = f"/Users/riccardomoricone/telegram-bot-pc-components/reports/{data['component'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)

async def check_prebuilt_pcs():
    """Cerca computer fissi pre-assemblati"""
    logger.info("Controllo computer fissi pre-assemblati...")
    
    search_terms = [
        "PC Gaming i9 32GB RTX 4080",
        "PC Gaming Ryzen 9 RTX 4080",
        "Workstation 64GB DDR5 RTX 4080"
    ]
    
    for term in search_terms:
        results = scrape_amazon_it(term)
        for r in results[:3]:
            save_price(
                f"PC Pre-assemblato: {term}",
                r['source'],
                r['price'],
                r['url']
            )

def main():
    """Main entry point"""
    init_db()
    
    try:
        response = requests.get(f"{TELEGRAM_API}/getMe", timeout=10)
        if response.status_code == 200:
            logger.info("Bot Telegram connesso correttamente")
        else:
            logger.error(f"Errore connessione bot: {response.text}")
    except Exception as e:
        logger.error(f"Errore verifica bot: {e}")
    
    send_message("<b>✅ Bot Telegram attivo per monitoraggio componenti PC!</b>")
    send_message("<i>Ti invierò notizie due volte al giorno su componenti Windows con prezzi e storici.</i>")

if __name__ == "__main__":
    main()