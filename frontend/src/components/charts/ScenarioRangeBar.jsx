export default function ScenarioRangeBar({ worst, base, best, currentPrice, weightedTarget }) {
  if (worst == null || best == null) return null

  const range = best - worst
  if (range <= 0) return null

  const pos = (val) => Math.max(0, Math.min(100, ((val - worst) / range) * 100))

  return (
    <div className="mb-4">
      <div className="flex justify-between text-[10px] mb-1" style={{ color: '#6b7280' }}>
        <span>Worst: ${worst.toFixed(0)}</span>
        {base != null && <span>Base: ${base.toFixed(0)}</span>}
        <span>Best: ${best.toFixed(0)}</span>
      </div>
      <div className="relative h-6 rounded" style={{
        background: 'linear-gradient(to right, #e5484d, #d97b0e, #00a562)',
      }}>
        {/* Current price line */}
        {currentPrice != null && (
          <div className="absolute top-0 bottom-0" style={{ left: `${pos(currentPrice)}%` }}>
            <div style={{ width: '2px', height: '100%', backgroundColor: '#1a1a2e' }} />
            <div className="text-[9px] font-bold whitespace-nowrap" style={{ color: '#1a1a2e', transform: 'translateX(-50%)', marginTop: '2px' }}>
              ${currentPrice.toFixed(0)}
            </div>
          </div>
        )}
        {/* Weighted target diamond */}
        {weightedTarget != null && (
          <div className="absolute" style={{ left: `${pos(weightedTarget)}%`, top: '50%', transform: 'translate(-50%, -50%)' }}>
            <div style={{
              width: '10px', height: '10px', backgroundColor: '#3b82f6',
              transform: 'rotate(45deg)', border: '1px solid white',
            }} />
          </div>
        )}
      </div>
    </div>
  )
}
