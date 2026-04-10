export default function InsiderPanel({ data }) {
  if (!data) return null

  const sentiment = data.net_sentiment || data.sentiment || 'QUIET'
  const sentimentColors = {
    BUYING: '#00a562',
    SELLING: '#e5484d',
    MIXED: '#d97b0e',
    QUIET: '#6b7280',
  }
  const bg = sentimentColors[sentiment] || '#6b7280'

  const buys = data.recent_buys
  const sells = data.recent_sells
  const transactions = (data.notable_transactions || data.transactions || data.notable || []).slice(0, 8)

  function fmtValue(val) {
    if (val == null) return '--'
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(1)}M`
    if (Math.abs(val) >= 1e3) return `$${(val / 1e3).toFixed(0)}K`
    return `$${val.toFixed(0)}`
  }

  return (
    <div className="mt-4 p-3 rounded border" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center gap-2 mb-3">
        <span className="font-semibold text-sm" style={{ color: '#1a1a2e' }}>Insider Activity</span>
        <span
          className="px-2 py-0.5 rounded text-[10px] font-bold text-white"
          style={{ backgroundColor: bg }}
        >
          {sentiment}{sentiment === 'SELLING' ? ' (contrarian)' : ''}
        </span>
      </div>

      {/* Buy/sell counts */}
      {(buys != null || sells != null) && (
        <div className="flex gap-4 mb-3 text-xs">
          {buys != null && (
            <div>
              <span style={{ color: '#6b7280' }}>Recent buys: </span>
              <span className="font-semibold" style={{ color: '#00a562' }}>{buys.toLocaleString()}</span>
            </div>
          )}
          {sells != null && (
            <div>
              <span style={{ color: '#6b7280' }}>Recent sells: </span>
              <span className="font-semibold" style={{ color: '#e5484d' }}>{sells.toLocaleString()}</span>
            </div>
          )}
          {buys != null && sells != null && (
            <div>
              <span style={{ color: '#6b7280' }}>Net: </span>
              <span className="font-semibold" style={{ color: buys > sells ? '#00a562' : '#e5484d' }}>
                {buys > sells ? '+' : ''}{(buys - sells).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      )}

      {transactions.length > 0 ? (
        <div className="space-y-1">
          {transactions.map((t, i) => (
            <div key={i} className="flex justify-between text-xs" style={{ color: '#1a1a2e' }}>
              <span className="mr-2">{t.name || t.insider_name || 'Unknown'}</span>
              <span style={{ color: '#6b7280' }}>
                {t.shares ? `${t.shares.toLocaleString()} shares` : ''} {t.value ? fmtValue(t.value) : ''} {t.date || ''}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs" style={{ color: '#6b7280' }}>No recent notable transactions.</p>
      )}
    </div>
  )
}
