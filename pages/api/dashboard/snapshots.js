// pages/api/dashboard/snapshots.js
// Storico snapshot Telegram (variazioni prezzo)
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';

export default async function handler(req, res) {
  const { component, limit = 50 } = req.query;
  const compFilter = component || '__all__';
  const limitNum = parseInt(limit) || 50;

  const PYTHON_SCRIPT = `
import sqlite3, json, os
base = "${BASE}"
conn = sqlite3.connect(os.path.join(base, "history.db"))
conn.row_factory = sqlite3.Row

# Get snapshots (all or filtered)
if "${compFilter}" != "__all__":
    rows = conn.execute(
        "SELECT ts, component, best_price, best_source FROM snapshots WHERE component = ? ORDER BY ts DESC LIMIT ?",
        ("${compFilter}", ${limitNum})
    ).fetchall()
else:
    rows = conn.execute(
        "SELECT ts, component, best_price, best_source FROM snapshots ORDER BY ts DESC LIMIT ?",
        (${limitNum},)
    ).fetchall()

snapshots = [dict(r) for r in rows]

# Get available components
comps = conn.execute("SELECT DISTINCT component FROM snapshots ORDER BY component").fetchall()
component_list = [r["component"] for r in comps]

conn.close()
print(json.dumps({"components": component_list, "snapshots": snapshots}))
`;

  try {
    const { stdout } = await execFileAsync('python3', ['-c', PYTHON_SCRIPT], { timeout: 10000 });
    const result = JSON.parse(stdout.trim());

    res.status(200).json(result);
  } catch (e) {
    console.error('snapshots error:', e);
    res.status(500).json({ error: e.message });
  }
}
