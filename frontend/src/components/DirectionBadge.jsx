export default function DirectionBadge({ direction }) {
  if (!direction) return null

  const colorMap = {
    FULL_UPTREND: '#00a562',
    PULLBACK_IN_UPTREND: '#d97b0e',
    CORRECTION_IN_UPTREND: '#d97b0e',
    TREND_WEAKENING: '#f87171',
    POTENTIAL_TREND_CHANGE: '#f87171',
    FULL_DOWNTREND: '#e5484d',
    MIXED: '#6b7280',
  }

  const bg = colorMap[direction] || '#6b7280'
  const label = direction.replace(/_/g, ' ')

  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
      style={{ backgroundColor: bg }}
    >
      {label}
    </span>
  )
}
