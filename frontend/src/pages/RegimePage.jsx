import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useRegime } from '../RegimeContext'
import { getBreadth } from '../api'
import RegimeBadge from '../components/RegimeBadge'
import EarningsCalendar from '../components/EarningsCalendar'

function DirectionCard({ data }) {
  if (!data) return null
  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{data.ticker}</span>
        <span className="text-sm font-medium px-2 py-0.5 rounded" style={{
          backgroundColor: data.direction?.includes('UPTREND') ? '#dcfce7' : data.direction?.includes('DOWNTREND') ? '#fef2f2' : '#fef9c3',
          color: data.direction?.includes('UPTREND') ? '#00a562' : data.direction?.includes('DOWNTREND') ? '#e5484d' : '#d97b0e',
        }}>
          {(data.direction || 'UNKNOWN').replace(/_/g, ' ')}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span style={{ color: '#6b7280' }}>Price</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.price?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>EMA 20</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.ema20?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>SMA 50</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.sma50?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>SMA 200</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.sma200?.toFixed(2)}</div>
        </div>
      </div>
    </div>
  )
}

function BreadthSummaryRow() {
  const [breadth, setBreadth] = useState(null)

  useEffect(() => {
    getBreadth().then(setBreadth).catch(() => {})
  }, [])

  if (!breadth) return null

  const verdictColor = breadth.verdict === 'RISK-ON' ? '#00a562' : breadth.verdict === 'RISK-OFF' ? '#e5484d' : '#d97b0e'
  const nysi = breadth.mcclellan?.nysi?.value
  const bpspx = breadth.bullish_pct?.spx
  const pct200 = breadth.spx_breadth?.pct_above_200d

  return (
    <div className="mt-6 mb-6">
      <div className="bg-white rounded-lg border p-4 flex items-center gap-4 flex-wrap" style={{ borderColor: '#e2e4e8' }}>
        <span className="text-sm font-bold px-3 py-1 rounded" style={{
          backgroundColor: verdictColor + '20',
          color: verdictColor,
        }}>
          {breadth.verdict} {breadth.score}/10
        </span>
        <div className="flex gap-3 text-sm flex-1" style={{ color: '#6b7280' }}>
          <span>S&P {pct200 != null ? `${pct200}%` : '—'} above 200d</span>
          <span>·</span>
          <span>$NYSI {nysi != null ? nysi.toLocaleString() : '—'}</span>
          <span>·</span>
          <span>$BPSPX {bpspx != null ? `${bpspx}%` : '—'}</span>
        </div>
        <Link to="/breadth" className="text-sm font-medium" style={{ color: '#00a562' }}>
          View full breadth →
        </Link>
      </div>
    </div>
  )
}

export default function RegimePage() {
  const { data, loading, error } = useRegime()

  if (loading) return <div className="p-8" style={{ color: '#6b7280' }}>Loading regime data...</div>
  if (!data) return (
    <div className="p-8" style={{ color: '#e5484d' }}>
      Failed to load regime data.{error && ` (${error})`}
    </div>
  )

  const { spy, qqq, regime } = data

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6" style={{ color: '#1a1a2e' }}>Market Regime — Gate 0</h1>

      <div className="bg-white rounded-lg border p-6 mb-6" style={{ borderColor: '#e2e4e8' }}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Current Verdict</div>
            <RegimeBadge verdict={regime.verdict} vix={regime.vix} />
          </div>
          <div className="text-right">
            <div className="text-sm" style={{ color: '#6b7280' }}>Max New Positions</div>
            <div className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>{regime.max_new_positions}</div>
          </div>
        </div>
        <div className="text-sm p-3 rounded" style={{ backgroundColor: '#f7f8fa', color: '#1a1a2e' }}>
          {regime.options_note}
        </div>
        {regime.vix_tax && regime.vix_tax.premium_premium_pct > 0 && (
          <div className="text-sm mt-3 p-3 rounded" style={{ backgroundColor: '#fef9c3', color: '#d97b0e' }}>
            VIX Tax: Premiums ~{regime.vix_tax.premium_premium_pct}% above normal. {regime.vix_tax.note}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DirectionCard data={spy} />
        <DirectionCard data={qqq} />
      </div>

      <BreadthSummaryRow />

      <EarningsCalendar />
    </div>
  )
}
