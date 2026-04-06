import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDeepDive } from '../api'
import CollapsibleSection from '../components/CollapsibleSection'
import DcfCalculator from '../components/DcfCalculator'
import SensitivityMatrix from '../components/SensitivityMatrix'
import EntryGrid from '../components/EntryGrid'
import ResearchPanel from '../components/ResearchPanel'
import TechnicalPanel from '../components/TechnicalPanel'
import SparklineGrid from '../components/SparklineGrid'
import PeerTable from '../components/PeerTable'
import AnalystBar from '../components/AnalystBar'
import InsiderPanel from '../components/InsiderPanel'
import InstitutionalPanel from '../components/InstitutionalPanel'
import AiAnalyzeButton from '../components/AiAnalyzeButton'

function MetricCell({ label, value, color }) {
  return (
    <div>
      <div className="text-[11px]" style={{ color: '#6b7280' }}>{label}</div>
      <div className="font-semibold text-sm" style={{ color: color || '#1a1a2e' }}>{value ?? '—'}</div>
    </div>
  )
}

function fmt(val, type = 'pct') {
  if (val == null) return '—'
  if (type === 'pct') return `${(val * 100).toFixed(1)}%`
  if (type === 'pe') return val.toFixed(1)
  if (type === 'money') {
    if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
    return `$${val.toFixed(0)}`
  }
  if (type === 'ratio') return val.toFixed(2)
  return String(val)
}

function AiText({ text, placeholder }) {
  if (text) return <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{text}</p>
  return <p className="text-sm italic" style={{ color: '#6b7280' }}>{placeholder}</p>
}

