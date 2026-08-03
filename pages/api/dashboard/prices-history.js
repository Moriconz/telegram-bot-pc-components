// pages/api/dashboard/prices-history.js
// Storico prezzi per componente — usa data.json come fallback
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';

export default async function handler(req, res) {
  const { component } = req.query;
  if (!component) {
    return res.status(400).json({ error: 'Missing component query param' });
  }

  // Try reading from data.json first (always available on Vercel)
  const dataPath = `${BASE}/data.json`;
  if (fs.existsSync(dataPath)) {
    try {
      const raw = fs.readFileSync(dataPath, 'utf8');
      const data = JSON.parse(raw);
      const comp = data.components?.[component];
      if (comp) {
        const prices = [];
        const bySource = {};
        for (const [src, v] of Object.entries(comp.prices || {})) {
          if (v.price_eur != null) {
            const entry = { source: src, price: v.price_eur, date: data.updated_at || 'N/A' };
            prices.push(entry);
            if (!bySource[src]) bySource[src] = [];
            bySource[src].push(entry);
          }
        }
        return res.status(200).json({ component, data: prices, bySource });
      }
    } catch (e) {
      // Fall through to Python DB query
    }
  }

  // Fallback: try SQLite via Python (local only)
  const PYTHON_SCRIPT = `
import sqlite3, json, os
base = "${BASE}"
db = os.path.join(base, "prices.db")
if not os.path.exists(db):
    print(json.dumps({"error": "DB not found"}))
    exit(1)
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT source, price, date FROM prices WHERE component = ? ORDER BY date DESC",
    ("${component}",)
).fetchall()
conn.close()
result = [{"source": r["source"], "price": r["price"], "date": r["date"]} for r in rows]
print(json.dumps(result))
`;

  try {
    const { stdout } = await execFileAsync('python3', ['-c', PYTHON_SCRIPT], { timeout: 10000 });
    const data = JSON.parse(stdout.trim());
    if (Array.isArray(data)) {
      const bySource = {};
      data.forEach(p => {
        if (!bySource[p.source]) bySource[p.source] = [];
        bySource[p.source].push(p);
      });
      res.status(200).json({ component, data, bySource });
    } else {
      res.status(200).json({ component, data: [], bySource: {} });
    }
  } catch (e) {
    res.status(200).json({ component, data: [], bySource: {}, error: e.message });
  }
}
