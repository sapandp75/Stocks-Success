export default function PeerTable({ data, ticker }) {
  if (!data) return null

  const peers = [...(data.peers || data.comparison || [])].sort((a, b) => (b.market_cap || 0) - (a.market_cap || 0))
  const rank = data.ticker_rank

  function fmt(val, type) {
    if (val == null) return '--'
    if (type === 'pct') return `${(val * 100).toFixed(1)}%`
    if (type === 'pe') return val.toFixed(1)
    return String(val)
  }

  return (
    <div className="mt-4">
      <div className="font-semibold text-sm mb-2" style={{ color: '#1a1a2e' }}>Peer Comparison</div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ color: '#6b7280', borderBottom: '1px solid #e2e4e8' }}>
              <th className="text-left font-medium pb-1 pr-3">Ticker</th>
              <th className="text-right font-medium pb-1 pr-3">Fwd PE</th>
              <th className="text-right font-medium pb-1 pr-3">Op Margin</th>
              <th className="text-right font-medium pb-1 pr-3">Rev Growth</th>
              <th className="text-right font-medium pb-1 pr-3">Drop %</th>
              <th className="text-left font-medium pb-1">Direction</th>
            </tr>
          </thead>
          <tbody>
            {peers.map((p, i) => {
              const isTarget = (p.ticker || '').toUpperCase() === (ticker || '').toUpperCase()
              return (
                <tr
                  key={i}
                  style={{
                    backgroundColor: isTarget ? '#f0f9ff' : 'transparent',
                    fontWeight: isTarget ? 600 : 400,
                    color: '#1a1a2e',
                  }}
                >
                  <td className="py-1 pr-3">{p.ticker}</td>
                  <td className="py-1 pr-3 text-right">{fmt(p.forward_pe, 'pe')}</td>
                  <td className="py-1 pr-3 text-right">{fmt(p.operating_margin, 'pct')}</td>
                  <td className="py-1 pr-3 text-right" style={{ color: p.revenue_growth > 0 ? '#00a562' : '#e5484d' }}>
                    {fmt(p.revenue_growth, 'pct')}
                  </td>
                  <td className="py-1 pr-3 text-right">{fmt(p.drop_from_high, 'pct')}</td>
                  <td className="py-1 text-[10px]">{(p.direction || '').replace(/_/g, ' ')}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {rank != null && (
        <div className="text-xs mt-2 flex gap-3" style={{ color: '#6b7280' }}>
          {typeof rank === 'object' ? (
            <>
              {rank.pe_rank != null && <span>PE rank: {rank.pe_rank}/{rank.total_peers}</span>}
              {rank.margin_rank != null && <span>Margin rank: {rank.margin_rank}/{rank.total_peers}</span>}
              {rank.growth_rank != null && <span>Growth rank: {rank.growth_rank}/{rank.total_peers}</span>}
            </>
          ) : (
            <span>Rank among peers: {rank}</span>
          )}
        </div>
      )}
    </div>
  )
}
