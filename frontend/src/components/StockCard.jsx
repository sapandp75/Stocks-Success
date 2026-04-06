import { useNavigate } from 'react-router-dom'
import WarningBadge from './WarningBadge'
import { addToWatchlist } from '../api'

function fmt(val, type = 'pct') {
  if (val == null) return '—'
  if (type === 'pct') return `${(val * 100).toFixed(1)}%`
  if (type === 'pe') return val.toFixed(1)
  if (type === 'money') {
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
    return `$${val.toFixed(0)}`
  }
  return String(val)
}

export default function StockCard({ stock, bucket }) {
  const navigate = useNavigate()

  const handleWatch = async () => {
    try {
      await addToWatchlist({ ticker: stock.ticker, bucket: bucket || stock.bucket || 'B1' })
      alert(`${stock.ticker} added to watchlist`)
    } catch (e) {
      alert(`Error: ${e.message}`)
    }
  }

  return (
    <div
      className="bg-white rounded-lg border p-4 hover:shadow-sm transition-shadow"
      style={{ borderColor: '#e2e4e8' }}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base" style={{ color: '#1a1a2e' }}>{stock.ticker}</span>
            <span
              className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
              style={{ backgroundColor: (bucket || stock.bucket) === 'B1' ? '#3b82f6' : '#8b5cf6' }}
            >
              {bucket || stock.bucket}
            </span>
          </div>
          <div className="text-xs mt-0.5" style={{ color: '#6b7280' }}>
            {stock.name} · {stock.sector}
          </div>
        </div>
        <div className="text-right">
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${stock.price?.toFixed(2)}</div>
          <div className="text-xs" style={{ color: stock.drop_from_high > 0.3 ? '#e5484d' : '#6b7280' }}>
            {stock.drop_from_high != null ? `↓${(stock.drop_from_high * 100).toFixed(0)}% from high` : ''}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 text-xs mb-3">
        <div>
          <div style={{ color: '#6b7280' }}>Fwd P/E</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.forward_pe, 'pe')}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>Op Margin</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.operating_margin)}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>Rev Growth</div>
          <div className="font-medium" style={{ color: stock.revenue_growth > 0 ? '#00a562' : '#e5484d' }}>
            {fmt(stock.revenue_growth)}
          </div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>FCF</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.free_cash_flow, 'money')}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>D/E</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{stock.debt_to_equity?.toFixed(2) ?? '—'}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>Gross Margin</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.gross_margin)}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>Short %</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.short_percent)}</div>
        </div>
        <div>
          <div style={{ color: '#6b7280' }}>Mkt Cap</div>
          <div className="font-medium" style={{ color: '#1a1a2e' }}>{fmt(stock.market_cap, 'money')}</div>
        </div>
      </div>

      {stock.warnings && stock.warnings.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {stock.warnings.map(w => <WarningBadge key={w} warning={w} />)}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => navigate(`/deep-dive/${stock.ticker}`)}
          className="px-3 py-1 rounded text-xs font-medium text-white"
          style={{ backgroundColor: '#00a562' }}
        >
          Deep Dive
        </button>
        <button
          onClick={handleWatch}
          className="px-3 py-1 rounded text-xs font-medium border"
          style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
        >
          + Watch
        </button>
      </div>
    </div>
  )
}
