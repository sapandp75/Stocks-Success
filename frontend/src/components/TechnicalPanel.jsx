import { GREEN, RED, AMBER, TEXT, MUTED, BORDER, HOVER } from '../constants/colors'
import DirectionBadge from './DirectionBadge'

function RsiGauge({ value }) {
  if (value == null) return null
  const val = Math.round(value)
  const r = 28
  const circ = 2 * Math.PI * r
  const pct = val / 100
  const offset = circ * (1 - pct * 0.75)
  let color = MUTED
  if (val < 30) color = GREEN
  else if (val > 70) color = AMBER

  return (
    <div className="flex flex-col items-center">
      <svg width="70" height="55" viewBox="0 0 70 55">
        <path d="M 7 48 A 28 28 0 0 1 63 48" fill="none" stroke={BORDER} strokeWidth="5" strokeLinecap="round" />
        <path d="M 7 48 A 28 28 0 0 1 63 48" fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
          strokeDasharray={`${circ * 0.75} ${circ}`} strokeDashoffset={offset} />
        <text x="35" y="44" textAnchor="middle" fontSize="14" fontWeight="bold" fill={color}>{val}</text>
      </svg>
      <div className="text-[10px]" style={{ color: MUTED }}>RSI</div>
    </div>
  )
}

function MiniCard({ label, children }) {
  return (
    <div className="p-2 rounded" style={{ backgroundColor: HOVER }}>
      <div className="text-[10px] font-medium mb-1" style={{ color: MUTED }}>{label}</div>
      {children}
    </div>
  )
}

function TrendBadge({ label, value }) {
  if (!value) return null
  const color = value === 'bullish' ? GREEN : value === 'bearish' ? RED : AMBER
  return (
    <div className="flex items-center gap-1">
      <span className="text-[10px]" style={{ color: MUTED }}>{label}:</span>
      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white" style={{ backgroundColor: color }}>
        {value.toUpperCase()}
      </span>
    </div>
  )
}

