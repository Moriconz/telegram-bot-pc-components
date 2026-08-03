// pages/api/dashboard/prices-history.js
// Reads price history from data.json (committed)
import fs from 'fs';
import path from 'path';

const BASE = process.cwd();

export default async function handler(req, res) {
  const { component } = req.query;
  if (!component) {
    return res.status(400).json({ error: 'Missing component query param' });
  }

  const p = path.join(BASE, 'data.json');
  if (!fs.existsSync(p)) {
    return res.status(200).json({ component, data: [], bySource: {}, error: "data.json not found" });
  }

  try {
    const data = JSON.parse(fs.readFileSync(p, 'utf8'));
    const comp = data.components?.[component];
    if (!comp) {
      return res.status(200).json({ component, data: [], bySource: {}, error: "Component not found in data.json" });
    }

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

    res.status(200).json({ component, data: prices, bySource, updatedAt: data.updated_at });
  } catch (e) {
    res.status(500).json({ component, error: e.message });
  }
}
