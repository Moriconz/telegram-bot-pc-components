// pages/api/dashboard/snapshots.js
// Reads from data.json as fallback (no DB on Vercel)
import fs from 'fs';
import path from 'path';

const BASE = process.cwd();

export default async function handler(req, res) {
  const { component, limit = 50 } = req.query;
  const limitNum = parseInt(limit) || 50;

  const p = path.join(BASE, 'data.json');
  if (!fs.existsSync(p)) {
    return res.status(200).json({ components: [], snapshots: [] });
  }

  try {
    const data = JSON.parse(fs.readFileSync(p, 'utf8'));
    const components = data.components || {};

    // Build pseudo-snapshots from data.json
    const componentList = Object.keys(components);
    const snapshots = [];

    if (component && component !== 'undefined') {
      const comp = components[component];
      if (comp) {
        const prices = Object.entries(comp.prices || {});
        prices.forEach(([src, v]) => {
          if (v.price_eur != null) {
            snapshots.push({
              ts: data.updated_at || new Date().toISOString(),
              component: component,
              best_price: v.price_eur,
              best_source: src,
            });
          }
        });
      }
    } else {
      // All components, their best price
      for (const [name, comp] of Object.entries(components)) {
        const prices = Object.entries(comp.prices || {});
        let best = null;
        for (const [src, v] of prices) {
          if (v.price_eur != null && (best === null || v.price_eur < best.price)) {
            best = { price: v.price_eur, source: src };
          }
        }
        if (best) {
          snapshots.push({
            ts: data.updated_at || new Date().toISOString(),
            component: name,
            best_price: best.price,
            best_source: best.source,
          });
        }
      }
    }

    res.status(200).json({
      components: componentList,
      snapshots: snapshots.slice(0, limitNum),
    });
  } catch (e) {
    res.status(200).json({ components: [], snapshots: [], error: e.message });
  }
}
