import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import MissingSeverity from '../MissingSeverity'

export default function BearCase({ ai }) {
  const stock = ai?.bear_case_stock
  const business = ai?.bear_case_business
  const hasAi = !!(stock || business)

  return (
    <CollapsibleSection title="Bear Case" number="3" accentColor="#e5484d" defaultOpen={hasAi} locked={!hasAi}>
      {hasAi ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 rounded" style={{ backgroundColor: '#fef2f2', borderLeft: '3px solid #e5484d' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#e5484d' }}>Bear on Stock</div>
              <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{stock || '—'}</p>
            </div>
            <div className="p-3 rounded" style={{ backgroundColor: '#fef2f2', borderLeft: '3px solid #991b1b' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#991b1b' }}>Bear on Business</div>
              <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{business || '—'}</p>
            </div>
          </div>
        </>
      ) : (
        <MissingSeverity severity="critical" label="Bear case not generated — run AI analysis first" />
      )}
    </CollapsibleSection>
  )
}
