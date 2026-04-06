function Sparkline({ values, color }) {
  if (!values || values.length < 2) return null

  const w = 60
  const h = 24
  const pad = 2
  const nums = values.filter(v => v != null)
  if (nums.length < 2) return null

  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const range = max - min || 1

  const points = nums.map((v, i) => {
    const x = pad + (i / (nums.length - 1)) * (w - pad * 2)
    const y = h - pad - ((v - min) / range) * (h - pad * 2)
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function fmtMetricValue(val, key) {
  if (val == null) return '--'
  if (key.includes('margin')) return `${(val * 100).toFixed(1)}%`
  if (key === 'revenue' || key === 'free_cash_flow') {
    if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(1)}T`
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
    return `$${val.toFixed(0)}`
  }
  if (key === 'debt_to_equity') return val.toFixed(2)
  return String(val)
}

function trendColor(values, key) {
  if (!values || values.length < 2) return '#6b7280'
  const first = values.find(v => v != null)
  const last = [...values].reverse().find(v => v != null)
  if (first == null || last == null) return '#6b7280'
  const up = last > first
  // For debt_to_equity, up is bad
  if (key === 'debt_to_equity') return up ? '#e5484d' : '#00a562'
  return up ? '#00a562' : '#e5484d'
}

const metricLabels = {
  revenue: 'Revenue',
  operating_margin: 'Op Margin',
  net_margin: 'Net Margin',
  free_cash_flow: 'FCF',
  debt_to_equity: 'D/E',
}

export default function SparklineGrid({ data }) {
  if (!data) return null

  const metrics = Object.keys(metricLabels).filter(k => data[k] && data[k].length > 0)
  if (metrics.length === 0) return null

  return (
    <div className="mt-4">
      <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Financial History (4yr)</div>
      <div className="grid grid-cols-3 md:grid-cols-5 gap-3">
        {metrics.map(key => {
          const values = data[key]
          const latest = [...values].reverse().find(v => v != null)
          const color = trendColor(values, key)
          return (
            <div key={key} className="p-2 rounded" style={{ backgroundColor: '#f7f8fa' }}>
              <div className="text-[10px] mb-1" style={{ color: '#6b7280' }}>{metricLabels[key]}</div>
              <Sparkline values={values} color={color} />
              <div className="text-xs font-semibold mt-1" style={{ color }}>
                {fmtMetricValue(latest, key)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
