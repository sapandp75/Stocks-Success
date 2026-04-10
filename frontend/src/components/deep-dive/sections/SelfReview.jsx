import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'

export default function SelfReview({ ai }) {
  const text = ai?.self_review
  const hasAi = !!text

  return (
    <CollapsibleSection title="Self-Review" number="7" accentColor="#f59e0b" defaultOpen={hasAi} locked={!hasAi}>
      {hasAi ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={false} confidence="low" />
          <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{text}</p>
        </>
      ) : (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>
          Bias check vs first impression, gap check, pre-mortem, 'what would make me wrong' — awaiting AI analysis.
        </p>
      )}
    </CollapsibleSection>
  )
}
