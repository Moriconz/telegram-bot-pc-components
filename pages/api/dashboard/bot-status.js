// pages/api/dashboard/bot-status.js
// Reads from data.json (committed) + logs/agent_log.jsonl if available
import fs from 'fs';
import path from 'path';

const BASE = process.cwd();

function readDataJson() {
  const p = path.join(BASE, 'data.json');
  if (!fs.existsSync(p)) return null;
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

function readAgentLog(n = 50) {
  const p = path.join(BASE, 'logs', 'agent_log.jsonl');
  if (!fs.existsSync(p)) return [];
  const lines = fs.readFileSync(p, 'utf8').split('\n').filter(Boolean);
  return lines.slice(-n).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
}

export default async function handler(req, res) {
  const dataJson = readDataJson();
  const logs = readAgentLog(50);

  if (dataJson) {
    const components = dataJson.components || {};
    const sources = new Set();
    for (const comp of Object.values(components)) {
      for (const src of Object.keys(comp.prices || {})) {
        sources.add(src);
      }
    }

    const recentErrors = logs.filter(e => e.status === 'error' || e.status === 'warn');

    res.status(200).json({
      bot: {
        name: "@ComponentiPCconIA_bot",
        token: "8932041955:***",
        chatId: 508375146,
        status: "active",
        lastRun: logs.length > 0 ? logs[logs.length - 1].ts : dataJson.updated_at || null,
      },
      components: Object.keys(components).length,
      sources: Array.from(sources),
      componentList: Object.keys(components),
      snapshotDays: 0,
      recentActivity: logs.slice(-10),
      recentErrors: recentErrors.slice(-5),
      errorCount: recentErrors.length,
      updatedAt: dataJson.updated_at,
    });
  } else {
    // Fallback: no data.json
    res.status(200).json({
      bot: { name: "@ComponentiPCconIA_bot", status: "unknown" },
      components: 0,
      sources: [],
      componentList: [],
      snapshotDays: 0,
      recentActivity: [],
      recentErrors: [],
      errorCount: 0,
      error: "data.json not found",
    });
  }
}
