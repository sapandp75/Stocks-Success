export default function AnalystBar({ data, currentPrice }) {
  if (!data) return null

  const low = data.target_low
  const high = data.target_high
  const mean = data.target_mean
  const consensus = data.consensus
  const signal = data.contrarian_signal
  const numAnalysts = data.num_analysts

  if (low == null || high == null) return null

  const range = high - low
  const meanPos = range > 0 ? ((mean - low) / range) * 100 : 50
  const pricePos = range > 0 && currentPrice != null ? Math.max(0, Math.min(100, ((currentPrice - low) / range) * 100)) : null

  return (
    <div className="mt-4">
      <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Analyst Price Targets</div>
      <div className="flex items-center gap-2 mb-2 text-xs" style={{ color: '#6b7280' }}>
        {consensus && <span>Consensus: <strong style={{ color: '#1a1a2e' }}>{consensus}</strong></span>}
        {signal && <span style={{ color: '#d97b0e' }}>{signal}</span>}
        {numAnalysts != null && <span>({numAnalysts} analysts)</span>}
      </div>

      <div className="relative" style={{ height: '40px' }}>
        {/* Bar */}
        <div
          className="absolute rounded"
          style={{
            top: '14px',
            left: 0,
            right: 0,
            height: '12px',
            backgroundColor: '#e2e4e8',
          }}
        />

        {/* Low label */}
        <div className="absolute text-[10px]" style={{ left: 0, top: 0, color: '#6b7280' }}>
          ${low.toFixed(0)}
        </div>

        {/* High label */}
        <div className="absolute text-[10px]" style={{ right: 0, top: 0, color: '#6b7280' }}>
          ${high.toFixed(0)}
        </div>

        {/* Mean marker */}
        {mean != null && (
          <div
            className="absolute"
            style={{ left: `${meanPos}%`, top: '12px', transform: 'translateX(-50%)' }}
          >
            <div style={{ width: '2px', height: '16px', backgroundColor: '#3b82f6' }} />
            <div className="text-[9px] font-bold" style={{ color: '#3b82f6', transform: 'translateX(-40%)' }}>
              ${mean.toFixed(0)}
            </div>
          </div>
        )}

        {/* Current price marker */}
        {pricePos != null && (
          <div
            className="absolute"
            style={{ left: `${pricePos}%`, top: '10px', transform: 'translateX(-50%)' }}
          >
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: currentPrice < mean ? '#00a562' : '#e5484d',
              border: '2px solid white',
              boxShadow: '0 0 2px rgba(0,0,0,0.3)',
              position: 'relative',
              top: '6px',
            }} />
          </div>
        )}
      </div>
    </div>
  )
}
