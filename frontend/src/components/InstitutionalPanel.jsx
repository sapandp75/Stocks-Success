export default function InstitutionalPanel({ data }) {
  if (!data) return null

  // institutional_pct is already a percentage (e.g. 88.29), not a decimal
  const ownershipRaw = data.institutional_pct ?? data.institutional_ownership ?? data.ownership_pct
  const ownership = ownershipRaw != null
    ? (ownershipRaw > 1 ? ownershipRaw : ownershipRaw * 100)
    : null

  const trend = data.trend || 'STABLE'
  const trendColors = {
    ACCUMULATING: '#00a562',
    DISTRIBUTING: '#d97b0e',
    STABLE: '#6b7280',
    HIGH: '#00a562',
    LOW: '#e5484d',
  }
  const holders = (data.top_holders || []).slice(0, 8)
  // Estimate total shares from holder data + ownership %
  const totalShares = data.total_shares_outstanding
    || (ownershipRaw > 1 && holders.length > 0
      ? holders.reduce((s, h) => s + (h.shares || 0), 0) / (ownershipRaw / 100) * (holders.length / 10)
      : null)

  return (
    <div className="mt-4 p-3 rounded border" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center gap-3 mb-3">
        <span className="font-semibold text-sm" style={{ color: '#1a1a2e' }}>Institutional Holdings</span>
        {ownership != null && (
          <span className="text-lg font-bold" style={{ color: '#1a1a2e' }}>
            {ownership.toFixed(1)}%
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
              <th className="text-right font-medium pb-1">Shares</th>
              <th className="text-right font-medium pb-1">% Out</th>
            </tr>
          </thead>
          <tbody>
            {holders.map((h, i) => (
              <tr key={i} style={{ color: '#1a1a2e' }}>
                <td className="py-0.5">{h.name || h.holder || '—'}</td>
                <td className="py-0.5 text-right">{h.shares ? h.shares.toLocaleString() : '—'}</td>
                <td className="py-0.5 text-right">
                  {h.pct_out != null ? `${h.pct_out.toFixed(2)}%`
                    : h.ownership_pct != null ? `${(h.ownership_pct * 100).toFixed(2)}%`
                    : h.pct != null ? `${h.pct.toFixed(2)}%`
                    : h.shares && data.total_shares_outstanding ? `${(h.shares / data.total_shares_outstanding * 100).toFixed(2)}%`
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
