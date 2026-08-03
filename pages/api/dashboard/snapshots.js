// pages/api/dashboard/snapshots.js
// Storico snapshot Telegram — fallback a data.json se history.db non disponibile
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';

export default async function handler(req, res) {
  const { component, limit = 50 } = req.query;
  const limitNum = parseInt(limit) || 50;

  // Try history.db via Python (local only)
  const PYTHON_SCRIPT = `
import sqlite3, json, os
base = "${BASE}"
db = os.path.join(base, "history.db")
if not os.path.exists(db):
    print(json.dumps({"components": [], "snapshots": []}))
    exit(0)
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
comp = "${component}" if "${component}" != "undefined" else None
if comp:
    rows = conn.execute(
        "SELECT ts, component, best_price, best_source FROM snapshots WHERE component = ? ORDER BY ts DESC LIMIT ?",
        (comp, ${limitNum})
    ).fetchall()
else:
    rows = conn.execute(
        "SELECT ts, component, best_price, best_source FROM snapshots ORDER BY ts DESC LIMIT ?",
        (${limitNum},)
    ).fetchall()
comps = conn.execute("SELECT DISTINCT component FROM snapshots ORDER BY component").fetchall()
conn.close()
result = {
    "components": [r["component"] for r in comps],
    "snapshots": [dict(r) for r in rows]
}
print(json.dumps(result))
`;

  try {
    const { stdout } = await execFileAsync('python3', ['-c', PYTHON_SCRIPT], { timeout: 10000 });
    const result = JSON.parse(stdout.trim());
    res.status(200).json(result);
  } catch (e) {
    // Fallback: return empty
    res.status(200).json({ components: [], snapshots: [], error: e.message });
  }
}
