import { useState, useEffect } from 'react'
import { getPositions, getPnlSummary, closePosition } from '../api'

function CloseForm({ onSubmit, onCancel }) {
  const [price, setPrice] = useState('')
  const [reason, setReason] = useState('')
  const valid = price !== '' && !isNaN(parseFloat(price)) && parseFloat(price) > 0

  return (
    <div className="flex flex-col gap-1">
      <input
        type="number"
        step="0.01"
        min="0"
        placeholder="Exit price"
        className="border rounded px-2 py-1 text-xs w-24"
        style={{ borderColor: '#e2e4e8' }}
        value={price}
        onChange={e => setPrice(e.target.value)}
        autoFocus
      />
      <input
        placeholder="Reason"
        className="border rounded px-2 py-1 text-xs w-24"
        style={{ borderColor: '#e2e4e8' }}
        value={reason}
        onChange={e => setReason(e.target.value)}
      />
      <div className="flex gap-1">
        <button
          onClick={() => onSubmit(parseFloat(price), reason)}
          disabled={!valid}
          className="text-xs font-medium disabled:opacity-40"
          style={{ color: '#00a562' }}
        >
          Confirm
        </button>
        <button onClick={onCancel} className="text-xs" style={{ color: '#6b7280' }}>Cancel</button>
      </div>
    </div>
  )
}

export default function PositionsPage() {
  const [positions, setPositions] = useState([])
  const [summary, setSummary] = useState(null)
  const [tab, setTab] = useState('open')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [closing, setClosing] = useState(null) // id of position being closed

  const load = () => {
    Promise.all([
      getPositions().then(setPositions),
      getPnlSummary().then(setSummary),
    ])
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const filtered = positions.filter(p =>
    tab === 'open' ? p.status === 'OPEN' : p.status === 'CLOSED'
  )

  const handleClose = (id) => setClosing(id)

  const submitClose = async (id, exitPrice, exitReason) => {
    if (isNaN(exitPrice) || exitPrice <= 0) return
    try {
      await closePosition(id, { exit_price: exitPrice, exit_reason: exitReason || '' })
      setClosing(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Positions</h1>

      {error && (
        <div className="rounded-lg p-4 mb-4 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d', border: '1px solid #fca5a5' }}>
          {error}
        </div>
      )}

      {loading && <p className="text-sm mb-4" style={{ color: '#6b7280' }}>Loading positions...</p>}

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
                      closing === p.id ? (
                        <CloseForm
                          onSubmit={(price, reason) => submitClose(p.id, price, reason)}
                          onCancel={() => setClosing(null)}
                        />
                      ) : (
                        <button onClick={() => handleClose(p.id)} className="text-xs font-medium" style={{ color: '#e5484d' }}>
                          Close
                        </button>
                      )
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
