import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MoatRatingBars from '../../charts/MoatRatingBars'

function normalizeMoat(moat) {
  if (!moat) return null

  if (moat.factors || moat.overall || moat.trend) {
    return moat
  }

  const entries = Object.entries(moat).filter(([, value]) => {
    return value && typeof value === 'object' && ('score' in value || 'reasoning' in value)
  })

  if (entries.length === 0) return moat

  const factors = entries.map(([name, value]) => ({
    name: name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    score: value.score,
    max: 5,
    note: value.reasoning,
  }))

  const avgScore = factors.reduce((sum, factor) => sum + (factor.score || 0), 0) / factors.length
  const overall = avgScore >= 4 ? 'WIDE' : avgScore >= 2.5 ? 'NARROW' : 'NONE'

  return {
    overall,
    trend: moat.trend || null,
    factors,
  }
}

export default function MoatAssessment({ ai }) {
  const moat = normalizeMoat(ai?.moat_structured)
  const hasData = !!(moat?.factors || moat?.overall)

  return (
    <CollapsibleSection title="Moat Assessment" label="B" accentColor="#8b5cf6" defaultOpen={hasData} locked={!hasData}>
      {hasData ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={false} confidence="low" />

          {/* Overall moat badge */}
          {moat.overall && (
            <div className="flex items-center gap-3 mb-4">
              <span className="px-3 py-1 rounded text-sm font-bold text-white" style={{
                backgroundColor: moat.overall === 'WIDE' ? '#00a562' : moat.overall === 'NARROW' ? '#d97b0e' : '#6b7280'
              }}>
                {moat.overall} MOAT
              </span>
              {moat.trend && (
                <span className="text-xs font-medium" style={{
                  color: moat.trend === 'STRENGTHENING' ? '#00a562' : moat.trend === 'ERODING' ? '#e5484d' : '#6b7280'
                }}>
                  {moat.trend === 'STRENGTHENING' ? '↑' : moat.trend === 'ERODING' ? '↓' : '→'} {moat.trend}
                </span>
              )}
            </div>
          )}

          {/* Factor bars */}
          {moat.factors && <MoatRatingBars ratings={moat.factors} />}
        </>
      ) : (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>Run AI analysis to generate moat assessment.</p>
      )}
    </CollapsibleSection>
  )
}
