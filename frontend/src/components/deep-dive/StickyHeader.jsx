import AiAnalyzeButton from '../AiAnalyzeButton'

export default function StickyHeader({ ticker, fundamentals, ai, onReload, onExport, exporting }) {
  const f = fundamentals || {}
  const price = f.price
  const changePct = f.price_change_pct
  const verdict = ai?.verdict
  const conviction = ai?.conviction

  const convictionColors = { HIGH: '#00a562', MODERATE: '#d97b0e', LOW: '#6b7280' }
  const verdictColors = { BUY: '#00a562', HOLD: '#d97b0e', AVOID: '#e5484d' }

  return (
    <div className="sticky top-0 z-50 bg-white border-b px-5 py-2" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center justify-between flex-wrap gap-2 max-w-5xl mx-auto">
        <div className="flex items-center gap-4">
          {/* Ticker + Company */}
          <div>
            <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{ticker}</span>
            {f.name && <span className="text-sm ml-2" style={{ color: '#6b7280' }}>{f.name}</span>}
          </div>

          {/* Price */}
          {price != null && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg" style={{ color: '#1a1a2e' }}>${price.toFixed(2)}</span>
              {changePct != null && (
                <span className="text-sm font-medium" style={{ color: changePct >= 0 ? '#00a562' : '#e5484d' }}>
                  {changePct >= 0 ? '+' : ''}{(changePct * 100).toFixed(1)}%
                </span>
              )}
            </div>
          )}

          {/* Conviction state — only if AI exists */}
          {verdict && (
            <div className="flex items-center gap-1.5">
              <span className="px-2 py-0.5 rounded text-xs font-bold text-white" style={{ backgroundColor: verdictColors[verdict] || '#6b7280' }}>
                {verdict}
              </span>
              {conviction && (
                <span className="text-[10px] font-bold" style={{ color: convictionColors[conviction] || '#6b7280' }}>
                  {conviction}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onExport}
            disabled={!ticker || exporting}
            className="px-3 py-1.5 rounded text-xs font-medium border"
            style={{ borderColor: '#d1d5db', color: '#374151', backgroundColor: exporting ? '#f3f4f6' : '#ffffff' }}
          >
            {exporting ? 'Exporting...' : 'Export All'}
          </button>
          <AiAnalyzeButton ticker={ticker} onComplete={onReload} />
        </div>
      </div>
    </div>
  )
}
