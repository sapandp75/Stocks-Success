function Sparkline({ values, color, width = 100, height = 32 }) {
  if (!values || values.length < 2) return null
  const pad = 2
  const nums = values.filter(v => v != null && typeof v === 'number' && isFinite(v))
  if (nums.length < 2) return null

  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const range = max - min || 1

  const points = nums.map((v, i) => {
    const x = pad + (i / (nums.length - 1)) * (width - pad * 2)
    const y = height - pad - ((v - min) / range) * (height - pad * 2)
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function fmtVal(val, key) {
  if (val == null || typeof val !== 'number' || !isFinite(val)) return '--'
  if (key === 'eps') return `$${val.toFixed(2)}`
  if (key === 'roic' || key === 'roe') return `${(val * 100).toFixed(1)}%`
  if (key === 'fcf') {
    if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(1)}T`
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
    return `$${val.toFixed(0)}`
  }
  return String(val)
}

function fmtPct(val) {
  if (val == null || typeof val !== 'number' || !isFinite(val)) return null
  return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(1)}%`
}

function color(first, last) {
  if (first == null || last == null) return '#6b7280'
  return last >= first ? '#00a562' : '#e5484d'
}

// Extract raw values from [{year, value}] or [{quarter, value}] arrays
function extractValues(arr) {
  if (!arr || !Array.isArray(arr)) return []
  return arr.map(item => item?.value ?? item).filter(v => v != null && typeof v === 'number' && isFinite(v))
}

function extractLabels(arr, type) {
  if (!arr || !Array.isArray(arr)) return []
  if (type === 'annual') return arr.map(item => item?.year ? `FY${String(item.year).slice(2)}` : '')
  return arr.map(item => item?.quarter || '')
}

function ChartTile({ label, annualData, quarterlyData, metricKey }) {
  const aVals = extractValues(annualData)
  const aLabels = extractLabels(annualData, 'annual')
  const qVals = extractValues(quarterlyData)
  const qLabels = extractLabels(quarterlyData, 'quarterly')
  const hasA = aVals.length >= 2
  const hasQ = qVals.length >= 2

  const latestQ = Array.isArray(quarterlyData) && quarterlyData.length > 0 ? quarterlyData[0] : {}

  if (!hasA && !hasQ) return null

  const aCol = hasA ? color(aVals[0], aVals[aVals.length - 1]) : '#6b7280'
  const qCol = hasQ ? color(qVals[qVals.length - 1], qVals[0]) : '#6b7280' // quarterly is newest-first

  return (
    <div className="p-3 rounded-lg border" style={{ borderColor: '#e2e4e8', backgroundColor: '#ffffff' }}>
      <div className="font-semibold text-xs mb-2" style={{ color: '#1a1a2e' }}>{label}</div>

      {hasA && (
        <div className="mb-2">
          <div className="text-[9px] font-medium mb-1" style={{ color: '#6b7280' }}>
            ANNUAL — {aLabels[0]} → {aLabels[aLabels.length - 1]}
          </div>
          <div className="flex items-center gap-3">
            <Sparkline values={aVals} color={aCol} />
            <div className="text-sm font-bold" style={{ color: aCol }}>
              {fmtVal(aVals[aVals.length - 1], metricKey)}
            </div>
          </div>
        </div>
      )}

      {hasQ && (
        <div>
          <div className="text-[9px] font-medium mb-1" style={{ color: '#6b7280' }}>
            QUARTERLY — {qLabels[qLabels.length - 1]} → {qLabels[0]}
          </div>
          <div className="flex items-center gap-3">
            <Sparkline values={[...qVals].reverse()} color={qCol} />
            <div>
              <div className="text-sm font-bold" style={{ color: qCol }}>
                {fmtVal(qVals[0], metricKey)}
              </div>
              <div className="flex gap-2">
                {latestQ.yoy != null && (
                  <span className="text-[9px] font-medium" style={{ color: latestQ.yoy >= 0 ? '#00a562' : '#e5484d' }}>
                    {fmtPct(latestQ.yoy)} YoY
                  </span>
                )}
                {latestQ.qoq != null && (
                  <span className="text-[9px] font-medium" style={{ color: latestQ.qoq >= 0 ? '#00a562' : '#e5484d' }}>
                    {fmtPct(latestQ.qoq)} QoQ
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function SparklineGrid({ data, quarterly, growthMetrics, fundamentals }) {
  if (!data && !quarterly && !growthMetrics) return null

  // EPS: quarterly from quarterly.eps, annual derived from net_income / shares_outstanding
  const epsQuarterly = quarterly?.eps?.filter(q => q.value != null) || []
  const annualEps = (data?.net_income && data?.shares_outstanding)
    ? data.net_income.map((ni, i) => {
        const so = data.shares_outstanding[i]
        const niVal = ni?.value ?? ni
        const soVal = so?.value ?? so
        if (niVal != null && soVal != null && soVal > 0) {
          return { year: ni?.year, value: niVal / soVal }
        }
        return { year: ni?.year, value: null }
      })
    : []

  // Revenue: annual from data.revenue, quarterly from quarterly.revenue
  const revAnnual = data?.revenue || []
  const revQuarterly = quarterly?.revenue?.filter(q => q.value != null) || []

  // ROIC: annual from growth_metrics.roic_trend
  const roicAnnual = (growthMetrics?.roic_trend || []).map(r => ({ year: r.year, value: r.roic }))

  // FCF: annual from data.free_cash_flow, quarterly from quarterly.fcf
  const fcfAnnual = data?.free_cash_flow || []
  const fcfQuarterly = quarterly?.fcf?.filter(q => q.value != null) || []

  // ROE: current only
  const roe = fundamentals?.return_on_equity

  // P/E: current only (no historical available)
  const fwdPe = fundamentals?.forward_pe
  const trailPe = fundamentals?.trailing_pe

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
      <ChartTile label="Revenue" metricKey="fcf" annualData={revAnnual} quarterlyData={revQuarterly} />
      <ChartTile label="EPS" metricKey="eps" annualData={annualEps} quarterlyData={epsQuarterly} />
      <ChartTile label="Free Cash Flow" metricKey="fcf" annualData={fcfAnnual} quarterlyData={fcfQuarterly} />
      <ChartTile label="ROIC" metricKey="roic" annualData={roicAnnual} quarterlyData={[]} />
      <div className="p-3 rounded-lg border" style={{ borderColor: '#e2e4e8', backgroundColor: '#ffffff' }}>
        <div className="font-semibold text-xs mb-2" style={{ color: '#1a1a2e' }}>ROE</div>
        <div className="text-2xl font-bold" style={{ color: roe != null && roe > 0.15 ? '#00a562' : roe > 0.08 ? '#d97b0e' : '#e5484d' }}>
          {roe != null ? `${(roe * 100).toFixed(1)}%` : '--'}
        </div>
        <div className="text-[9px] mt-1" style={{ color: '#6b7280' }}>Current snapshot</div>
      </div>
      <div className="p-3 rounded-lg border" style={{ borderColor: '#e2e4e8', backgroundColor: '#ffffff' }}>
        <div className="font-semibold text-xs mb-2" style={{ color: '#1a1a2e' }}>P/E</div>
        <div className="flex gap-4">
          <div>
            <div className="text-[9px]" style={{ color: '#6b7280' }}>Forward</div>
            <div className="text-lg font-bold" style={{ color: fwdPe != null && fwdPe < 15 ? '#00a562' : fwdPe < 25 ? '#d97b0e' : '#e5484d' }}>
              {fwdPe != null ? fwdPe.toFixed(1) : '--'}
            </div>
          </div>
          <div>
            <div className="text-[9px]" style={{ color: '#6b7280' }}>Trailing</div>
            <div className="text-lg font-bold" style={{ color: '#1a1a2e' }}>
              {trailPe != null ? trailPe.toFixed(1) : '--'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
