#!/usr/bin/env python3
"""
Backend API per monitoraggio prezzi componenti PC
Esecuzione scraping in tempo reale da multiple fonti EU
"""

from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Componenti da monitorare
COMPONENTS = {
    "Ryzen 7 7800X3D": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JQ",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JQ"
    },
    "Ryzen 9 7950X3D": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JR",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JR"
    },
    "RTX 5080 16GB": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JS",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JS"
    },
    "RX 7900 XTX": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JT",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JT"
    },
    "DDR5 64GB Kit 5600MHz": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JU",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JU"
    },
    "SSD 2TB NVMe PCIe 4.0": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JV",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JV"
    },
    "ASUS Z790-A Gaming WiFi II": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JW",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JW"
    },
    "Corsair RM1000x 1000W Platinum": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JX",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JX"
    },
    "Fractal Design Meshify 2": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JY",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JY"
    },
    "Noctua NH-D15": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7JZ",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7JZ"
    },
    "Noctua NF-A12x25 3-pack": {
        "amazon_de": "https://www.amazon.de/dp/B0C9V3J7KA",
        "amazon_it": "https://www.amazon.it/dp/B0C9V3J7KA"
    }
}

def scrape_amazon(url, country="de"):
    """Scrapes Amazon product page for price"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Try multiple selectors for price
        price_selectors = [
            'span.a-price-whole',
            'span[data-a-strike="true"] span.a-price-whole',
            '.a-price .a-offscreen'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                # Extract price (remove non-numeric characters)
                price_match = re.search(r'[\d,]+', price_text.replace(',', '.'))
                if price_match:
                    return float(price_match.group())
        
        return None
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None

def scrape_eprice(url):
    """Scrapes EPrice product page for price"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')
        
        price_elem = soup.select_one('.price, .product-price')
        if price_elem:
            price_text = price_elem.get_text().strip()
            price_match = re.search(r'[\d,]+', price_text.replace(',', '.'))
            if price_match:
                return float(price_match.group())
        
        return None
    except Exception as e:
        logger.error(f"Error scraping EPrice {url}: {e}")
        return None

def get_prices_for_component(component_name):
    """Get all prices for a component from all sources"""
    if component_name not in COMPONENTS:
        return None
    
    component_data = COMPONENTS[component_name]
    prices = {}
    
    # Scrape Amazon.de
    if 'amazon_de' in component_data:
        price = scrape_amazon(component_data['amazon_de'], 'de')
        if price:
            prices['Amazon.de'] = {'price': price, 'url': component_data['amazon_de']}
    
    # Scrape Amazon.it
    if 'amazon_it' in component_data:
        price = scrape_amazon(component_data['amazon_it'], 'it')
        if price:
            prices['Amazon.it'] = {'price': price, 'url': component_data['amazon_it']}
    
    # Scrape Amazon.fr
    if 'amazon_fr' in component_data:
        price = scrape_amazon(component_data['amazon_fr'], 'fr')
        if price:
            prices['Amazon.fr'] = {'price': price, 'url': component_data['amazon_fr']}
    
    # Scrape EPrice
    if 'eprice' in component_data:
        price = scrape_eprice(component_data['eprice'])
        if price:
            prices['EPrice.it'] = {'price': price, 'url': component_data['eprice']}
    
    return prices

@app.route('/api/prices', methods=['GET'])
def get_all_prices():
    """API endpoint to get all current prices"""
    result = {
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    for component in COMPONENTS.keys():
        prices = get_prices_for_component(component)
        if prices:
            result['components'][component] = prices
    
    return jsonify(result)

@app.route('/api/prices/<component>', methods=['GET'])
def get_component_prices(component):
    """API endpoint to get prices for a specific component"""
    prices = get_prices_for_component(component)
    if prices:
        return jsonify({
            'component': component,
            'timestamp': datetime.now().isoformat(),
            'prices': prices
        })
    return jsonify({'error': 'Component not found'}), 404

@app.route('/api/best-price/<component>', methods=['GET'])
def get_best_price(component):
    """API endpoint to get the best price for a component"""
    prices = get_prices_for_component(component)
    if prices:
        best_source = min(prices.keys(), key=lambda k: prices[k]['price'])
        return jsonify({
            'component': component,
            'best_source': best_source,
            'best_price': prices[best_source]['price'],
            'url': prices[best_source]['url'],
            'all_prices': prices
        })
    return jsonify({'error': 'Component not found'}), 404

@app.route('/api/components', methods=['GET'])
def get_components():
    """API endpoint to get list of all components"""
    return jsonify({
        'components': list(COMPONENTS.keys()),
        'count': len(COMPONENTS)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)