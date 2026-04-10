import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MissingSeverity from '../MissingSeverity'
import DcfCalculator from '../../DcfCalculator'
import SensitivityMatrix from '../../SensitivityMatrix'
import PeerTable from '../../PeerTable'
import AnalystBar from '../../AnalystBar'
import PriceTargetBar from '../../charts/PriceTargetBar'

export default function Valuation({ data, ai }) {
  const price = data?.fundamentals?.price
  const reverseDcf = data?.reverse_dcf
  const forwardDcf = data?.forward_dcf
  const f = data?.fundamentals || {}
  const hasValuationData = !!(reverseDcf || forwardDcf || data?.peers)

  if (!hasValuationData && !ai?.valuation) {
    return (
      <CollapsibleSection title="Valuation" number="5" accentColor="#d97b0e" defaultOpen>
        <MissingSeverity severity="critical" label="Valuation data unavailable" />
      </CollapsibleSection>
    )
  }

  // Build price target sources for PriceTargetBar
  const targetSources = []
  if (data?.external_targets) {
    Object.entries(data.external_targets).forEach(([name, t]) => {
      if (t?.low != null || t?.high != null) {
        targetSources.push({ name, low: t.low, mean: t.mean, high: t.high })
      }
    })
  }
  if (forwardDcf?.base) {
    targetSources.push({ name: 'DCF Base', mean: forwardDcf.base.intrinsic_value_per_share })
  }

  return (
    <CollapsibleSection title="Valuation" number="5" accentColor="#d97b0e" defaultOpen>
      {/* Reverse DCF first — always */}
      {reverseDcf && (
        <div className="mb-4 p-3 rounded" style={{ backgroundColor: '#f7f8fa' }}>
          <div className="font-semibold text-sm mb-1" style={{ color: '#1a1a2e' }}>Reverse DCF — What does the market price imply?</div>
          <div className="text-sm" style={{ color: '#6b7280' }}>
            Implied growth rate: <span className="font-bold" style={{ color: '#1a1a2e' }}>{(reverseDcf.implied_growth_rate * 100).toFixed(1)}%</span>
          </div>
          {reverseDcf.interpretation && (
            <div className="text-sm mt-1" style={{ color: '#6b7280' }}>{reverseDcf.interpretation}</div>
          )}
        </div>
      )}

      {/* Forward DCF 3 scenarios */}
      {forwardDcf && (
        <div className="mb-4">
          <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Forward DCF — 3 Scenarios</div>
          <div className="grid grid-cols-3 gap-3">
            {['bear', 'base', 'bull'].map(s => {
              const d = forwardDcf[s]
              if (!d) return null
              const colors = { bear: '#e5484d', base: '#1a1a2e', bull: '#00a562' }
              const abovePrice = price && d.intrinsic_value_per_share > price
              return (
                <div key={s} className="p-3 rounded border" style={{ borderColor: '#e2e4e8' }}>
                  <div className="font-semibold text-xs capitalize mb-1" style={{ color: colors[s] }}>{s}</div>
                  <div className="text-xl font-bold" style={{ color: abovePrice ? '#00a562' : '#e5484d' }}>
                    ${d.intrinsic_value_per_share?.toFixed(0)}
                  </div>
                  {price && (
                    <div className="text-xs font-semibold mt-1" style={{ color: abovePrice ? '#00a562' : '#e5484d' }}>
                      {abovePrice ? '+' : ''}{((d.intrinsic_value_per_share - price) / price * 100).toFixed(0)}% vs current
                    </div>
                  )}
                  {d.inputs && (
                    <div className="text-[10px] mt-1 space-y-0.5" style={{ color: '#6b7280' }}>
                      <div>Yr 1-5: {(d.inputs.growth_1_5 * 100).toFixed(0)}% · Yr 6-10: {((d.inputs.growth_6_10 || 0) * 100).toFixed(0)}% · Terminal: {(d.inputs.terminal_growth * 100).toFixed(1)}%</div>
                    </div>
                  )}
                  <div className="text-[10px] mt-1" style={{ color: '#6b7280' }}>
                    TV: {(d.terminal_value_pct * 100).toFixed(0)}%
                    {d.terminal_value_warning && <span style={{ color: '#d97b0e' }}> (exceeds 50%)</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Interactive DCF */}
      <div className="mb-4">
        <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Interactive DCF Calculator</div>
        <DcfCalculator defaults={{
          starting_fcf: data?.fcf_3yr_avg || f.free_cash_flow,
          growth_1_5: 0.12,
          growth_6_10: 0.07,
          shares: f.shares_outstanding,
          net_debt: data?.net_debt || 0,
        }} />
      </div>

      {/* Sensitivity Matrix */}
      {data?.sensitivity_matrix && (
        <div className="mb-4">
          <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Sensitivity Matrix</div>
          <SensitivityMatrix matrix={data.sensitivity_matrix} currentPrice={price} />
        </div>
      )}

      {/* Price targets */}
      {targetSources.length > 0 && (
        <PriceTargetBar sources={targetSources} currentPrice={price} />
      )}

      {/* Peers + Analyst */}
      {data?.peers && <PeerTable data={data.peers} ticker={data.ticker} />}
      {data?.analyst && <AnalystBar data={data.analyst} currentPrice={price} />}

      {/* AI narrative */}
      {ai?.valuation && (
        <div className="mt-4">
          <AiProvenance type="AI + data-derived" sourceBacked={true} />
          <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{ai.valuation}</p>
        </div>
      )}
    </CollapsibleSection>
  )
}
