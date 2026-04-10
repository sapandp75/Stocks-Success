import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'

export default function FirstImpression({ ai, ticker }) {
  const text = ai?.first_impression
  const hasAi = !!text

  return (
    <CollapsibleSection title="First Impression" number="2" accentColor="#6366f1" defaultOpen={hasAi} locked={!hasAi}>
      {hasAi ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={false} />
          <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{text}</p>
        </>
      ) : (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>
          No AI analysis yet. Run: python bridge/deep_dive_worker.py {ticker} --post
        </p>
      )}
    </CollapsibleSection>
  )
}
