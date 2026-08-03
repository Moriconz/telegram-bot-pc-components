// pages/api/dashboard/bot-status.js
// Status del bot Telegram + ultime statistiche
// NOTA: usa Python inline per SQLite (Node non ha sqlite3 installato in questo repo)
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';
const LOG_PATH = `${BASE}/logs/agent_log.jsonl`;

function readRecentLogs(n = 50) {
  if (!fs.existsSync(LOG_PATH)) return [];
  const lines = fs.readFileSync(LOG_PATH, 'utf8').split('\n').filter(Boolean);
  return lines.slice(-n).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
}

const PYTHON_SCRIPT = `
import sqlite3, json, os, sys
base = "${BASE}"
prices_db = os.path.join(base, "prices.db")
hist_db = os.path.join(base, "history.db")

# Latest price per component/source
conn = sqlite3.connect(prices_db)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT component, source, price, date FROM prices
    WHERE rowid IN (SELECT MAX(rowid) FROM prices GROUP BY component, source)
    ORDER BY component
""").fetchall()
conn.close()

components = {}
sources_set = set()
for r in rows:
    if r["component"] not in components:
        components[r["component"]] = []
    components[r["component"]].append({"source": r["source"], "price": r["price"], "date": r["date"]})
    sources_set.add(r["source"])

# Snapshot days from history.db
try:
    conn2 = sqlite3.connect(hist_db)
    snapshot_days = conn2.execute("SELECT COUNT(DISTINCT ts) FROM snapshots").fetchone()[0]
    conn2.close()
except:
    snapshot_days = 0

result = {
    "components": len(components),
    "component_list": list(components.keys()),
    "sources": list(sources_set),
    "snapshot_days": snapshot_days,
}
print(json.dumps(result))
`;

export default async function handler(req, res) {
  try {
    const { stdout } = await execFileAsync('python3', ['-c', PYTHON_SCRIPT], { timeout: 10000 });
    const dbData = JSON.parse(stdout.trim());

    const recentLogs = readRecentLogs(20);
    const recentErrors = recentLogs.filter(e => e.status === 'error' || e.status === 'warn');

    res.status(200).json({
      bot: {
        name: "@ComponentiPCconIA_bot",
        token: "8932041955:***",
        chatId: 508375146,
        status: "active",
        lastRun: recentLogs.length > 0 ? recentLogs[recentLogs.length - 1].ts : null,
      },
      components: dbData.components,
      sources: dbData.sources,
      snapshotDays: dbData.snapshot_days,
      componentList: dbData.component_list,
      recentActivity: recentLogs.slice(-10),
      recentErrors: recentErrors.slice(-5),
      errorCount: recentErrors.length,
    });
  } catch (e) {
    console.error('bot-status error:', e);
    res.status(500).json({ error: e.message });
  }
}
