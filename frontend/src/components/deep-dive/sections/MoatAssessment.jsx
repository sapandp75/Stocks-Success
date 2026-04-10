import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MoatRatingBars from '../../charts/MoatRatingBars'

export default function MoatAssessment({ ai }) {
  const moat = ai?.moat_structured
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
