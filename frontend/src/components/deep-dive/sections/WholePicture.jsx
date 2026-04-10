import CollapsibleSection from '../../CollapsibleSection'
import AiProvenance from '../AiProvenance'
import InsiderPanel from '../../InsiderPanel'
import InstitutionalPanel from '../../InstitutionalPanel'

export default function WholePicture({ ai, fundFlow, insiderActivity, institutional, sharesOutstanding }) {
  const hasAi = !!(ai?.whole_picture || ai?.smart_money)
  const hasData = !!(fundFlow || insiderActivity || institutional)
  const hasContent = hasAi || hasData

  return (
    <CollapsibleSection title="Whole Picture" number="6" accentColor="#8b5cf6" defaultOpen={hasContent}>
      {/* AI whole picture narrative */}
      {ai?.whole_picture && (
        <>
          <AiProvenance type="AI synthesis" sourceBacked={true} />
          <p className="text-sm whitespace-pre-wrap mb-4" style={{ color: '#1a1a2e' }}>{ai.whole_picture}</p>
        </>
      )}

      {/* Fund flow summary */}
      {fundFlow && (
        <div className="p-3 rounded border mb-3" style={{ borderColor: '#e2e4e8' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-sm" style={{ color: '#1a1a2e' }}>Fund Flow (13F)</span>
            {fundFlow.net_flow != null && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold text-white" style={{
                backgroundColor: fundFlow.net_flow > 0 ? '#00a562' : fundFlow.net_flow < 0 ? '#e5484d' : '#6b7280'
              }}>
                {fundFlow.net_flow > 0 ? 'NET BUY' : fundFlow.net_flow < 0 ? 'NET SELL' : 'NEUTRAL'}
              </span>
            )}
          </div>
          <div className="flex gap-4 text-xs" style={{ color: '#6b7280' }}>
            {fundFlow.new_positions != null && <span>New positions: {fundFlow.new_positions}</span>}
            {fundFlow.exits != null && <span>Exits: {fundFlow.exits}</span>}
          </div>
          {/* Top holders */}
          {(fundFlow.current_holders || fundFlow.top_holders)?.length > 0 && (
            <table className="w-full text-xs mt-2">
              <thead>
                <tr style={{ color: '#6b7280' }}>
                  <th className="text-left font-medium pb-1">Fund</th>
                  <th className="text-right font-medium pb-1">Shares</th>
                  <th className="text-right font-medium pb-1">Value</th>
                  <th className="text-right font-medium pb-1">% Out</th>
                  <th className="text-left font-medium pb-1 pl-2">Type</th>
                </tr>
              </thead>
              <tbody>
                {(fundFlow.current_holders || fundFlow.top_holders).slice(0, 8).map((h, i) => {
                  const val = h.value_usd || h.value
                  return (
                    <tr key={i} style={{ color: '#1a1a2e' }}>
                      <td className="py-0.5">{h.fund_name || h.name || h.fund || '—'}</td>
                      <td className="py-0.5 text-right">{h.shares?.toLocaleString() || '—'}</td>
                      <td className="py-0.5 text-right" style={{ color: '#6b7280' }}>
                        {val != null ? (val >= 1e9 ? `$${(val / 1e9).toFixed(1)}B` : val >= 1e6 ? `$${(val / 1e6).toFixed(0)}M` : `$${val.toLocaleString()}`) : '—'}
                      </td>
                      <td className="py-0.5 text-right" style={{ color: '#6b7280' }}>
                        {h.shares && sharesOutstanding ? `${(h.shares / sharesOutstanding * 100).toFixed(2)}%` : '—'}
                      </td>
                      <td className="py-0.5 pl-2 text-[10px]" style={{ color: '#6b7280' }}>{h.fund_type || h.type || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
          {fundFlow.holder_type_breakdown && (
            <div className="flex gap-3 mt-2 text-[10px]" style={{ color: '#6b7280' }}>
              {Object.entries(fundFlow.holder_type_breakdown).map(([type, count]) => (
                <span key={type}>{type}: {count}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Existing panels */}
      {insiderActivity && <InsiderPanel data={insiderActivity} />}
      {institutional && <InstitutionalPanel data={institutional} />}

      {/* AI smart money interpretation */}
      {ai?.smart_money && (
        <div className="mt-3">
          <AiProvenance type="AI synthesis" sourceBacked={true} />
          <p className="text-sm whitespace-pre-wrap" style={{ color: '#1a1a2e' }}>{ai.smart_money}</p>
        </div>
      )}

      {!hasContent && (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>
          Sector theme, smart money (13F), management quality — awaiting AI analysis.
        </p>
      )}
    </CollapsibleSection>
  )
}
