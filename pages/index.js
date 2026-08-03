import Head from 'next/head'
import { useEffect, useState } from 'react'
import styles from '../styles/Home.module.css'

function StatusBadge({ status }) {
  const colors = { ok: '#10b981', warn: '#f59e0b', error: '#ef4444', info: '#3b82f6', start: '#8b5cf6', end: '#6b7280' }
  const c = colors[status] || '#6b7280'
  return <span style={{
    display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px',
    borderRadius: '12px', fontSize: '0.75rem', fontWeight: 600,
    backgroundColor: c + '20', color: c, border: `1px solid ${c}40`
  }}><span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: c }} />{status}</span>
}

function PriceChart({ data, component }) {
  if (!data || data.length === 0) return <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Nessun dato</p>

  const points = data.slice(0, 20).reverse()
  const prices = points.map(p => p.price)
  const dates = points.map(p => p.date)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const range = maxPrice - minPrice || 1

  const width = 420, height = 180, margin = 30
  const cw = width - 2 * margin, ch = height - 2 * margin

  const pts = points.map((p, i) => {
    const x = margin + (i / (points.length - 1)) * cw
    const y = height - margin - ((p.price - minPrice) / range) * ch
    return `${x},${y}`
  }).join(' L ')

  return (
    <div style={{ fontFamily: 'monospace', background: '#1e293b', color: '#eee', padding: '12px', borderRadius: '8px', margin: '8px 0' }}>
      <div style={{ fontSize: '0.8rem', marginBottom: '8px' }}>📊 {component}</div>
      <svg width={width} height={height}>
        <polyline points={pts} fill="none" stroke="#38bdf8" strokeWidth="2" />
        {points.map((p, i) => {
          const x = margin + (i / (points.length - 1)) * cw
          const y = height - margin - ((p.price - minPrice) / range) * ch
          return <circle key={i} cx={x} cy={y} r="3" fill="#f59e0b" />
        })}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#888' }}>
        <span>{dates[0]}</span>
        <span>Min: €{minPrice.toFixed(2)} / Max: €{maxPrice.toFixed(2)}</span>
        <span>{dates[dates.length - 1]}</span>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [botStatus, setBotStatus] = useState(null)
  const [history, setHistory] = useState(null)
  const [selectedComponent, setSelectedComponent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [priceHistory, setPriceHistory] = useState(null)

  useEffect(() => {
    fetchBotStatus()
    fetchHistory()
    const interval = setInterval(() => {
      fetchBotStatus()
    }, 120000)
    return () => clearInterval(interval)
  }, [])

  const fetchBotStatus = async () => {
    try {
      const r = await fetch('/api/dashboard/bot-status')
      const data = await r.json()
      setBotStatus(data)
    } catch (e) { console.error(e) }
  }

  const fetchHistory = async () => {
    try {
      const r = await fetch('/api/dashboard/snapshots')
      const data = await r.json()
      setHistory(data)
      if (data.components && data.components.length > 0) {
        setSelectedComponent(data.components[0])
      }
      setLoading(false)
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    if (selectedComponent) fetchPriceHistory(selectedComponent)
  }, [selectedComponent])

  const fetchPriceHistory = async (comp) => {
    try {
      const r = await fetch(`/api/dashboard/prices-history?component=${encodeURIComponent(comp)}`)
      const data = await r.json()
      setPriceHistory(data)
    } catch (e) { console.error(e) }
  }

  if (loading) return (
    <div className={styles.container}>
      <Head><title>🤖 Agent Dashboard — Loading…</title></Head>
      <main className={styles.main} style={{ textAlign: 'center', padding: '80px' }}>
        <h2>🔄 Caricamento agente…</h2>
      </main>
    </div>
  )

  const lastRun = botStatus?.bot?.lastRun
  const errorCount = botStatus?.errorCount || 0

  return (
    <div className={styles.container}>
      <Head>
        <title>🤖 Agent Dashboard — PC Components Bot</title>
        <meta name="description" content="Dashboard agente autonomo — @ComponentiPCconIA_bot" />
      </Head>

      <main className={styles.main} style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <header style={{ marginBottom: '32px', textAlign: 'center' }}>
          <h1 className={styles.title}>🤖 Agent Dashboard</h1>
          <p className={styles.subtitle}>
            {botStatus?.bot?.name || '@ComponentiPCconIA_bot'} — Ultimo run: {lastRun ? new Date(lastRun).toLocaleString('it-IT') : ' mai'}
          </p>
        </header>

        {/* Health cards */}
        <section className={styles.card} style={{ marginBottom: '24px' }}>
          <h2 style={{ marginTop: 0, borderBottom: '2px solid #334159', paddingBottom: '12px' }}>📊 Stato Sistema (24h)</h2>
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px'
          }}>
            <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#38bdf8' }}>{botStatus?.components || 0}</div>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Componenti monitorati</div>
            </div>
            <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981' }}>{botStatus?.sources?.length || 0}</div>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Fonti prezzo</div>
            </div>
            <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: '#f59e0b' }}>{botStatus?.snapshotDays || 0}</div>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Giorni snapshot</div>
            </div>
            <div style={{ textAlign: 'center', padding: '16px', backgroundColor: '#1e293b', borderRadius: '8px' }}>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: errorCount > 0 ? '#ef4444' : '#10b981' }}>{errorCount}</div>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Errori recenti</div>
            </div>
          </div>
        </section>

        {/* Sources list */}
        <section className={styles.card} style={{ marginBottom: '24px' }}>
          <h2 style={{ marginTop: 0, borderBottom: '2px solid #334159', paddingBottom: '12px' }}>🌍 Fonti Prezzo Attive</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {botStatus?.sources?.map(src => (
              <span key={src} style={{
                padding: '4px 12px', backgroundColor: '#334159', borderRadius: '16px',
                fontSize: '0.875rem'
              }}>{src}</span>
            )) || []}
          </div>
        </section>

        {/* Price history by component */}
        <section className={styles.card} style={{ marginBottom: '24px' }}>
          <h2 style={{ marginTop: 0, borderBottom: '2px solid #334159', paddingBottom: '12px' }}>📈 Storico Prezzi per Componente</h2>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ marginRight: '8px' }}>Seleziona componente: </label>
            <select
              value={selectedComponent || ''}
              onChange={(e) => setSelectedComponent(e.target.value)}
              style={{
                padding: '6px 12px', borderRadius: '6px', border: '1px solid #475569',
                backgroundColor: '#1e293b', color: '#e2e8f0'
              }}
            >
              {history?.components?.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          {priceHistory ? (
            <>
              <h3 style={{ color: '#94a3b8' }}>{priceHistory.component}</h3>
              <PriceChart data={priceHistory.data} component={priceHistory.component} />

              <div style={{ marginTop: '16px', overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #334159' }}>
                      <th style={{ textAlign: 'left', padding: '8px' }}>Data</th>
                      <th style={{ textAlign: 'left', padding: '8px' }}>Fonte</th>
                      <th style={{ textAlign: 'right', padding: '8px' }}>Prezzo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {priceHistory.data.slice(0, 20).map((p, i) => (
                      <tr key={i}>
                        <td style={{ padding: '6px' }}>{p.date}</td>
                        <td style={{ padding: '6px', color: '#94a3b8' }}>{p.source}</td>
                        <td style={{ padding: '6px', textAlign: 'right' }}>€{p.price.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p style={{ color: '#6b7280' }}>Caricamento storico…</p>
          )}
        </section>

        {/* Snapshots table */}
        {history?.snapshots && history.snapshots.length > 0 && (
          <section className={styles.card} style={{ marginBottom: '24px' }}>
            <h2 style={{ marginTop: 0, borderBottom: '2px solid #334159', paddingBottom: '12px' }}>📸 Snapshot Telegram (storico notifiche)</h2>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334159' }}>
                    <th style={{ textAlign: 'left', padding: '6px' }}>Timestamp</th>
                    <th style={{ textAlign: 'left', padding: '6px' }}>Componente</th>
                    <th style={{ textAlign: 'right', padding: '6px' }}>Prezzo migliore</th>
                    <th style={{ textAlign: 'left', padding: '6px' }}>Fonte</th>
                  </tr>
                </thead>
                <tbody>
                  {history.snapshots.slice(0, 30).map((s, i) => (
                    <tr key={i}>
                      <td style={{ padding: '6px', color: '#94a3b8' }}>{s.ts || '--'}</td>
                      <td style={{ padding: '6px' }}>{s.component || '--'}</td>
                      <td style={{ padding: '6px', textAlign: 'right' }}>€{s.best_price?.toFixed(2) || '--'}</td>
                      <td style={{ padding: '6px', color: '#94a3b8' }}>{s.best_source || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <footer className={styles.footer}>
          <p>🤖 @ComponentiPCconIA_bot — Dashboard agente autonomo | Aggiornamento ogni 2 minuti</p>
          <p>📊 Dati da prices.db + history.db | Log: logs/agent_log.jsonl</p>
        </footer>
      </main>
    </div>
  )
}
