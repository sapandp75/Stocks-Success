import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MissingSeverity from '../MissingSeverity'
import EntryGrid from '../../EntryGrid'

export default function VerdictAction({ ai, memoTrust }) {
  const hasAi = !!(ai?.verdict)

  return (
    <CollapsibleSection title="Verdict & Action Plan" number="8" accentColor="#00a562" defaultOpen={hasAi} locked={!hasAi}>
      {hasAi ? (
        <div className="space-y-4">
          <AiProvenance
            type="AI synthesis"
            sourceBacked={true}
            confidence={ai.conviction === 'HIGH' ? 'high' : ai.conviction === 'MODERATE' ? 'medium' : 'low'}
          />

          {/* Memo trust summary */}
          {memoTrust && memoTrust.state !== 'Complete' && (
            <div className="text-xs p-2 rounded" style={{ backgroundColor: '#fffbeb', color: '#92400e' }}>
              This verdict is based on {memoTrust.state?.toLowerCase()} analysis
              {memoTrust.criticalGaps?.length > 0 && ` (missing: ${memoTrust.criticalGaps.join(', ')})`}
            </div>
          )}

          {/* Verdict + Conviction */}
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

          {/* Entry Grid */}
          <div>
            <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Entry Grid</div>
            <EntryGrid grid={ai.entry_grid} />
          </div>

          {/* Exit Playbook */}
          {ai.exit_playbook && (
            <div>
              <div className="font-semibold text-sm mb-1" style={{ color: '#1a1a2e' }}>Exit Playbook</div>
              <p className="text-sm whitespace-pre-wrap" style={{ color: '#6b7280' }}>{ai.exit_playbook}</p>
            </div>
          )}

          {/* Next review */}
          {ai.next_review_date && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: '#6b7280' }}>Next review:</span>
              <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: '#f3f4f6', color: '#1a1a2e' }}>
                {ai.next_review_date}
              </span>
            </div>
          )}
        </div>
      ) : (
        <MissingSeverity severity="critical" label="Verdict not generated — run AI analysis to produce decision output" />
      )}
    </CollapsibleSection>
  )
}
