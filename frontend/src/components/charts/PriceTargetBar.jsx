export default function PriceTargetBar({ sources, currentPrice }) {
  if (!sources || sources.length === 0) return null

  const allVals = sources.flatMap(s => [s.low, s.high].filter(v => v != null))
  if (currentPrice != null) allVals.push(currentPrice)
  if (allVals.length === 0) return null

  const min = Math.min(...allVals) * 0.9
  const max = Math.max(...allVals) * 1.1
  const range = max - min
  const pos = (v) => range > 0 ? ((v - min) / range) * 100 : 50

  return (
    <div className="space-y-2 mt-3">
      <div className="text-xs font-medium" style={{ color: '#1a1a2e' }}>Price Targets by Source</div>
      {sources.map((s, i) => (
        <div key={i} className="relative" style={{ height: '20px' }}>
          {/* Label */}
          <div className="absolute text-[10px] font-medium" style={{ color: '#6b7280', top: '2px', left: 0, width: '70px' }}>
            {s.name}
          </div>
          {/* Bar area */}
          <div className="absolute" style={{ left: '75px', right: 0, top: 0, bottom: 0 }}>
            <div className="absolute top-1.5 left-0 right-0 h-1 rounded" style={{ backgroundColor: '#e5e7eb' }} />
            {/* Range bar */}
            {s.low != null && s.high != null && (
              <div className="absolute top-1 h-2 rounded" style={{
                left: `${pos(s.low)}%`, width: `${pos(s.high) - pos(s.low)}%`,
                backgroundColor: '#93c5fd',
              }} />
            )}
            {/* Mean marker */}
            {s.mean != null && (
              <div className="absolute top-0" style={{ left: `${pos(s.mean)}%`, transform: 'translateX(-50%)' }}>
                <div style={{ width: '2px', height: '14px', backgroundColor: '#3b82f6' }} />
              </div>
            )}
          </div>
        </div>
      ))}
      {/* Current price reference */}
      {currentPrice != null && (
        <div className="relative" style={{ height: '12px' }}>
          <div className="absolute" style={{ left: '75px', right: 0 }}>
            <div className="absolute" style={{ left: `${pos(currentPrice)}%`, transform: 'translateX(-50%)' }}>
              <div className="text-[9px] font-bold" style={{ color: '#1a1a2e' }}>Current: ${currentPrice.toFixed(0)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