export default function DeepDivePage() {
  const { ticker: urlTicker } = useParams()
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const loadData = (t) => {
    if (!t) return
    setLoading(true)
    getDeepDive(t).then(setData).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => {
    if (urlTicker) {
      setInput(urlTicker.toUpperCase())
      loadData(urlTicker)
    }
  }, [urlTicker])

  const handleLoad = () => {
    if (input) navigate(`/deep-dive/${input}`)
  }

  const f = data?.fundamentals || {}
  const ai = data?.ai_analysis
  const price = f.price

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Deep Dive</h1>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 text-sm w-40"
          style={{ borderColor: '#e2e4e8' }}
          placeholder="Ticker (e.g. AAPL)"
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === 'Enter' && handleLoad()}
        />
        <button
          onClick={handleLoad}
          className="px-4 py-2 rounded text-sm font-medium text-white"
          style={{ backgroundColor: '#00a562' }}
        >
          Load
        </button>
      </div>

      {loading && <p style={{ color: '#6b7280' }}>Loading deep dive data...</p>}

      {data && !ai && (
        <AiAnalyzeButton ticker={data.ticker} onComplete={() => loadData(data.ticker)} />
      )}

      {data && (
        <div className="space-y-3">
          {/* Section 1: Data Snapshot */}
          <CollapsibleSection title="Data Snapshot" number="1" accentColor="#3b82f6" defaultOpen={true}>
            <div className="flex items-center gap-2 mb-3">
              <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{f.name}</span>
              <span className="text-sm" style={{ color: '#6b7280' }}>({data.ticker})</span>
              <span className="text-sm" style={{ color: '#6b7280' }}>· {f.sector} · {f.industry}</span>
            </div>
            {data.data_quality && (
              <div className="text-xs mb-3 flex gap-3" style={{ color: '#6b7280' }}>
                <span>Source: {data.data_quality.source}</span>
                <span>Completeness: {(data.data_quality.completeness * 100).toFixed(0)}%</span>
                {data.data_quality.missing_fields.length > 0 && (
                  <span style={{ color: '#d97b0e' }}>Missing: {data.data_quality.missing_fields.join(', ')}</span>
                )}
              </div>
            )}
            <div className="grid grid-cols-4 md:grid-cols-6 gap-3">
              <MetricCell label="Price" value={`$${price?.toFixed(2)}`} />
              <MetricCell label="Mkt Cap" value={fmt(f.market_cap, 'money')} />
              <MetricCell label="Fwd P/E" value={fmt(f.forward_pe, 'pe')} />
              <MetricCell label="Trail P/E" value={fmt(f.trailing_pe, 'pe')} />
              <MetricCell label="Rev Growth" value={fmt(f.revenue_growth)} color={f.revenue_growth > 0 ? '#00a562' : '#e5484d'} />
              <MetricCell label="Op Margin" value={fmt(f.operating_margin)} />
              <MetricCell label="Gross Margin" value={fmt(f.gross_margin)} />
              <MetricCell label="FCF" value={fmt(f.free_cash_flow, 'money')} />
              <MetricCell label="FCF 3yr Avg" value={data.fcf_3yr_avg ? fmt(data.fcf_3yr_avg, 'money') : '—'} />
              <MetricCell label="D/E" value={fmt(f.debt_to_equity, 'ratio')} />
              <MetricCell label="Net Debt" value={data.net_debt ? fmt(data.net_debt, 'money') : '—'} />
              <MetricCell label="SBC" value={data.sbc ? fmt(data.sbc, 'money') : '—'} />
              <MetricCell label="SBC Adjusted" value={data.sbc_adjusted ? 'Yes' : 'No'} color={data.sbc_adjusted ? '#d97b0e' : '#6b7280'} />
              <MetricCell label="Short %" value={fmt(f.short_percent)} />
              <MetricCell label="Drop from High" value={fmt(f.drop_from_high)} color={f.drop_from_high > 0.2 ? '#e5484d' : '#6b7280'} />
              <MetricCell label="Beta" value={f.beta?.toFixed(2)} />
              <MetricCell label="ROE" value={fmt(f.return_on_equity)} />
              <MetricCell label="Div Yield" value={f.dividend_yield ? fmt(f.dividend_yield) : '—'} />
            </div>
            {data.technicals && <TechnicalPanel technicals={data.technicals} />}
            {data.financial_history && <SparklineGrid data={data.financial_history} />}
          </CollapsibleSection>

          {/* Section 2: First Impression */}
          <CollapsibleSection title="First Impression" number="2" accentColor="#6366f1" defaultOpen={!!ai}>
            <AiText
              text={ai?.first_impression}
              placeholder="No AI analysis yet. Run: python bridge/deep_dive_worker.py {ticker} --post"
            />
          </CollapsibleSection>

          {/* Section 3: Bear Case (FIRST per spec) */}
          <CollapsibleSection title="Bear Case" number="3" accentColor="#e5484d" defaultOpen={!!ai}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded" style={{ backgroundColor: '#fef2f2', borderLeft: '3px solid #e5484d' }}>
                <div className="font-semibold text-sm mb-2" style={{ color: '#e5484d' }}>Bear on Stock</div>
                <AiText text={ai?.bear_case_stock} placeholder="Awaiting AI analysis..." />
              </div>
              <div className="p-3 rounded" style={{ backgroundColor: '#fef2f2', borderLeft: '3px solid #991b1b' }}>
                <div className="font-semibold text-sm mb-2" style={{ color: '#991b1b' }}>Bear on Business</div>
                <AiText text={ai?.bear_case_business} placeholder="Awaiting AI analysis..." />
              </div>
            </div>
          </CollapsibleSection>

          {/* Section 4: Bull Case */}
          <CollapsibleSection title="Bull Case" number="4" accentColor="#00a562" defaultOpen={!!ai}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded" style={{ backgroundColor: '#dcfce7', borderLeft: '3px solid #00a562' }}>
                <div className="font-semibold text-sm mb-2" style={{ color: '#00a562' }}>Bear Rebuttal</div>
                <AiText text={ai?.bull_case_rebuttal} placeholder="Each bull point should address a specific bear point..." />
              </div>
              <div className="p-3 rounded" style={{ backgroundColor: '#dcfce7', borderLeft: '3px solid #15803d' }}>
                <div className="font-semibold text-sm mb-2" style={{ color: '#15803d' }}>Unpriced Upside</div>
                <AiText text={ai?.bull_case_upside} placeholder="Awaiting AI analysis..." />
              </div>
            </div>
          </CollapsibleSection>

          {/* Section 5: Valuation (Reverse DCF first, then Forward, then Interactive, then Sensitivity) */}
          <CollapsibleSection title="Valuation" number="5" accentColor="#d97b0e" defaultOpen={true}>
            {/* Reverse DCF first per spec */}
            {data.reverse_dcf && (
              <div className="mb-4 p-3 rounded" style={{ backgroundColor: '#f7f8fa' }}>
                <div className="font-semibold text-sm mb-1" style={{ color: '#1a1a2e' }}>Reverse DCF — What does the market price imply?</div>
                <div className="text-sm" style={{ color: '#6b7280' }}>
                  Implied growth rate: <span className="font-bold" style={{ color: '#1a1a2e' }}>{(data.reverse_dcf.implied_growth_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="text-sm mt-1" style={{ color: '#6b7280' }}>{data.reverse_dcf.interpretation}</div>
              </div>
            )}

            {/* Forward DCF 3 scenarios */}
            {data.forward_dcf && (
              <div className="mb-4">
                <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Forward DCF — 3 Scenarios</div>
                <div className="grid grid-cols-3 gap-3">
                  {['bear', 'base', 'bull'].map(s => {
                    const d = data.forward_dcf[s]
                    if (!d) return null
                    const colors = { bear: '#e5484d', base: '#1a1a2e', bull: '#00a562' }
                    const abovePrice = price && d.intrinsic_value_per_share > price
                    return (
                      <div key={s} className="p-3 rounded border" style={{ borderColor: '#e2e4e8' }}>
                        <div className="font-semibold text-xs capitalize mb-1" style={{ color: colors[s] }}>{s}</div>
                        <div className="text-xl font-bold" style={{ color: abovePrice ? '#00a562' : '#e5484d' }}>
                          ${d.intrinsic_value_per_share}
                        </div>
                        <div className="text-[10px] mt-1" style={{ color: '#6b7280' }}>
                          TV: {(d.terminal_value_pct * 100).toFixed(0)}%
                          {d.terminal_value_warning && <span style={{ color: '#d97b0e' }}> (exceeds 50%)</span>}
                        </div>
                        {price && (
                          <div className="text-[10px]" style={{ color: abovePrice ? '#00a562' : '#e5484d' }}>
                            {abovePrice ? '+' : ''}{((d.intrinsic_value_per_share - price) / price * 100).toFixed(0)}% vs current
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Interactive DCF Calculator */}
            <div className="mb-4">
              <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Interactive DCF Calculator</div>
              <DcfCalculator defaults={{
                starting_fcf: data.fcf_3yr_avg || f.free_cash_flow,
                growth_1_5: 0.12,
                growth_6_10: 0.07,
                shares: f.shares_outstanding,
                net_debt: data.net_debt || 0,
              }} />
            </div>

            {/* Sensitivity Matrix */}
            {data.sensitivity_matrix && (
              <div>
                <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Sensitivity Matrix</div>
                <SensitivityMatrix matrix={data.sensitivity_matrix} currentPrice={price} />
              </div>
            )}
            {data.peers && <PeerTable data={data.peers} ticker={data.ticker} />}
            {data.analyst && <AnalystBar data={data.analyst} currentPrice={price} />}
          </CollapsibleSection>

          {/* Section 6: Whole Picture */}
          <CollapsibleSection title="Whole Picture" number="6" accentColor="#8b5cf6" defaultOpen={!!ai}>
            <AiText
              text={ai?.whole_picture}
              placeholder="Sector theme, smart money (13F), management quality, customer evidence — awaiting AI analysis."
            />
            {data.insider_activity && <InsiderPanel data={data.insider_activity} />}
            {data.institutional && <InstitutionalPanel data={data.institutional} />}
          </CollapsibleSection>

          {/* Section 7: Self-Review */}
          <CollapsibleSection title="Self-Review" number="7" accentColor="#f59e0b" defaultOpen={!!ai}>
            <AiText
              text={ai?.self_review}
              placeholder="Bias check vs first impression, gap check, pre-mortem, 'what would make me wrong' — awaiting AI analysis."
            />
          </CollapsibleSection>

          {/* Section 8: Verdict */}
          <CollapsibleSection title="Verdict" number="8" accentColor="#00a562" defaultOpen={!!ai}>
            {ai ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div>
                    <div className="text-xs" style={{ color: '#6b7280' }}>Verdict</div>
                    <div className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{ai.verdict}</div>
                  </div>
                  <div>
                    <div className="text-xs" style={{ color: '#6b7280' }}>Conviction</div>
                    <span className="px-2 py-0.5 rounded text-sm font-bold text-white" style={{
                      backgroundColor: ai.conviction === 'HIGH' ? '#00a562' : ai.conviction === 'MODERATE' ? '#d97b0e' : '#6b7280'
                    }}>
                      {ai.conviction}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Entry Grid</div>
                  <EntryGrid grid={ai.entry_grid} />
                </div>

                {ai.exit_playbook && (
                  <div>
                    <div className="font-semibold text-sm mb-1" style={{ color: '#1a1a2e' }}>Exit Playbook</div>
                    <p className="text-sm whitespace-pre-wrap" style={{ color: '#6b7280' }}>{ai.exit_playbook}</p>
                  </div>
                )}
              </div>
            ) : (
              <AiText text={null} placeholder="Bucket assignment, conviction, entry grid, exit playbook — awaiting AI analysis." />
            )}
          </CollapsibleSection>

          {/* Section 9: Research Context */}
          <CollapsibleSection title="Research Context" number="9" accentColor="#3b82f6" defaultOpen={false}>
            <ResearchPanel ticker={data.ticker} initialData={data.research_context} />
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}
