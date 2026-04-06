import { REGIME_COLORS } from '../theme'

export default function RegimeBadge({ verdict, vix }) {
  const color = REGIME_COLORS[verdict] || '#6b7280'
  return (
    <div className="flex items-center gap-2">
      <span
        className="px-2 py-0.5 rounded text-xs font-bold text-white"
        style={{ backgroundColor: color }}
      >
        {verdict}
      </span>
      {vix != null && (
        <span className="text-xs" style={{ color: '#6b7280' }}>
          VIX {vix}
        </span>
      )}
    </div>
  )
}
