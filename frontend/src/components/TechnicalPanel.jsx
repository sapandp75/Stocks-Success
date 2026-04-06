import DirectionBadge from './DirectionBadge'

function RsiGauge({ value }) {
  if (value == null) return null
  const val = Math.round(value)
  const r = 28
  const circ = 2 * Math.PI * r
  const pct = val / 100
  const offset = circ * (1 - pct * 0.75)
  let color = '#6b7280'
  if (val < 30) color = '#00a562'
  else if (val > 70) color = '#d97b0e'

  return (
    <div className="flex flex-col items-center">
      <svg width="70" height="55" viewBox="0 0 70 55">
        <path
          d="M 7 48 A 28 28 0 0 1 63 48"
          fill="none"
          stroke="#e2e4e8"
          strokeWidth="5"
          strokeLinecap="round"
        />
        <path
          d="M 7 48 A 28 28 0 0 1 63 48"
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${circ * 0.75} ${circ}`}
          strokeDashoffset={offset}
        />
        <text x="35" y="44" textAnchor="middle" fontSize="14" fontWeight="bold" fill={color}>
          {val}
        </text>
      </svg>
      <div className="text-[10px]" style={{ color: '#6b7280' }}>RSI</div>
    </div>
  )
}

function MiniCard({ label, children }) {
  return (
    <div className="p-2 rounded" style={{ backgroundColor: '#f7f8fa' }}>
      <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>{label}</div>
      {children}
    </div>
  )
}

function BollingerBar({ upper, lower, middle, percentB }) {
  if (upper == null || lower == null) return <span className="text-xs" style={{ color: '#6b7280' }}>--</span>
  const pctB = percentB != null ? percentB : 0.5
  const pos = Math.max(0, Math.min(100, pctB * 100))

  return (
    <div>
      <div className="flex justify-between text-[10px]" style={{ color: '#6b7280' }}>
        <span>${lower?.toFixed(0)}</span>
        {middle != null && <span>${middle?.toFixed(0)}</span>}
        <span>${upper?.toFixed(0)}</span>
      </div>
      <div className="relative mt-1" style={{ height: '6px', backgroundColor: '#e2e4e8', borderRadius: '3px' }}>
        <div
          className="absolute"
          style={{
            left: `${pos}%`,
            top: '-1px',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#3b82f6',
            transform: 'translateX(-50%)',
          }}
        />
      </div>
      {percentB != null && (
        <div className="text-[10px] mt-1" style={{ color: '#6b7280' }}>%B: {percentB.toFixed(2)}</div>
      )}
    </div>
  )
}

export default function TechnicalPanel({ technicals }) {
  if (!technicals) return null

  const t = technicals
  const macd = t.macd || {}
  const bollinger = t.bollinger || {}
  const adx = t.adx
  const volume = t.volume || {}
  const supports = t.support_levels || t.support || []
  const resistances = t.resistance_levels || t.resistance || []
  const relStrength = t.relative_strength || {}

  const adxLabel = adx != null ? (adx > 25 ? 'Trending' : adx < 20 ? 'Ranging' : 'Weak Trend') : null
  const macdCross = macd.histogram != null ? (macd.histogram > 0 ? 'Bullish' : 'Bearish') : null

  const volumeTrend = volume.trend || volume.volume_trend
  const relVol = volume.relative_volume ?? volume.rel_volume
  const dryUp = volume.dry_up_warning || volume.dryup

  return (
    <div className="mt-4">
      <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Technical Analysis</div>

      {/* Direction + RSI row */}
      <div className="flex items-center gap-4 mb-3">
        {t.direction && <DirectionBadge direction={t.direction} />}
        <RsiGauge value={t.rsi} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {/* MACD */}
        <MiniCard label="MACD">
          <div className="text-xs" style={{ color: '#1a1a2e' }}>
            <div>Value: {macd.value?.toFixed(2) ?? '--'}</div>
            <div>Signal: {macd.signal?.toFixed(2) ?? '--'}</div>
            <div>Hist: {macd.histogram?.toFixed(2) ?? '--'}</div>
            {macdCross && (
              <span
                className="text-[10px] font-bold"
                style={{ color: macdCross === 'Bullish' ? '#00a562' : '#e5484d' }}
              >
                {macdCross} Crossover
              </span>
            )}
          </div>
        </MiniCard>

        {/* Bollinger */}
        <MiniCard label="Bollinger Bands">
          <BollingerBar
            upper={bollinger.upper}
            lower={bollinger.lower}
            middle={bollinger.middle}
            percentB={bollinger.percent_b}
          />
        </MiniCard>

        {/* ADX */}
        <MiniCard label="ADX">
          <div className="text-sm font-bold" style={{ color: '#1a1a2e' }}>
            {adx != null ? adx.toFixed(1) : '--'}
          </div>
          {adxLabel && (
            <span className="text-[10px]" style={{ color: adx > 25 ? '#00a562' : '#d97b0e' }}>
              {adxLabel}
            </span>
          )}
        </MiniCard>

        {/* Volume */}
        <MiniCard label="Volume">
          {relVol != null && (
            <div className="mb-1">
              <div className="text-[10px]" style={{ color: '#6b7280' }}>Rel Volume</div>
              <div className="relative mt-0.5" style={{ height: '6px', backgroundColor: '#e2e4e8', borderRadius: '3px', width: '100%' }}>
                <div style={{
                  height: '6px',
                  borderRadius: '3px',
                  backgroundColor: relVol > 1.5 ? '#00a562' : '#3b82f6',
                  width: `${Math.min(100, relVol * 50)}%`,
                }} />
              </div>
              <div className="text-xs font-semibold mt-0.5" style={{ color: '#1a1a2e' }}>{relVol.toFixed(2)}x</div>
            </div>
          )}
          {volumeTrend && <div className="text-[10px]" style={{ color: '#6b7280' }}>{volumeTrend}</div>}
          {dryUp && <div className="text-[10px] font-bold" style={{ color: '#d97b0e' }}>Dry-Up Warning</div>}
        </MiniCard>

        {/* Support / Resistance */}
        {(supports.length > 0 || resistances.length > 0) && (
          <MiniCard label="Support / Resistance">
            <div className="flex flex-wrap gap-1">
              {supports.map((s, i) => (
                <span key={`s${i}`} className="px-1 py-0.5 rounded text-[10px] font-medium" style={{ backgroundColor: '#dcfce7', color: '#00a562' }}>
                  S: ${typeof s === 'number' ? s.toFixed(0) : s}
                </span>
              ))}
              {resistances.map((r, i) => (
                <span key={`r${i}`} className="px-1 py-0.5 rounded text-[10px] font-medium" style={{ backgroundColor: '#fef2f2', color: '#e5484d' }}>
                  R: ${typeof r === 'number' ? r.toFixed(0) : r}
                </span>
              ))}
            </div>
          </MiniCard>
        )}

        {/* Relative Strength vs SPY */}
        {(relStrength.rs_20d != null || relStrength.rs_60d != null) && (
          <MiniCard label="Rel Strength vs SPY">
            <div className="text-xs" style={{ color: '#1a1a2e' }}>
              {relStrength.rs_20d != null && (
                <div>
                  20d: <span style={{ color: relStrength.rs_20d > 0 ? '#00a562' : '#e5484d' }}>
                    {relStrength.rs_20d > 0 ? '+' : ''}{(relStrength.rs_20d * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              {relStrength.rs_60d != null && (
                <div>
                  60d: <span style={{ color: relStrength.rs_60d > 0 ? '#00a562' : '#e5484d' }}>
                    {relStrength.rs_60d > 0 ? '+' : ''}{(relStrength.rs_60d * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </MiniCard>
        )}
      </div>
    </div>
  )
}
