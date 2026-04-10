import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'

export default function OpportunitiesThreats({ ai }) {
  const opps = ai?.opportunities
  const threats = ai?.threats
  const hasData = !!(opps || threats)

  return (
    <CollapsibleSection title="Opportunities & Threats" label="C" accentColor="#14b8a6" defaultOpen={hasData} locked={!hasData}>
      {hasData ? (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={false} confidence="low" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Opportunities */}
            <div className="p-3 rounded" style={{ backgroundColor: '#f0fdf4', borderLeft: '3px solid #00a562' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#00a562' }}>Opportunities</div>
              {typeof opps === 'string' ? (
                <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{opps}</p>
              ) : Array.isArray(opps) ? (
                <ul className="text-sm space-y-1" style={{ color: '#1a1a2e' }}>
                  {opps.map((o, i) => <li key={i}>• {typeof o === 'string' ? o : o.description || o.text || JSON.stringify(o)}</li>)}
                </ul>
              ) : (
                <p className="text-sm italic" style={{ color: '#6b7280' }}>—</p>
              )}
            </div>

            {/* Threats */}
            <div className="p-3 rounded" style={{ backgroundColor: '#fef2f2', borderLeft: '3px solid #e5484d' }}>
              <div className="font-semibold text-sm mb-2" style={{ color: '#e5484d' }}>Threats</div>
              {typeof threats === 'string' ? (
                <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{threats}</p>
              ) : Array.isArray(threats) ? (
                <ul className="text-sm space-y-1" style={{ color: '#1a1a2e' }}>
                  {threats.map((t, i) => <li key={i}>• {typeof t === 'string' ? t : t.description || t.text || JSON.stringify(t)}</li>)}
                </ul>
              ) : (
                <p className="text-sm italic" style={{ color: '#6b7280' }}>—</p>
              )}
            </div>
          </div>
        </>
      ) : (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>Run AI analysis to generate opportunities & threats.</p>
      )}
    </CollapsibleSection>
  )
}
