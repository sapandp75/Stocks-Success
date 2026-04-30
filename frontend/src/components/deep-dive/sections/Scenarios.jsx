import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import ScenarioRangeBar from '../../charts/ScenarioRangeBar'

function parseProbability(value) {
  if (value == null) return null
  if (typeof value === 'number') return value > 1 ? value / 100 : value
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed.endsWith('%')) {
      const num = Number(trimmed.slice(0, -1))
      return Number.isFinite(num) ? num / 100 : null
    }
    const num = Number(trimmed)
    return Number.isFinite(num) ? (num > 1 ? num / 100 : num) : null
  }
  return null
}

function normalizeScenario(s, i) {
  if (!s || typeof s !== 'object') return null
  return {
    name: s.name || s.label || s.scenario || ['Worst', 'Base', 'Best'][i] || `Scenario ${i + 1}`,
    target_price: s.target_price ?? s.price ?? null,
    probability: parseProbability(s.probability),
    rationale: s.rationale || s.note || null,
  }
}

export default function Scenarios({ ai, currentPrice }) {
  const rawScenarios = ai?.scenarios
  const scenarios = rawScenarios
    ? (Array.isArray(rawScenarios)
        ? rawScenarios.map(normalizeScenario).filter(Boolean)
        : [rawScenarios.worst, rawScenarios.base, rawScenarios.best].map(normalizeScenario).filter(Boolean))
    : []
  const hasData = scenarios.length > 0

  // Extract scenario values
  let worst, base, best, weightedTarget
  if (scenarios.length > 0) {
    const sorted = [...scenarios].sort((a, b) => (a.target_price || 0) - (b.target_price || 0))
    worst = sorted[0]?.target_price
    best = sorted[sorted.length - 1]?.target_price
    base = sorted.length >= 2 ? sorted[Math.floor(sorted.length / 2)]?.target_price : worst
    weightedTarget = scenarios.reduce((sum, s) => sum + (s.target_price || 0) * (s.probability || 0.33), 0)
  }

  const scenarioRows = scenarios

  const rowColors = { worst: '#e5484d', bear: '#e5484d', base: '#d97b0e', best: '#00a562', bull: '#00a562' }

  return (
    <CollapsibleSection title="Scenarios" label="D" accentColor="#64748b" defaultOpen={hasData} locked={!hasData}>
      {hasData ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium" />

          {/* Range bar */}
          {worst != null && best != null && (
            <ScenarioRangeBar worst={worst} base={base} best={best} currentPrice={currentPrice} weightedTarget={weightedTarget} />
          )}

          {/* Scenario table */}
          {scenarioRows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                    {['Scenario', 'Target', 'Probability', 'Upside/Downside'].map(h => (
                      <th key={h} className="text-left py-2 px-2 font-medium text-xs" style={{ color: '#6b7280' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {scenarioRows.map((s, i) => {
                    const name = s.name || ['Worst', 'Base', 'Best'][i] || `Scenario ${i + 1}`
                    const color = rowColors[name.toLowerCase()] || '#1a1a2e'
                    const upside = currentPrice && s.target_price ? ((s.target_price - currentPrice) / currentPrice * 100) : null
                    return (
                      <tr key={i} className="border-b" style={{ borderColor: '#e2e4e8' }}>
                        <td className="py-2 px-2 font-semibold capitalize" style={{ color }}>{name}</td>
                        <td className="py-2 px-2" style={{ color: '#1a1a2e' }}>${s.target_price?.toFixed(0) || '—'}</td>
                        <td className="py-2 px-2" style={{ color: '#6b7280' }}>
                          {s.probability != null ? `${(s.probability * 100).toFixed(0)}%` : '—'}
                          <span className="text-[10px] ml-1 italic" style={{ color: '#9ca3af' }}>
                            {s.probability != null ? '(judgment)' : ''}
                          </span>
                        </td>
                        <td className="py-2 px-2 font-medium" style={{ color: upside > 0 ? '#00a562' : '#e5484d' }}>
                          {upside != null ? `${upside > 0 ? '+' : ''}${upside.toFixed(0)}%` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>Run AI analysis to generate scenario analysis.</p>
      )}
    </CollapsibleSection>
  )
}