function MaRow({ label, value, price }) {
  if (value == null) return null
  const pctDiff = price ? ((price / value - 1) * 100) : null
  const above = pctDiff != null && pctDiff > 0
  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-[10px]" style={{ color: MUTED }}>{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold" style={{ color: TEXT }}>${value.toFixed(2)}</span>
        {pctDiff != null && (
          <span className="text-[10px] font-medium" style={{ color: above ? GREEN : RED }}>
            {above ? '+' : ''}{pctDiff.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  )
}

function PivotRow({ label, value, color }) {
  if (value == null) return null
  return (
    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium" style={{ backgroundColor: color === 'support' ? '#dcfce7' : color === 'resistance' ? '#fef2f2' : '#f3f4f6', color: color === 'support' ? GREEN : color === 'resistance' ? RED : TEXT }}>
      {label}: ${value.toFixed(2)}
    </span>
  )
}

export default function TechnicalPanel({ technicals }) {
  if (!technicals) return null
  const t = technicals

  const ma = t.moving_averages || {}
  const macd = t.macd || {}
  const boll = t.bollinger || {}
  const vol = t.volume || {}
  const sr = t.support_resistance || {}
  const rs = t.relative_strength || {}
  const price = t.price

  const adxLabel = t.adx != null ? (t.adx > 25 ? 'Trending' : t.adx < 20 ? 'Ranging' : 'Weak Trend') : null

  return (
    <div>
      {/* Row 1: Direction + Trends + RSI */}
      <div className="flex items-center gap-4 mb-3 flex-wrap">
        {t.direction && <DirectionBadge direction={t.direction} />}
        <TrendBadge label="Short-term" value={t.short_trend} />
        <TrendBadge label="Long-term" value={t.long_trend} />
        <RsiGauge value={t.rsi} />
        {t.atr != null && (
          <div className="text-center">
            <div className="text-xs font-semibold" style={{ color: TEXT }}>${t.atr.toFixed(2)}</div>
            <div className="text-[10px]" style={{ color: MUTED }}>ATR(14)</div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {/* Moving Averages */}
        <MiniCard label="MOVING AVERAGES">
          <div>
            <MaRow label="EMA 20" value={ma.ema20} price={price} />
            <MaRow label="SMA 50" value={ma.sma50} price={price} />
            <MaRow label="SMA 200" value={ma.sma200} price={price} />
          </div>
        </MiniCard>

        {/* MACD */}
        <MiniCard label="MACD">
          <div className="text-xs" style={{ color: TEXT }}>
            <div className="flex justify-between"><span style={{ color: MUTED }}>MACD:</span> <span>{macd.value?.toFixed(2) ?? '--'}</span></div>
            <div className="flex justify-between"><span style={{ color: MUTED }}>Signal:</span> <span>{macd.signal?.toFixed(2) ?? '--'}</span></div>
            <div className="flex justify-between"><span style={{ color: MUTED }}>Hist:</span> <span style={{ color: macd.histogram > 0 ? GREEN : RED }}>{macd.histogram?.toFixed(2) ?? '--'}</span></div>
            {macd.crossover && macd.crossover !== 'none' && (
              <span className="text-[10px] font-bold" style={{ color: macd.crossover === 'bullish' ? GREEN : RED }}>
                {macd.crossover.toUpperCase()} CROSS
              </span>
            )}
          </div>
        </MiniCard>

        {/* Bollinger Bands */}
        <MiniCard label="BOLLINGER BANDS">
          {boll.upper != null ? (
            <div>
              <div className="flex justify-between text-[10px]" style={{ color: MUTED }}>
                <span>L: ${boll.lower?.toFixed(0)}</span>
                <span>M: ${boll.middle?.toFixed(0)}</span>
                <span>U: ${boll.upper?.toFixed(0)}</span>
              </div>
              <div className="relative mt-1" style={{ height: '6px', backgroundColor: BORDER, borderRadius: '3px' }}>
                <div className="absolute" style={{
                  left: `${Math.max(0, Math.min(100, (boll.percent_b ?? 0.5) * 100))}%`,
                  top: '-1px', width: '8px', height: '8px', borderRadius: '50%',
                  backgroundColor: '#3b82f6', transform: 'translateX(-50%)',
                }} />
              </div>
              <div className="text-[10px] mt-1" style={{ color: MUTED }}>%B: {boll.percent_b?.toFixed(2) ?? '--'}</div>
            </div>
          ) : <span className="text-xs" style={{ color: MUTED }}>--</span>}
        </MiniCard>

        {/* ADX */}
        <MiniCard label="ADX (TREND STRENGTH)">
          <div className="text-sm font-bold" style={{ color: TEXT }}>
            {t.adx != null ? t.adx.toFixed(1) : '--'}
          </div>
          {adxLabel && <span className="text-[10px]" style={{ color: t.adx > 25 ? GREEN : AMBER }}>{adxLabel}</span>}
        </MiniCard>

        {/* Volume */}
        <MiniCard label="VOLUME">
          {vol.relative_volume != null && (
            <div className="mb-1">
              <div className="relative mt-0.5" style={{ height: '6px', backgroundColor: BORDER, borderRadius: '3px' }}>
                <div style={{
                  height: '6px', borderRadius: '3px',
                  backgroundColor: vol.relative_volume > 1.5 ? GREEN : '#3b82f6',
                  width: `${Math.min(100, vol.relative_volume * 50)}%`,
                }} />
              </div>
              <div className="text-xs font-semibold mt-0.5" style={{ color: TEXT }}>{vol.relative_volume.toFixed(2)}x avg</div>
            </div>
          )}
          {vol.trend && <div className="text-[10px]" style={{ color: MUTED }}>Trend: {vol.trend}</div>}
          {vol.dry_up_warning && <div className="text-[10px] font-bold" style={{ color: AMBER }}>DRY-UP WARNING</div>}
        </MiniCard>

        {/* RS vs SPX */}
        <MiniCard label="RELATIVE STRENGTH vs SPX">
          <div className="text-xs" style={{ color: TEXT }}>
            {rs.rs_20d != null && (
              <div className="flex justify-between">
                <span style={{ color: MUTED }}>20d:</span>
                <span style={{ color: rs.rs_20d > 0 ? GREEN : RED }}>
                  {rs.rs_20d > 0 ? '+' : ''}{(rs.rs_20d * 100).toFixed(1)}%
                </span>
              </div>
            )}
            {rs.rs_60d != null && (
              <div className="flex justify-between">
                <span style={{ color: MUTED }}>60d:</span>
                <span style={{ color: rs.rs_60d > 0 ? GREEN : RED }}>
                  {rs.rs_60d > 0 ? '+' : ''}{(rs.rs_60d * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </MiniCard>
      </div>

      {/* Support & Resistance — full row */}
      <div className="mt-2 p-2 rounded" style={{ backgroundColor: HOVER }}>
        <div className="text-[10px] font-medium mb-1.5" style={{ color: MUTED }}>SUPPORT & RESISTANCE (PIVOT POINTS)</div>
        <div className="flex flex-wrap gap-1.5">
          <PivotRow label="S3" value={sr.s3} color="support" />
          <PivotRow label="S2" value={sr.s2} color="support" />
          <PivotRow label="S1" value={sr.s1} color="support" />
          <PivotRow label="P" value={sr.pivot} color="pivot" />
          <PivotRow label="R1" value={sr.r1} color="resistance" />
          <PivotRow label="R2" value={sr.r2} color="resistance" />
          <PivotRow label="R3" value={sr.r3} color="resistance" />
        </div>
        {/* Dynamic S/R from price action */}
        {(sr.support?.length > 0 || sr.resistance?.length > 0) && (
          <div className="mt-1.5 pt-1.5 border-t flex flex-wrap gap-1.5" style={{ borderColor: BORDER }}>
            <span className="text-[10px]" style={{ color: MUTED }}>Price-action:</span>
            {sr.support?.map((s, i) => (
              <span key={`s${i}`} className="px-1.5 py-0.5 rounded text-[10px] font-medium" style={{ backgroundColor: '#dcfce7', color: GREEN }}>
                S: ${s.toFixed(2)}
              </span>
            ))}
            {sr.resistance?.map((r, i) => (
              <span key={`r${i}`} className="px-1.5 py-0.5 rounded text-[10px] font-medium" style={{ backgroundColor: '#fef2f2', color: RED }}>
                R: ${r.toFixed(2)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
