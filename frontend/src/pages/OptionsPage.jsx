import { useState } from 'react'
import { scanOptions } from '../api'
import RegimeBadge from '../components/RegimeBadge'
import WarningBadge from '../components/WarningBadge'

export default function OptionsPage() {
  const [tickers, setTickers] = useState('')
  const [results, setResults] = useState(null)
  const [regime, setRegime] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleScan = async () => {
    if (!tickers.trim()) return
    setLoading(true)
    try {
      const data = await scanOptions(tickers.trim())
      setResults(data.results)
      setRegime(data.regime?.regime)
    } catch (e) {
      alert(e.message)
    }
    setLoading(false)
  }

  const contracts = (results || []).filter(r => !r.error)
  const errors = (results || []).filter(r => r.error)

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Options Scanner</h1>

      {regime && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-sm" style={{ color: '#6b7280' }}>Regime:</span>
          <RegimeBadge verdict={regime.verdict} vix={regime.vix} />
          {regime.verdict === 'DEFENSIVE' || regime.verdict === 'CASH' ? (
            <span className="text-sm font-medium" style={{ color: '#e5484d' }}>
              No new positions allowed in {regime.verdict} regime.
            </span>
          ) : null}
        </div>
      )}

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 text-sm w-64"
          style={{ borderColor: '#e2e4e8' }}
          placeholder="Tickers (e.g. AAPL,MSFT,ADBE)"
          value={tickers}
          onChange={e => setTickers(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleScan()}
        />
        <button
          onClick={handleScan}
          disabled={loading}
          className="px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
          style={{ backgroundColor: '#00a562' }}
        >
          {loading ? 'Scanning...' : 'Scan Options'}
        </button>
      </div>

      {contracts.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                {['Ticker', 'Strike', 'Expiry', 'DTE', 'Delta', 'IV', 'Bid', 'Ask', 'OI', 'Spread', 'GBP Cost', '4x Target', 'Move Needed', 'Warnings'].map(h => (
                  <th key={h} className="text-left py-2 px-2 font-medium" style={{ color: '#6b7280' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contracts.map((c, i) => (
                <tr key={i} className="border-b hover:bg-[#f7f8fa]" style={{ borderColor: '#e2e4e8' }}>
                  <td className="py-2 px-2 font-medium" style={{ color: '#1a1a2e' }}>{c.ticker}</td>
                  <td className="py-2 px-2">${c.strike}</td>
                  <td className="py-2 px-2">{c.expiry}</td>
                  <td className="py-2 px-2">{c.dte}</td>
                  <td className="py-2 px-2">{c.delta}</td>
                  <td className="py-2 px-2">{c.iv ? (c.iv * 100).toFixed(0) + '%' : '—'}</td>
                  <td className="py-2 px-2">${c.bid}</td>
                  <td className="py-2 px-2">${c.ask}</td>
                  <td className="py-2 px-2">{c.open_interest}</td>
                  <td className="py-2 px-2">{(c.spread_pct * 100).toFixed(1)}%</td>
                  <td className="py-2 px-2 font-medium">£{c.premium_gbp}</td>
                  <td className="py-2 px-2">${c.target_4x}</td>
                  <td className="py-2 px-2">{(c.required_move_pct * 100).toFixed(1)}%</td>
                  <td className="py-2 px-2">
                    <div className="flex gap-1">{(c.warnings || []).map(w => <WarningBadge key={w} warning={w} />)}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {results && contracts.length === 0 && (
        <p className="text-sm" style={{ color: '#6b7280' }}>No qualifying contracts found. Filters: 60-120 DTE, 2-15% OTM, delta 0.25-0.40, OI &gt; 500, spread &lt; 10%, premium ≤ $7.</p>
      )}

      {errors.length > 0 && (
        <div className="mt-4 text-sm" style={{ color: '#e5484d' }}>
          {errors.map((e, i) => <div key={i}>{e.ticker}: {e.error}</div>)}
        </div>
      )}
    </div>
  )
}
