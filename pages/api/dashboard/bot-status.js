// pages/api/dashboard/bot-status.js
// Endpoint fallback: usa data.json se prices.db non disponibile
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execFileAsync = promisify(execFile);
const BASE = '/Users/riccardomoricone/telegram-bot-pc-components';
const DATA_PATH = `${BASE}/data.json`;
const LOG_PATH = `${BASE}/logs/agent_log.jsonl`;

function readRecentLogs(n = 50) {
  if (!fs.existsSync(LOG_PATH)) return [];
  const lines = fs.readFileSync(LOG_PATH, 'utf8').split('\n').filter(Boolean);
  return lines.slice(-n).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
}

function readDataJson() {
  if (!fs.existsSync(DATA_PATH)) return null;
  try {
    const raw = fs.readFileSync(DATA_PATH, 'utf8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

const PYTHON_SCRIPT = `
import sqlite3, json, os, sys
base = "${BASE}"
# Try prices.db first
prices_db = os.path.join(base, "prices.db")
if not os.path.exists(prices_db):
    # Fallback to data.json
    data_json = os.path.join(base, "data.json")
    if os.path.exists(data_json):
        with open(data_json) as f:
            d = json.load(f)
        components = {}
        sources = set()
        comp_list = list(d.get("components", {}).keys())
        for name, comp in d.get("components", {}).items():
            for src, v in comp.get("prices", {}).items():
                if v.get("price_eur") is not None:
                    if name not in components:
                        components[name] = []
                    components[name].append({"source": src, "price": v["price_eur"], "date": d.get("updated_at", "N/A")})
                    sources.add(src)
        print(json.dumps({"components": len(components), "sources": list(sources), "component_list": comp_list, "snapshot_days": 0}))
    else:
        print(json.dumps({"components": 0, "sources": [], "component_list": [], "snapshot_days": 0}))
    sys.exit(0)

conn = sqlite3.connect(prices_db)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT component, source, price, date FROM prices
    WHERE rowid IN (SELECT MAX(rowid) FROM prices GROUP BY component, source)
    ORDER BY component
""").fetchall()
conn.close()
components = {}
sources = set()
for r in rows:
    if r["component"] not in components: components[r["component"]] = []
    components[r["component"]].append({"source": r["source"], "price": r["price"], "date": r["date"]})
    sources.add(r["source"])
print(json.dumps({"components": len(components), "sources": list(sources), "component_list": list(components.keys()), "snapshot_days": 0}))
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
      components: dbData.components || 0,
      sources: dbData.sources || [],
      componentList: dbData.component_list || [],
      snapshotDays: dbData.snapshot_days || 0,
      recentActivity: recentLogs.slice(-10),
      recentErrors: recentErrors.slice(-5),
      errorCount: recentErrors.length,
    });
  } catch (e) {
    // Last-resort fallback: data.json
    const dataJson = readDataJson();
    const recentLogs = readRecentLogs(10);
    res.status(200).json({
      bot: {
        name: "@ComponentiPCconIA_bot",
        token: "8932041955:***",
        chatId: 508375146,
        status: "active",
        lastRun: recentLogs.length > 0 ? recentLogs[recentLogs.length - 1].ts : null,
      },
      components: dataJson ? Object.keys(dataJson.components || {}).length : 0,
      sources: dataJson ? [...new Set(Object.values(dataJson.components || {}).flatMap(c => Object.keys(c.prices || {})))] : [],
      componentList: dataJson ? Object.keys(dataJson.components || {}) : [],
      snapshotDays: 0,
      recentActivity: recentLogs.slice(-10) || [],
      recentErrors: [],
      errorCount: 0,
      fallback: true,
    });
  }
}
