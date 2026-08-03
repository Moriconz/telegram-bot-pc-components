// pages/api/dashboard/prices-history.js
// Storico prezzi giornaliero per un componente
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';

export default async function handler(req, res) {
  const { component } = req.query;
  if (!component) {
    return res.status(400).json({ error: 'Missing component query param' });
  }

  const PYTHON_SCRIPT = `
import sqlite3, json, urllib.parse, os
base = "${BASE}"
conn = sqlite3.connect(os.path.join(base, "prices.db"))
conn.row_factory = sqlite3.Row
comp = urllib.parse.unquote("${component}")
rows = conn.execute(
    "SELECT source, price, date FROM prices WHERE component = ? ORDER BY date DESC",
    (comp,)
).fetchall()
conn.close()

result = [{"source": r["source"], "price": r["price"], "date": r["date"]} for r in rows]
print(json.dumps(result))
`;

  try {
    const { stdout } = await execFileAsync('python3', ['-c', PYTHON_SCRIPT], { timeout: 10000 });
    const data = JSON.parse(stdout.trim());

    // Group by source
    const bySource = {};
    data.forEach(r => {
      if (!bySource[r.source]) bySource[r.source] = [];
      bySource[r.source].push({ price: r.price, date: r.date });
    });

    res.status(200).json({
      component,
      data,
      bySource,
    });
  } catch (e) {
    console.error('prices-history error:', e);
    res.status(500).json({ error: e.message });
  }
}
