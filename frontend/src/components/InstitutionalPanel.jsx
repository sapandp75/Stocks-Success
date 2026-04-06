export default function InstitutionalPanel({ data }) {
  if (!data) return null

  const ownership = data.institutional_ownership ?? data.ownership_pct
  const trend = data.trend || 'STABLE'
  const trendColors = {
    ACCUMULATING: '#00a562',
    DISTRIBUTING: '#d97b0e',
    STABLE: '#6b7280',
  }
  const holders = (data.top_holders || []).slice(0, 5)

  return (
    <div className="mt-4 p-3 rounded border" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center gap-3 mb-3">
        <span className="font-semibold text-sm" style={{ color: '#1a1a2e' }}>Institutional Holdings</span>
        {ownership != null && (
          <span className="text-lg font-bold" style={{ color: '#1a1a2e' }}>
            {(ownership * 100).toFixed(1)}%
          </span>
        )}
        <span
          className="px-2 py-0.5 rounded text-[10px] font-bold text-white"
          style={{ backgroundColor: trendColors[trend] || '#6b7280' }}
        >
          {trend}
        </span>
      </div>
      {holders.length > 0 && (
        <table className="w-full text-xs">
          <thead>
            <tr style={{ color: '#6b7280' }}>
              <th className="text-left font-medium pb-1">Holder</th>
              <th className="text-right font-medium pb-1">% Ownership</th>
            </tr>
          </thead>
          <tbody>
            {holders.map((h, i) => (
              <tr key={i} style={{ color: '#1a1a2e' }}>
                <td className="py-0.5 truncate" style={{ maxWidth: '200px' }}>{h.name || h.holder}</td>
                <td className="py-0.5 text-right">
                  {h.ownership_pct != null ? `${(h.ownership_pct * 100).toFixed(2)}%` : h.pct != null ? `${h.pct.toFixed(2)}%` : '--'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
