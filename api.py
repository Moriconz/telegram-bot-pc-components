#!/usr/bin/env python3
"""
API Flask per fornire i prezzi dal database SQLite
+ Dashboard dell'agente autonomo (health, stats, metrics)
"""

from flask import Flask, jsonify
import sqlite3
from datetime import datetime
import logging
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
DB_PATH = '/Users/riccardomoricone/telegram-bot-pc-components/prices.db'
LOG_PATH = '/Users/riccardomoricone/telegram-bot-pc-components/logs/agent_log.jsonl'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/prices', methods=['GET'])
def get_all_prices():
    """Get all prices from database"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get latest price for each component from each source (window function fix)
        c.execute('''SELECT component, source, price, url, date 
                     FROM (
                       SELECT component, source, price, url, date,
                              ROW_NUMBER() OVER (PARTITION BY component, source ORDER BY rowid DESC) as rn
                       FROM prices
                     )
                     WHERE rn = 1
                     ORDER BY component''')
        
        rows = c.fetchall()
        conn.close()
        
        # Organize by component
        components = {}
        for row in rows:
            component = row['component']
            if component not in components:
                components[component] = {}
            components[component][row['source']] = {
                'price': row['price'],
                'url': row['url'],
                'date': row['date']
            }
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'components': components
        })
    except Exception as e:
        logger.error(f"Error getting prices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prices/<component>', methods=['GET'])
def get_component_prices(component):
    """Get prices for specific component"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''SELECT source, price, url, date 
                     FROM (
                       SELECT source, price, url, date,
                              ROW_NUMBER() OVER (PARTITION BY source ORDER BY rowid DESC) as rn
                       FROM prices WHERE component = ?
                     )
                     WHERE rn = 1
                     ORDER BY price ASC''', (component,))
        
        rows = c.fetchall()
        conn.close()
        
        prices = {row['source']: {
            'price': row['price'],
            'url': row['url'],
            'date': row['date']
        } for row in rows}
        
        return jsonify({
            'component': component,
            'timestamp': datetime.now().isoformat(),
            'prices': prices
        })
    except Exception as e:
        logger.error(f"Error getting component prices: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/best-price/<component>', methods=['GET'])
def get_best_price(component):
    """Get the best price for a component"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''SELECT source, price, url 
                     FROM (
                       SELECT source, price, url,
                              ROW_NUMBER() OVER (PARTITION BY source ORDER BY rowid DESC) as rn
                       FROM prices WHERE component = ?
                     )
                     WHERE rn = 1
                     ORDER BY price ASC 
                     LIMIT 1''', (component,))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'component': component,
                'best_source': row['source'],
                'best_price': row['price'],
                'url': row['url']
            })
        return jsonify({'error': 'Component not found'}), 404
    except Exception as e:
        logger.error(f"Error getting best price: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/components', methods=['GET'])
def get_components():
    """Get list of all components"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT DISTINCT component FROM prices ORDER BY component')
        components = [row['component'] for row in c.fetchall()]
        conn.close()
        
        return jsonify({
            'components': components,
            'count': len(components)
        })
    except Exception as e:
        logger.error(f"Error getting components: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



# ========== DASHBOARD ENDPOINTS ==========

import json
from collections import defaultdict
from task_planner import get_health_status, should_retry, get_ua_pool, _read_recent_events


@app.route('/api/dashboard/health', methods=['GET'])
def dashboard_health():
    """Health summary per la dashboard."""
    try:
        health = get_health_status()
        # Aggiungi ultime 10 attività
        recent = _read_recent_events(60)
        health["recent_activity"] = recent[-10:] if recent else []
        return jsonify(health)
    except Exception as e:
        logger.error(f"Dashboard health error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/failure-map', methods=['GET'])
def dashboard_failure_map():
    """Mappa di guasti per TLD — mostra quali marketplace stanno fallendo."""
    events = _read_recent_events(1440)
    failures_by_tld = defaultdict(int)
    ok_by_tld = defaultdict(int)

    for e in events:
        if e.get("task") != "scraper":
            continue
        tld = e.get("tld")
        if not tld:
            continue
        if e.get("status") == "ok":
            ok_by_tld[tld] += 1
        elif e.get("status") in ("error", "warn"):
            failures_by_tld[tld] += 1

    result = []
    for tld in ok_by_tld.keys() | failures_by_tld.keys():
        total = ok_by_tld[tld] + failures_by_tld[tld]
        result.append({
            "tld": tld,
            "ok": ok_by_tld[tld],
            "failures": failures_by_tld[tld],
            "success_rate": round(ok_by_tld[tld] / total * 100, 1) if total else 0,
        })
    return jsonify({"failure_map": sorted(result, key=lambda x: x["tld"])})


@app.route('/api/dashboard/metrics', methods=['GET'])
def dashboard_metrics():
    """Metriche aggregate per dashboard."""
    events = _read_recent_events(1440)

    # Componenti con prezzi OK vs falliti
    scraper_events = [e for e in events if e.get("task") == "scraper"]
    ok_components = set()
    failed_components = set()
    for e in scraper_events:
        if e.get("status") == "ok":
            ok_components.add((e.get("tld"), e.get("component")))
        elif e.get("status") in ("error", "warn"):
            failed_components.add((e.get("tld"), e.get("component")))

    return jsonify({
        "total_scrape_events": len(scraper_events),
        "components_with_price": len(ok_components),
        "components_failed": len(failed_components),
        "failed_combos": [{"tld": t, "component": c} for t, c in sorted(failed_components)],
        "ua_pool_size": len(get_ua_pool()),
    })