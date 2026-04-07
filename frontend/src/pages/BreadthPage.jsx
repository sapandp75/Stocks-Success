import { useState, useEffect } from 'react'
import { getBreadth } from '../api'

const COLORS = {
  green: '#00a562', red: '#e5484d', amber: '#d97b0e',
  text: '#1a1a2e', muted: '#6b7280', border: '#e2e4e8', bg: '#f0f1f3',
}

function verdictColor(verdict) {
  if (verdict === 'RISK-ON') return COLORS.green
  if (verdict === 'RISK-OFF') return COLORS.red
  return COLORS.amber
}

function signalBadge(signal) {
  if (!signal) return null
  const bullish = ['BULLISH', 'STRONG', 'HEALTHY', 'ADVANCING', 'OVERBOUGHT', 'LOW', 'COMPLACENT']
  const bearish = ['BEARISH', 'DEEPLY_BEARISH', 'POOR', 'DECLINING', 'OVERSOLD', 'EXTREME', 'HIGH', 'EXTREME_FEAR', 'PANIC_SELLING', 'FEAR']
  let bg, color
  if (bullish.includes(signal)) { bg = '#dcfce7'; color = COLORS.green }
  else if (bearish.includes(signal)) { bg = '#fef2f2'; color = COLORS.red }
  else { bg = '#fef9c3'; color = COLORS.amber }
  return (
    <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ backgroundColor: bg, color }}>
      {signal.replace(/_/g, ' ')}
    </span>
  )
}

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-lg border p-4" style={{ borderColor: COLORS.border }}>
      {title && <div className="text-xs font-medium mb-2" style={{ color: COLORS.muted }}>{title}</div>}
      {children}
    </div>
  )
}

