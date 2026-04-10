import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import QuarterlyBarChart from '../../charts/QuarterlyBarChart'
import { fmt, fmtMoney } from '../../../utils/fmt'

export default function GrowthEstimates({ quarterly, growthMetrics, forwardEstimates, reverseDcf, financialHistory, ai }) {
  const hasData = !!(quarterly || forwardEstimates || financialHistory)
  const fe = forwardEstimates || {}
  const gm = growthMetrics || {}
  const fh = financialHistory || {}

  return (
    <CollapsibleSection title="Growth & Forward Estimates" label="A" accentColor="#06b6d4" defaultOpen={hasData}>
      {/* Annual revenue + growth */}
      {fh.revenue && fh.revenue.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium mb-2" style={{ color: '#1a1a2e' }}>Annual Revenue</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                  <th className="text-left py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>Year</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>Revenue</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>Op Income</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>FCF</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>Op Margin</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>Net Margin</th>
                  <th className="text-right py-1 px-2 text-xs font-medium" style={{ color: '#6b7280' }}>D/E</th>
                </tr>
              </thead>
              <tbody>
                {fh.revenue.map((r, i) => {
                  const year = r.year
                  const oi = fh.operating_income?.find(x => x.year === year)
                  const fcf = fh.free_cash_flow?.find(x => x.year === year)
                  const om = fh.operating_margin?.find(x => x.year === year)
                  const nm = fh.net_margin?.find(x => x.year === year)
                  const de = fh.debt_to_equity?.find(x => x.year === year)

                  // YoY growth
                  const prevRev = fh.revenue[i + 1]
                  const revGrowth = prevRev?.value && r.value ? (r.value / prevRev.value - 1) : null

                  return (
                    <tr key={year} className="border-b" style={{ borderColor: '#f3f4f6' }}>
                      <td className="py-1 px-2 font-semibold" style={{ color: '#1a1a2e' }}>{year}</td>
                      <td className="py-1 px-2 text-right" style={{ color: '#1a1a2e' }}>
                        {fmtMoney(r.value)}
                        {revGrowth != null && (
                          <span className="ml-1 text-[10px]" style={{ color: revGrowth >= 0 ? '#00a562' : '#e5484d' }}>
                            {fmt(revGrowth, 'pctSigned')}
                          </span>
                        )}
                      </td>
                      <td className="py-1 px-2 text-right" style={{ color: '#1a1a2e' }}>{fmtMoney(oi?.value)}</td>
                      <td className="py-1 px-2 text-right" style={{ color: '#1a1a2e' }}>{fmtMoney(fcf?.value)}</td>
                      <td className="py-1 px-2 text-right" style={{ color: om?.value > 0.2 ? '#00a562' : '#1a1a2e' }}>
                        {om?.value != null ? `${(om.value * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-1 px-2 text-right" style={{ color: '#1a1a2e' }}>
                        {nm?.value != null ? `${(nm.value * 100).toFixed(1)}%` : '—'}
                      </td>
                      <td className="py-1 px-2 text-right" style={{ color: de?.value > 2 ? '#e5484d' : '#1a1a2e' }}>
                        {de?.value != null ? de.value.toFixed(2) : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {gm.revenue_cagr_3yr != null && (
            <div className="text-xs mt-2" style={{ color: '#6b7280' }}>
              3yr Revenue CAGR: <strong style={{ color: '#1a1a2e' }}>{fmt(gm.revenue_cagr_3yr, 'pctSigned')}</strong>
              {gm.revenue_cagr_5yr != null && (
                <span className="ml-3">5yr: <strong style={{ color: '#1a1a2e' }}>{fmt(gm.revenue_cagr_5yr, 'pctSigned')}</strong></span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Quarterly revenue chart */}
      {quarterly?.revenue && (
        <div className="mb-4">
          <QuarterlyBarChart
            data={quarterly.revenue}
            label="Quarterly Revenue"
            valueFormatter={v => v >= 1e9 ? `$${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v / 1e6).toFixed(0)}M` : `$${v}`}
          />
        </div>
      )}

      {/* EPS quarterly */}
      {quarterly?.eps && (
        <div className="mb-4">
          <QuarterlyBarChart data={quarterly.eps} label="Quarterly EPS" valueFormatter={v => `$${v?.toFixed(2)}`} />
        </div>
      )}

      {/* Forward estimates */}
      {(fe.eps_growth_1yr != null || fe.revenue_growth_trailing != null || fe.eps_fwd_vs_trailing != null) && (
        <div className="mb-4 p-3 rounded" style={{ backgroundColor: '#f7f8fa' }}>
          <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Forward Estimates</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {fe.eps_growth_1yr != null && (
              <div>
                <div style={{ color: '#6b7280' }}>EPS Growth (1yr)</div>
                <div className="font-semibold" style={{ color: fe.eps_growth_1yr > 0 ? '#00a562' : '#e5484d' }}>{fmt(fe.eps_growth_1yr, 'pctSigned')}</div>
              </div>
            )}
            {fe.eps_growth_quarterly != null && (
              <div>
                <div style={{ color: '#6b7280' }}>EPS Growth (QoQ)</div>
                <div className="font-semibold" style={{ color: fe.eps_growth_quarterly > 0 ? '#00a562' : '#e5484d' }}>{fmt(fe.eps_growth_quarterly, 'pctSigned')}</div>
              </div>
            )}
            {fe.revenue_growth_trailing != null && (
              <div>
                <div style={{ color: '#6b7280' }}>Revenue Growth (TTM)</div>
                <div className="font-semibold" style={{ color: fe.revenue_growth_trailing > 0 ? '#00a562' : '#e5484d' }}>{fmt(fe.revenue_growth_trailing, 'pctSigned')}</div>
              </div>
            )}
            {fe.eps_fwd_vs_trailing != null && (
              <div>
                <div style={{ color: '#6b7280' }}>Fwd vs Trail EPS</div>
                <div className="font-semibold" style={{ color: fe.eps_fwd_vs_trailing > 0 ? '#00a562' : '#e5484d' }}>{fmt(fe.eps_fwd_vs_trailing, 'pctSigned')}</div>
              </div>
            )}
            {fe.forward_pe != null && (
              <div>
                <div style={{ color: '#6b7280' }}>Forward P/E</div>
                <div className="font-semibold" style={{ color: '#1a1a2e' }}>{fe.forward_pe.toFixed(1)}</div>
              </div>
            )}
            {fe.trailing_pe != null && (
              <div>
                <div style={{ color: '#6b7280' }}>Trailing P/E</div>
                <div className="font-semibold" style={{ color: '#1a1a2e' }}>{fe.trailing_pe.toFixed(1)}</div>
              </div>
            )}
            {fe.peg_ratio != null && (
              <div>
                <div style={{ color: '#6b7280' }}>PEG Ratio</div>
                <div className="font-semibold" style={{ color: '#1a1a2e' }}>{fe.peg_ratio.toFixed(2)}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Earnings history */}
      {fe.earnings_history && fe.earnings_history.length > 0 && (
        <div className="mb-4">
          <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>
            Earnings History
            {fe.consecutive_beats != null && (
              <span className="ml-2 text-xs font-normal" style={{ color: '#00a562' }}>
                {fe.consecutive_beats} consecutive beats
              </span>
            )}
            {fe.beat_rate_4q != null && (
              <span className="ml-2 text-xs font-normal" style={{ color: '#6b7280' }}>
                ({(fe.beat_rate_4q * 100).toFixed(0)}% beat rate last 4Q)
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                  <th className="text-left py-1 px-2 font-medium" style={{ color: '#6b7280' }}>Date</th>
                  <th className="text-right py-1 px-2 font-medium" style={{ color: '#6b7280' }}>Estimate</th>
                  <th className="text-right py-1 px-2 font-medium" style={{ color: '#6b7280' }}>Actual</th>
                  <th className="text-right py-1 px-2 font-medium" style={{ color: '#6b7280' }}>Surprise</th>
                  <th className="text-center py-1 px-2 font-medium" style={{ color: '#6b7280' }}>Result</th>
                </tr>
              </thead>
              <tbody>
                {fe.earnings_history.map((q, i) => (
                  <tr key={i} className="border-b" style={{ borderColor: '#f3f4f6' }}>
                    <td className="py-1 px-2" style={{ color: '#1a1a2e' }}>
                      {q.date}
                      {q.upcoming && <span className="ml-1 text-[10px] px-1 rounded" style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>upcoming</span>}
                    </td>
                    <td className="py-1 px-2 text-right" style={{ color: '#6b7280' }}>${q.eps_estimate?.toFixed(2) ?? '—'}</td>
                    <td className="py-1 px-2 text-right font-semibold" style={{ color: '#1a1a2e' }}>
                      {q.eps_actual != null ? `$${q.eps_actual.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-1 px-2 text-right" style={{ color: q.surprise_pct > 0 ? '#00a562' : q.surprise_pct < 0 ? '#e5484d' : '#6b7280' }}>
                      {q.surprise_pct != null ? `${q.surprise_pct > 0 ? '+' : ''}${q.surprise_pct.toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-1 px-2 text-center">
                      {q.beat != null ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white" style={{
                          backgroundColor: q.beat ? '#00a562' : '#e5484d'
                        }}>
                          {q.beat ? 'BEAT' : 'MISS'}
                        </span>
                      ) : q.upcoming ? (
                        <span className="text-[10px]" style={{ color: '#6b7280' }}>pending</span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Implied vs Actual gap */}
      {reverseDcf?.implied_growth_rate != null && (gm.revenue_cagr_3yr != null || gm.revenue_cagr_5yr != null) && (
        <div className="p-3 rounded mb-4" style={{ backgroundColor: '#f7f8fa' }}>
          <div className="text-sm" style={{ color: '#1a1a2e' }}>
            Market implies <strong>{(reverseDcf.implied_growth_rate * 100).toFixed(1)}%</strong> growth.
            Historical CAGR is <strong>{((gm.revenue_cagr_3yr || gm.revenue_cagr_5yr) * 100).toFixed(1)}%</strong>.
            {(() => {
              const cagr = gm.revenue_cagr_3yr || gm.revenue_cagr_5yr
              const gap = reverseDcf.implied_growth_rate - cagr
              const undervalued = gap < 0
              return (
                <span style={{ color: undervalued ? '#00a562' : '#e5484d' }}>
                  {' '}Gap: {(gap * 100).toFixed(1)}% ({undervalued ? 'undervalued' : 'optimistic'})
                </span>
              )
            })()}
          </div>
        </div>
      )}

      {/* AI narrative */}
      {ai?.growth && (
        <div className="mt-3">
          <AiProvenance type="AI + data-derived" sourceBacked={true} />
          <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{ai.growth}</p>
        </div>
      )}

      {!hasData && !ai?.growth && (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>No growth data available.</p>
      )}
    </CollapsibleSection>
  )
}
