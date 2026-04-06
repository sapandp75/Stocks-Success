export default function BreadthGauge({ data }) {
  if (!data) return null

  const pct = data.pct_above_200d ?? 0
  const pct50 = data.pct_above_50d ?? 0
  const signal = data.breadth_signal || 'UNKNOWN'
  const sampleSize = data.sample_size || 0

  // Color based on percentage
  const fillColor = pct > 70 ? '#00a562' : pct >= 50 ? '#d97b0e' : '#e5484d'

  // Signal colors
  const signalColors = {
    STRONG: { bg: '#dcfce7', text: '#00a562' },
    HEALTHY: { bg: '#dcfce7', text: '#00a562' },
    WEAKENING: { bg: '#fef9c3', text: '#d97b0e' },
    POOR: { bg: '#fef2f2', text: '#e5484d' },
  }
  const sc = signalColors[signal] || { bg: '#f0f1f3', text: '#6b7280' }

  // SVG gauge parameters
  const width = 200
  const height = 110
  const cx = 100
  const cy = 100
  const r = 80
  // Semi-circle arc length = pi * r
  const arcLength = Math.PI * r
  const filled = (pct / 100) * arcLength

  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex flex-col items-center">
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* Background arc */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke="#e2e4e8"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Filled arc */}
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none"
            stroke={fillColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${arcLength}`}
          />
          {/* Percentage text */}
          <text x={cx} y={cy - 10} textAnchor="middle" style={{ fill: '#1a1a2e', fontSize: '24px', fontWeight: 'bold' }}>
            {pct.toFixed(0)}%
          </text>
        </svg>

        <span
          className="text-xs font-medium px-2 py-0.5 rounded mt-1"
          style={{ backgroundColor: sc.bg, color: sc.text }}
        >
          {signal}
        </span>

        <div className="text-sm mt-2" style={{ color: '#1a1a2e' }}>
          {pct.toFixed(1)}% of S&P above 200d SMA
        </div>

        <div className="text-xs mt-1" style={{ color: '#6b7280' }}>
          50d SMA: {pct50.toFixed(1)}% above
        </div>

        <div className="text-xs mt-1" style={{ color: '#6b7280' }}>
          (based on {sampleSize} stocks)
        </div>
      </div>
    </div>
  )
}
