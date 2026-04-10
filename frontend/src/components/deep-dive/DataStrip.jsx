import { useState } from 'react'
import TechnicalPanel from '../TechnicalPanel'
import SparklineGrid from '../SparklineGrid'
import TradingViewChart from '../charts/TradingViewChart'

function MetricCell({ label, value, color }) {
  return (
    <div>
      <div className="text-[10px]" style={{ color: '#6b7280' }}>{label}</div>
      <div className="font-semibold text-xs" style={{ color: color || '#1a1a2e' }}>{value ?? '—'}</div>
    </div>
  )
}

function fmt(val, type = 'pct') {
  if (val == null) return '—'
  if (type === 'pct') return `${(val * 100).toFixed(1)}%`
  if (type === 'pe') return val.toFixed(1)
  if (type === 'ratio') return val.toFixed(2)
  if (type === 'money') {
    if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
    return `$${val.toFixed(0)}`
  }
  return String(val)
}

function LeapsRow({ opt }) {
  const premium = opt.mid || opt.premium_per_contract
  const meetsRules = premium <= 7 && (opt.oi || 0) >= 500 && opt.delta >= 0.25 && opt.delta <= 0.40
  return (
    <tr style={{ backgroundColor: meetsRules ? '#f0fdf4' : undefined }}>
      <td className="px-2 py-1 text-xs">{opt.expiry}</td>
      <td className="px-2 py-1 text-xs">CALL</td>
      <td className="px-2 py-1 text-xs font-mono">${opt.strike}</td>
      <td className="px-2 py-1 text-xs font-mono">${premium?.toFixed(2)}</td>
      <td className="px-2 py-1 text-xs font-mono">{opt.delta?.toFixed(2)}</td>
      <td className="px-2 py-1 text-xs font-mono">{opt.iv != null ? `${(opt.iv * 100).toFixed(0)}%` : '—'}</td>
      <td className="px-2 py-1 text-xs font-mono">{opt.oi?.toLocaleString()}</td>
      <td className="px-2 py-1 text-xs font-mono">{opt.dte}</td>
      {meetsRules && <td className="px-1 text-[10px]" style={{ color: '#00a562' }}>PASS</td>}
      {!meetsRules && <td className="px-1 text-[10px]" style={{ color: '#6b7280' }}></td>}
    </tr>
  )
}

const TABS = ['Fundamentals', 'Technicals', 'Chart', 'LEAPS', 'History']

