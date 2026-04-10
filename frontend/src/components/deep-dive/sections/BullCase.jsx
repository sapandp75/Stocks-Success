import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MissingSeverity from '../MissingSeverity'

export default function BullCase({ ai }) {
  const rebuttal = ai?.bull_case_rebuttal
  const upside = ai?.bull_case_upside
  const hasAi = !!(rebuttal || upside)

  return (
    <CollapsibleSection title="Bull Case" number="4" accentColor="#00a562" defaultOpen={hasAi} locked={!hasAi}>
      {hasAi ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 rounded" style={{ backgroundColor: '#dcfce7', borderLeft: '3px solid #00a562' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#00a562' }}>Bear Rebuttal</div>
              <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{rebuttal || '—'}</p>
            </div>
            <div className="p-3 rounded" style={{ backgroundColor: '#dcfce7', borderLeft: '3px solid #15803d' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#15803d' }}>Unpriced Upside</div>
              <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{upside || '—'}</p>
            </div>
          </div>
        </>
      ) : (
        <MissingSeverity severity="critical" label="Bull case not generated — run AI analysis first" />
      )}
    </CollapsibleSection>
  )
}
