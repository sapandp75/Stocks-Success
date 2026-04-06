export default function InsiderPanel({ data }) {
  if (!data) return null

  const sentiment = data.net_sentiment || data.sentiment || 'QUIET'
  const sentimentColors = {
    BUYING: '#00a562',
    SELLING: '#00a562',
    MIXED: '#d97b0e',
    QUIET: '#6b7280',
  }
  const bg = sentimentColors[sentiment] || '#6b7280'

  const transactions = (data.notable_transactions || data.transactions || []).slice(0, 5)

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
      {transactions.length > 0 ? (
        <div className="space-y-1">
          {transactions.map((t, i) => (
            <div key={i} className="flex justify-between text-xs" style={{ color: '#1a1a2e' }}>
              <span className="truncate mr-2" style={{ maxWidth: '40%' }}>{t.name || t.insider_name || 'Unknown'}</span>
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
