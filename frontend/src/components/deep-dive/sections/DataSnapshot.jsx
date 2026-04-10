import CollapsibleSection from '../../CollapsibleSection'
import MissingSeverity from '../MissingSeverity'
import { fmt } from '../../../utils/fmt'
import { GREEN, RED, AMBER, TEXT, MUTED, BORDER } from '../../../constants/colors'

function MetricCell({ label, value, color, sub }) {
  return (
    <div>
      <div className="text-[11px]" style={{ color: MUTED }}>{label}</div>
      <div className="font-semibold text-sm" style={{ color: color || TEXT }}>{value ?? '\u2014'}</div>
      {sub && <div className="text-[10px]" style={{ color: MUTED }}>{sub}</div>}
    </div>
  )
}

export default function DataSnapshot({ ticker, fundamentals, gates, dataQuality, fcf3yrAvg, netDebt, sbc, sbcAdjusted, growthMetrics, reverseDcf, analyst, optionsSnapshot }) {
  const f = fundamentals || {}
  const gm = growthMetrics || {}

  if (!f.price && !f.name) {
    return (
      <CollapsibleSection title="Data Snapshot" number="1" accentColor="#3b82f6" defaultOpen>
        <MissingSeverity severity="critical" label="Fundamentals data unavailable" />
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title="Data Snapshot" number="1" accentColor="#3b82f6" defaultOpen>
      {/* Identity */}
      <div className="flex items-center gap-2 mb-3">
        <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{f.name}</span>
        <span className="text-sm" style={{ color: '#6b7280' }}>({ticker})</span>
        <span className="text-sm" style={{ color: '#6b7280' }}>· {f.sector} · {f.industry}</span>
      </div>

      {/* Data quality */}
      {dataQuality && (
        <div className="text-xs mb-3 flex gap-3" style={{ color: '#6b7280' }}>
          <span>Source: {dataQuality.source}</span>
          <span>Completeness: {(dataQuality.completeness * 100).toFixed(0)}%</span>
          {dataQuality.missing_fields?.length > 0 && (
            <span style={{ color: '#d97b0e' }}>Missing: {dataQuality.missing_fields.join(', ')}</span>
          )}
        </div>
      )}

      {/* Gates */}
      {gates && (
        <div className="flex items-center gap-2 mb-3">
          <span className="px-2 py-0.5 rounded text-xs font-bold text-white" style={{ backgroundColor: gates.passes_all ? '#00a562' : '#e5484d' }}>
            {gates.passes_all ? 'ALL GATES PASS' : 'GATES FAIL'}
          </span>
          {f.drop_from_high != null && (
            <span className="px-2 py-0.5 rounded text-xs font-bold" style={{ backgroundColor: '#fef2f2', color: '#e5484d' }}>
              {fmt(f.drop_from_high)} from 52w high
            </span>
          )}
          {f.earnings_date && (
            <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
              Earnings: {f.earnings_date}
            </span>
          )}
        </div>
      )}

      {/* Price & Size */}
      <div className="mb-3">
        <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>PRICE & SIZE</div>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <MetricCell label="Price" value={f.price != null ? `$${f.price.toFixed(2)}` : '—'} />
          <MetricCell label="Mkt Cap" value={fmt(f.market_cap, 'money')} />
          <MetricCell label="EV" value={fmt(f.enterprise_value, 'money')} />
          <MetricCell label="52w High" value={f.high_52w != null ? `$${f.high_52w.toFixed(2)}` : '—'} />
          <MetricCell label="52w Low" value={f.low_52w != null ? `$${f.low_52w.toFixed(2)}` : '—'} />
          <MetricCell label="Drop from High" value={fmt(f.drop_from_high)} color={f.drop_from_high > 0.2 ? '#e5484d' : '#6b7280'} />
        </div>
      </div>

      {/* Valuation */}
      <div className="mb-3">
        <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>VALUATION</div>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <MetricCell label="Fwd P/E" value={fmt(f.forward_pe, 'pe')} />
          <MetricCell label="Trail P/E" value={fmt(f.trailing_pe, 'pe')} />
          <MetricCell label="PEG" value={f.peg_ratio != null ? f.peg_ratio.toFixed(2) : '—'} />
          <MetricCell label="EV/EBIT" value={gm.ev_ebit != null ? gm.ev_ebit.toFixed(1) : '—'} />
          <MetricCell label="FCF Yield" value={fmt(gm.fcf_yield)} color={gm.fcf_yield > 0.05 ? '#00a562' : undefined} />
          <MetricCell
            label="Implied Growth"
            value={reverseDcf?.implied_growth_rate != null ? fmt(reverseDcf.implied_growth_rate, 'pctSigned') : '—'}
            color={reverseDcf?.implied_growth_rate < 0 ? '#e5484d' : '#00a562'}
          />
        </div>
      </div>

      {/* Profitability & Quality */}
      <div className="mb-3">
        <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>PROFITABILITY & QUALITY</div>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <MetricCell label="Gross Margin" value={fmt(f.gross_margin)} />
          <MetricCell label="Op Margin" value={fmt(f.operating_margin)} color={f.operating_margin > 0.2 ? '#00a562' : undefined} />
          <MetricCell label="Profit Margin" value={fmt(f.profit_margin)} />
          <MetricCell label="ROE" value={fmt(f.return_on_equity)} />
          <MetricCell label="ROIC" value={gm.roic_current != null ? fmt(gm.roic_current) : '—'} color={gm.roic_current > 0.15 ? '#00a562' : undefined} />
          <MetricCell label="Piotroski F" value={gm.piotroski != null ? `${gm.piotroski}/9` : '—'} color={gm.piotroski >= 7 ? '#00a562' : gm.piotroski <= 3 ? '#e5484d' : undefined} />
        </div>
      </div>

      {/* Cash Flow & Growth */}
      <div className="mb-3">
        <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>CASH FLOW & GROWTH</div>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <MetricCell label="FCF (TTM)" value={fmt(f.free_cash_flow, 'money')} />
          <MetricCell label="FCF 3yr Avg" value={fcf3yrAvg ? fmt(fcf3yrAvg, 'money') : '—'} />
          <MetricCell label="Rev Growth" value={fmt(f.revenue_growth)} color={f.revenue_growth > 0 ? '#00a562' : '#e5484d'} />
          <MetricCell label="Rev CAGR 3yr" value={gm.revenue_cagr_3yr != null ? fmt(gm.revenue_cagr_3yr) : '—'} />
          <MetricCell label="Buyback Yield" value={gm.buyback_yield != null ? fmt(gm.buyback_yield) : '—'} color={gm.buyback_yield > 0.02 ? '#00a562' : undefined} />
          <MetricCell label="Total Shrhlder Yield" value={gm.total_shareholder_yield != null ? fmt(gm.total_shareholder_yield) : '—'} />
        </div>
      </div>

      {/* Balance Sheet & Risk */}
      <div className="mb-3">
        <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>BALANCE SHEET & RISK</div>
        <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
          <MetricCell label="D/E" value={fmt(f.debt_to_equity, 'ratio')} color={f.debt_to_equity > 5 ? '#e5484d' : undefined} />
          <MetricCell label="Net Debt" value={netDebt ? fmt(netDebt, 'money') : '—'} />
          <MetricCell label="SBC" value={sbc ? fmt(sbc, 'money') : '—'} sub={sbcAdjusted ? 'FCF adjusted' : null} />
          <MetricCell label="Accruals" value={gm.accruals_ratio != null ? fmt(gm.accruals_ratio) : '—'} color={gm.accruals_ratio > 0.1 ? '#e5484d' : gm.accruals_ratio < 0 ? '#00a562' : undefined} sub={gm.accruals_ratio < 0 ? 'cash > earnings' : null} />
          <MetricCell label="Short %" value={fmt(f.short_percent)} />
          <MetricCell label="Beta" value={f.beta?.toFixed(2)} />
        </div>
      </div>

      {/* Options Sentiment */}
      {optionsSnapshot && (
        <div className="mb-3">
          <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>OPTIONS & SHORT INTEREST</div>
          <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
            <MetricCell
              label="Put/Call (OI)"
              value={optionsSnapshot.put_call_ratio_oi?.toFixed(3)}
              color={optionsSnapshot.put_call_ratio_oi > 1 ? '#e5484d' : optionsSnapshot.put_call_ratio_oi < 0.7 ? '#00a562' : '#d97b0e'}
              sub={optionsSnapshot.put_call_ratio_oi > 1 ? 'bearish' : optionsSnapshot.put_call_ratio_oi < 0.7 ? 'bullish' : 'neutral'}
            />
            <MetricCell
              label="Put/Call (Vol)"
              value={optionsSnapshot.put_call_ratio_vol?.toFixed(3)}
              color={optionsSnapshot.put_call_ratio_vol > 1 ? '#e5484d' : optionsSnapshot.put_call_ratio_vol < 0.7 ? '#00a562' : '#d97b0e'}
            />
            <MetricCell label="Total Call OI" value={optionsSnapshot.total_call_oi?.toLocaleString()} />
            <MetricCell label="Total Put OI" value={optionsSnapshot.total_put_oi?.toLocaleString()} />
            <MetricCell
              label="Short Interest"
              value={optionsSnapshot.short_interest ? `${(optionsSnapshot.short_interest / 1e6).toFixed(1)}M` : fmt(f.short_percent)}
            />
            <MetricCell
              label="Short % Float"
              value={optionsSnapshot.short_pct_float != null ? `${(optionsSnapshot.short_pct_float * 100).toFixed(1)}%` : '—'}
              color={optionsSnapshot.short_pct_float > 0.1 ? '#e5484d' : undefined}
            />
          </div>
        </div>
      )}

      {/* Analyst */}
      {analyst && (
        <div className="mb-1">
          <div className="text-[10px] font-medium mb-1" style={{ color: '#6b7280' }}>ANALYST CONSENSUS</div>
          <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
            <MetricCell
              label="Consensus"
              value={analyst.consensus?.toUpperCase()}
              color={analyst.consensus === 'buy' ? '#00a562' : analyst.consensus === 'sell' ? '#e5484d' : '#d97b0e'}
            />
            <MetricCell label="Target Mean" value={analyst.target_mean != null ? `$${analyst.target_mean.toFixed(0)}` : '—'} />
            <MetricCell label="Target Low" value={analyst.target_low != null ? `$${analyst.target_low.toFixed(0)}` : '—'} />
            <MetricCell label="Target High" value={analyst.target_high != null ? `$${analyst.target_high.toFixed(0)}` : '—'} />
            <MetricCell label="# Analysts" value={analyst.num_analysts} />
            <MetricCell
              label="Contrarian Signal"
              value={analyst.contrarian_signal}
              color={analyst.contrarian_signal === 'CONSENSUS' ? '#6b7280' : '#d97b0e'}
            />
          </div>
        </div>
      )}
    </CollapsibleSection>
  )
}
