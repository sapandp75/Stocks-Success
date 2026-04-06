import { useState, useEffect } from 'react'
import { getPositions, getPnlSummary, closePosition } from '../api'

export default function PositionsPage() {
  const [positions, setPositions] = useState([])
  const [summary, setSummary] = useState(null)
  const [tab, setTab] = useState('open')

  const load = () => {
    getPositions().then(setPositions).catch(() => {})
    getPnlSummary().then(setSummary).catch(() => {})
  }
  useEffect(() => { load() }, [])

  const filtered = positions.filter(p =>
    tab === 'open' ? p.status === 'OPEN' : p.status === 'CLOSED'
  )

  const handleClose = async (id) => {
    const price = prompt('Exit price:')
    const reason = prompt('Exit reason:')
    if (price) {
      await closePosition(id, { exit_price: parseFloat(price), exit_reason: reason || '' })
      load()
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Positions</h1>

      {summary && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total P&L', value: `£${summary.total_pnl_gbp.toFixed(2)}`, color: summary.total_pnl_gbp >= 0 ? '#00a562' : '#e5484d' },
            { label: 'Total Trades', value: summary.total_trades, color: '#1a1a2e' },
            { label: 'Win Rate', value: `${(summary.win_rate * 100).toFixed(0)}%`, color: '#1a1a2e' },
            { label: 'W / L', value: `${summary.wins} / ${summary.losses}`, color: '#1a1a2e' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
              <div className="text-xs" style={{ color: '#6b7280' }}>{s.label}</div>
              <div className="text-xl font-bold" style={{ color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-1 mb-4 border-b" style={{ borderColor: '#e2e4e8' }}>
        {['open', 'closed'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 ${
              tab === t ? 'border-[#00a562] text-[#00a562]' : 'border-transparent text-[#6b7280]'
            }`}
          >
            {t} ({positions.filter(p => p.status === (t === 'open' ? 'OPEN' : 'CLOSED')).length})
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm" style={{ color: '#6b7280' }}>No {tab} positions.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                {['Ticker', 'Type', 'Bucket', 'Entry', 'Details', 'Thesis', tab === 'open' ? 'Actions' : 'Exit'].map(h => (
                  <th key={h} className="text-left py-2 px-2 font-medium" style={{ color: '#6b7280' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} className="border-b hover:bg-[#f7f8fa]" style={{ borderColor: '#e2e4e8' }}>
                  <td className="py-2 px-2 font-bold" style={{ color: '#1a1a2e' }}>{p.ticker}</td>
                  <td className="py-2 px-2 capitalize">{p.position_type}</td>
                  <td className="py-2 px-2">{p.bucket}</td>
                  <td className="py-2 px-2" style={{ color: '#6b7280' }}>{p.entry_date}</td>
                  <td className="py-2 px-2 text-xs" style={{ color: '#6b7280' }}>
                    {p.position_type === 'option'
                      ? `$${p.strike} ${p.expiry} · ${p.contracts}x · $${p.premium_paid}`
                      : `${p.shares} shares @ $${p.avg_price}`}
                  </td>
                  <td className="py-2 px-2 max-w-[150px] truncate" style={{ color: '#6b7280' }}>{p.thesis || '—'}</td>
                  <td className="py-2 px-2">
                    {tab === 'open' ? (
                      <button onClick={() => handleClose(p.id)} className="text-xs font-medium" style={{ color: '#e5484d' }}>
                        Close
                      </button>
                    ) : (
                      <span className="text-xs" style={{ color: '#6b7280' }}>
                        ${p.exit_price} · {p.exit_reason}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