function ValueCard({ label, data }) {
  if (!data) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const changeArrow = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '—'
  const changeColor = data.change > 0 ? COLORS.green : data.change < 0 ? COLORS.red : COLORS.muted
  return (
    <Card title={label}>
      <div className="flex items-center justify-between">
        <span className="text-xl font-bold" style={{ color: COLORS.text }}>
          {typeof data.value === 'number' ? data.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
        </span>
        {signalBadge(data.signal)}
      </div>
      <div className="text-xs mt-1" style={{ color: changeColor }}>
        {changeArrow} {Math.abs(data.change || 0).toFixed(2)}
      </div>
    </Card>
  )
}

function OscillatorCard({ label, data, min, max }) {
  if (!data) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const range = max - min
  const pct = Math.max(0, Math.min(100, ((data.value - min) / range) * 100))
  const changeArrow = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '—'
  const changeColor = data.change > 0 ? COLORS.green : data.change < 0 ? COLORS.red : COLORS.muted
  return (
    <Card title={label}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xl font-bold" style={{ color: COLORS.text }}>
          {data.value.toFixed(2)}
        </span>
        {signalBadge(data.signal)}
      </div>
      <div className="text-xs mb-1" style={{ color: changeColor }}>
        {changeArrow} {Math.abs(data.change || 0).toFixed(2)}
      </div>
      <div className="relative h-2 rounded-full" style={{
        background: `linear-gradient(to right, ${COLORS.red}, ${COLORS.amber} 30%, ${COLORS.green} 50%, ${COLORS.amber} 70%, ${COLORS.red})`,
      }}>
        <div className="absolute top-0 w-0.5 h-full bg-black rounded" style={{ left: `${pct}%`, transform: 'translateX(-50%)' }} />
      </div>
      <div className="flex justify-between text-xs mt-0.5" style={{ color: COLORS.muted }}>
        <span>{min}</span><span>0</span><span>{max}</span>
      </div>
    </Card>
  )
}

function ParticipationCard({ label, data }) {
  if (!data || data.pct_above_200d == null) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const pct200 = data.pct_above_200d
  const pct50 = data.pct_above_50d
  const pct20 = data.pct_above_20d
  const barColor = pct200 >= 60 ? COLORS.green : pct200 >= 40 ? COLORS.amber : COLORS.red
  return (
    <Card title={label}>
      <div className="text-xl font-bold" style={{ color: COLORS.text }}>{pct200.toFixed(1)}%</div>
      <div className="text-xs" style={{ color: COLORS.muted }}>above 200d SMA</div>
      <div className="h-2 rounded-full mt-2" style={{ backgroundColor: '#e2e4e8' }}>
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct200)}%`, backgroundColor: barColor }} />
      </div>
      <div className="flex gap-3 text-xs mt-2" style={{ color: COLORS.muted }}>
        <span>50d: {pct50 != null ? `${pct50.toFixed(1)}%` : 'N/A'}</span>
        <span>20d: {pct20 != null ? `${pct20.toFixed(1)}%` : 'N/A'}</span>
      </div>
    </Card>
  )
}

function SectorChart({ sectors }) {
  if (!sectors || sectors.length === 0) return null
  const sorted = [...sectors].sort((a, b) => b.value - a.value)
  const maxVal = 100
  return (
    <Card title="Sector Bullish %">
      <div className="space-y-1.5">
        {sorted.map(s => {
          const barColor = s.value >= 60 ? COLORS.green : s.value >= 40 ? COLORS.amber : COLORS.red
          return (
            <div key={s.symbol} className="flex items-center gap-2">
              <div className="text-xs w-28 truncate" style={{ color: COLORS.text }}>{s.name}</div>
              <div className="flex-1 h-3 rounded-full" style={{ backgroundColor: '#e2e4e8' }}>
                <div className="h-full rounded-full" style={{ width: `${s.value / maxVal * 100}%`, backgroundColor: barColor }} />
              </div>
              <div className="text-xs w-10 text-right font-medium" style={{ color: COLORS.text }}>{s.value.toFixed(0)}%</div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export default function BreadthPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      getBreadth()
        .then(d => { if (!cancelled) { setData(d); setLoading(false); setError(null) } })
        .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    }
    load()
    const interval = setInterval(load, 3600000) // 1h refresh
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (loading) return <div className="p-8" style={{ color: COLORS.muted }}>Loading breadth data...</div>
  if (!data) return (
    <div className="p-8" style={{ color: COLORS.red }}>
      Failed to load breadth data.{error && ` (${error})`}
    </div>
  )

  const mc = data.mcclellan || {}
  const ad = data.advance_decline || {}
  const sent = data.sentiment || {}
  const bp = data.bullish_pct || {}

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6" style={{ color: COLORS.text }}>Market Breadth</h1>

      {/* Section 1: Summary strip */}
      <div className="bg-white rounded-lg border p-4 mb-6 flex items-center gap-4 flex-wrap" style={{ borderColor: COLORS.border }}>
        <span className="text-sm font-bold px-3 py-1 rounded" style={{
          backgroundColor: verdictColor(data.verdict) + '20',
          color: verdictColor(data.verdict),
        }}>
          {data.verdict}
        </span>
        <span className="text-2xl font-bold" style={{ color: COLORS.text }}>{data.score}/10</span>
        <div className="flex gap-4 text-sm" style={{ color: COLORS.muted }}>
          <span>$NYSI {mc.nysi?.value?.toLocaleString() ?? 'N/A'}</span>
          <span>$BPSPX {bp.spx != null ? `${bp.spx}%` : 'N/A'}</span>
          <span>S&P above 200d {data.spx_breadth?.pct_above_200d != null ? `${data.spx_breadth.pct_above_200d}%` : 'N/A'}</span>
        </div>
        {data.stale && (
          <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#fef9c3', color: COLORS.amber }}>
            STALE DATA
          </span>
        )}
      </div>

      {data.verdict_note && (
        <div className="text-sm mb-6 p-3 rounded" style={{ backgroundColor: '#f7f8fa', color: COLORS.muted }}>
          {data.verdict_note}
        </div>
      )}

      {/* Section 2: McClellan */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>McClellan Indicators</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <OscillatorCard label="$NYMO — NYSE Oscillator" data={mc.nymo} min={-150} max={150} />
        <OscillatorCard label="$NYSI — NYSE Summation" data={mc.nysi} min={-1500} max={1500} />
        <OscillatorCard label="$NAMO — Nasdaq Oscillator" data={mc.namo} min={-150} max={150} />
        <OscillatorCard label="$NASI — Nasdaq Summation" data={mc.nasi} min={-1500} max={1500} />
      </div>

      {/* Section 3: Advance/Decline + Highs/Lows */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Advance/Decline & Highs/Lows</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <ValueCard label="$NYAD — NYSE A/D" data={ad.nyad} />
        <ValueCard label="$NAAD — Nasdaq A/D" data={ad.naad} />
        <ValueCard label="$NYHL — NYSE Highs−Lows" data={ad.nyhl} />
        <ValueCard label="$NAHL — Nasdaq Highs−Lows" data={ad.nahl} />
      </div>

      {/* Section 4: Participation */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Participation</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <ParticipationCard label="S&P 500 — % Above MAs" data={data.spx_breadth} />
        <ParticipationCard label="Nasdaq 100 — % Above MAs" data={data.ndx_breadth} />
        <ValueCard label="$BPSPX — S&P 500 BP" data={bp.spx != null ? { value: bp.spx, change: 0, signal: bp.spx >= 60 ? 'BULLISH' : bp.spx >= 40 ? 'NEUTRAL' : 'BEARISH' } : null} />
        <ValueCard label="$BPNDX — Nasdaq 100 BP" data={bp.ndx != null ? { value: bp.ndx, change: 0, signal: bp.ndx >= 60 ? 'BULLISH' : bp.ndx >= 40 ? 'NEUTRAL' : 'BEARISH' } : null} />
      </div>

      {/* Section 5: Sentiment & Sector BP */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Sentiment & Sector Bullish %</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="space-y-4">
          <ValueCard label="$CPC — Put/Call Ratio" data={sent.cpc} />
          <ValueCard label="$TRIN — Arms Index" data={sent.trin} />
          <ValueCard label="$VIX — Volatility Index" data={sent.vix} />
        </div>
        <div className="lg:col-span-2">
          <SectorChart sectors={bp.sectors} />
        </div>
      </div>
    </div>
  )
}