export default function DataStrip({ ticker, fundamentals, technicals, financialHistory, growthMetrics, quarterly, forwardEstimates, optionsSnapshot }) {
  const [open, setOpen] = useState(true)
  const [tab, setTab] = useState('Fundamentals')
  const f = fundamentals || {}
  const gm = growthMetrics || {}
  const opts = optionsSnapshot || {}

  return (
    <div className="border-b" style={{ borderColor: '#e2e4e8', backgroundColor: '#ffffff' }}>
      {/* Tab bar */}
      <div className="flex items-center justify-between px-5 max-w-5xl mx-auto">
        <div className="flex gap-1">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => { setTab(t); setOpen(true) }}
              className="px-3 py-2 text-xs font-medium border-b-2 transition-colors"
              style={{
                borderColor: tab === t && open ? '#3b82f6' : 'transparent',
                color: tab === t && open ? '#1a1a2e' : '#6b7280',
              }}
            >
              {t}
            </button>
          ))}
        </div>
        <button onClick={() => setOpen(!open)} className="text-xs px-2 py-1" style={{ color: '#6b7280' }}>
          {open ? '▲' : '▼'}
        </button>
      </div>

      {/* Content */}
      {open && (
        <div className="px-5 pb-4 pt-2 max-w-5xl mx-auto" style={{ maxHeight: '450px', overflow: 'auto' }}>
          {tab === 'Fundamentals' && (
            <div className="space-y-3">
              {/* Valuation */}
              <div>
                <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>VALUATION</div>
                <div className="grid grid-cols-5 gap-3">
                  <MetricCell label="Fwd P/E" value={fmt(f.forward_pe, 'pe')} />
                  <MetricCell label="Trail P/E" value={fmt(f.trailing_pe, 'pe')} />
                  <MetricCell label="PEG" value={gm.peg_ratio != null ? gm.peg_ratio.toFixed(2) : '—'} />
                  <MetricCell label="EV/EBIT" value={gm.ev_ebit != null ? gm.ev_ebit.toFixed(1) : '—'} />
                  <MetricCell label="FCF Yield" value={gm.fcf_yield != null ? fmt(gm.fcf_yield) : '—'} color={gm.fcf_yield > 0.05 ? '#00a562' : undefined} />
                </div>
              </div>
              {/* Profitability */}
              <div>
                <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>PROFITABILITY</div>
                <div className="grid grid-cols-5 gap-3">
                  <MetricCell label="Gross Margin" value={fmt(f.gross_margin)} />
                  <MetricCell label="Op Margin" value={fmt(f.operating_margin)} color={f.operating_margin > 0.2 ? '#00a562' : undefined} />
                  <MetricCell label="Profit Margin" value={fmt(f.profit_margin)} />
                  <MetricCell label="ROE" value={fmt(f.return_on_equity)} />
                  <MetricCell label="ROIC" value={gm.roic_current != null ? fmt(gm.roic_current) : '—'} />
                </div>
              </div>
              {/* Health */}
              <div>
                <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>HEALTH</div>
                <div className="grid grid-cols-5 gap-3">
                  <MetricCell label="D/E" value={fmt(f.debt_to_equity, 'ratio')} color={f.debt_to_equity > 5 ? '#e5484d' : undefined} />
                  <MetricCell label="FCF" value={fmt(f.free_cash_flow, 'money')} />
                  <MetricCell label="Piotroski F" value={gm.piotroski ?? '—'} />
                  <MetricCell label="Accruals" value={gm.accruals_ratio != null ? fmt(gm.accruals_ratio) : '—'} color={gm.accruals_ratio > 0.1 ? '#e5484d' : undefined} />
                  <MetricCell label="Buyback Yield" value={gm.buyback_yield != null ? fmt(gm.buyback_yield) : '—'} />
                </div>
              </div>
              {/* Size */}
              <div>
                <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>SIZE</div>
                <div className="grid grid-cols-5 gap-3">
                  <MetricCell label="Mkt Cap" value={fmt(f.market_cap, 'money')} />
                  <MetricCell label="EV" value={fmt(f.enterprise_value, 'money')} />
                  <MetricCell label="Avg Volume" value={f.avg_volume ? `${(f.avg_volume / 1e6).toFixed(1)}M` : '—'} />
                  <MetricCell label="Short %" value={fmt(f.short_percent)} />
                  <MetricCell label="Short Ratio" value={f.short_ratio != null ? f.short_ratio.toFixed(1) : '—'} />
                </div>
              </div>
            </div>
          )}

          {tab === 'Technicals' && (
            <div>
              {technicals ? <TechnicalPanel technicals={technicals} /> : <p className="text-sm italic" style={{ color: '#6b7280' }}>No technical data available</p>}
            </div>
          )}

          {tab === 'Chart' && (
            <div>
              {ticker ? <TradingViewChart ticker={ticker} height={400} /> : <p className="text-sm italic" style={{ color: '#6b7280' }}>No ticker specified</p>}
            </div>
          )}

          {tab === 'LEAPS' && (
            <div>
              {opts.leaps && opts.leaps.length > 0 ? (
                <div className="space-y-3">
                  {/* PCR Summary */}
                  {opts.put_call_ratio_oi != null && (
                    <div className="grid grid-cols-4 gap-3 mb-3">
                      <MetricCell label="PCR (OI)" value={opts.put_call_ratio_oi?.toFixed(2)} color={opts.put_call_ratio_oi > 1 ? '#00a562' : '#e5484d'} />
                      <MetricCell label="PCR (Vol)" value={opts.put_call_ratio_vol?.toFixed(2)} />
                      <MetricCell label="Total Call OI" value={opts.total_call_oi?.toLocaleString()} />
                      <MetricCell label="Total Put OI" value={opts.total_put_oi?.toLocaleString()} />
                    </div>
                  )}
                  {/* LEAPS Table */}
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>Expiry</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>Type</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>Strike</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>Premium</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>Delta</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>IV</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>OI</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}>DTE</th>
                          <th className="px-2 py-1 text-[10px] font-medium" style={{ color: '#6b7280' }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {opts.leaps.map((opt, i) => <LeapsRow key={i} opt={opt} />)}
                      </tbody>
                    </table>
                  </div>
                  <div className="text-[10px] mt-1" style={{ color: '#6b7280' }}>
                    Green rows pass options rules: premium &le;$7, OI &ge;500, delta 0.25-0.40
                  </div>
                </div>
              ) : (
                <p className="text-sm italic" style={{ color: '#6b7280' }}>No LEAPS data available</p>
              )}
            </div>
          )}

          {tab === 'History' && (
            <div>
              {financialHistory || quarterly
                ? <SparklineGrid data={financialHistory} quarterly={quarterly} growthMetrics={growthMetrics} fundamentals={fundamentals} />
                : <p className="text-sm italic" style={{ color: '#6b7280' }}>No historical data available</p>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
