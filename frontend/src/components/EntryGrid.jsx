const DEFAULT_TRANCHES = [
  { tranche: '1st Third', trigger: 'Stabilisation', confirmation: 'Volume dry-up, RSI >30', zone: 'Near 52w low support' },
  { tranche: '2nd Third', trigger: 'Higher low formed', confirmation: 'Price holds above 1st entry', zone: 'Above 1st tranche price' },
  { tranche: '3rd Third', trigger: 'Trend reversal confirmed', confirmation: 'EMA20 cross above SMA50', zone: 'Above SMA50' },
  { tranche: 'DO NOT ENTER', trigger: 'Free fall / knife catching', confirmation: 'No stabilisation signal', zone: 'Below all support' },
]

export default function EntryGrid({ grid }) {
  const rows = grid && grid.length > 0 ? grid : DEFAULT_TRANCHES

  // Detect format: {tranche, price, rationale} vs {tranche, trigger, confirmation, zone}
  const hasPrice = rows.some(r => r.price != null)

  if (hasPrice) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
              {['Tranche', 'Price', 'Rationale'].map(h => (
                <th key={h} className="text-left py-2 px-2 font-medium text-xs" style={{ color: '#6b7280' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b" style={{ borderColor: '#e2e4e8' }}>
                <td className="py-2 px-2 font-semibold" style={{ color: '#1a1a2e' }}>
                  {typeof r.tranche === 'number' ? `T${r.tranche}` : r.tranche}
                </td>
                <td className="py-2 px-2 font-semibold" style={{ color: '#1a1a2e' }}>
                  {typeof r.price === 'number' ? `$${r.price}` : r.price?.toString().startsWith('$') ? r.price : `$${r.price}`}
                </td>
                <td className="py-2 px-2" style={{ color: '#6b7280' }}>{r.rationale || r.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
            {['Tranche', 'Trigger', 'Technical Confirmation', 'Price Zone'].map(h => (
              <th key={h} className="text-left py-2 px-2 font-medium text-xs" style={{ color: '#6b7280' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={i}
              className="border-b"
              style={{
                borderColor: '#e2e4e8',
                backgroundColor: r.tranche === 'DO NOT ENTER' ? '#fef2f2' : 'transparent',
              }}
            >
              <td className="py-2 px-2 font-semibold" style={{
                color: r.tranche === 'DO NOT ENTER' ? '#e5484d' : '#1a1a2e'
              }}>{r.tranche}</td>
              <td className="py-2 px-2" style={{ color: '#1a1a2e' }}>{r.trigger}</td>
              <td className="py-2 px-2" style={{ color: '#6b7280' }}>{r.confirmation}</td>
              <td className="py-2 px-2" style={{ color: '#6b7280' }}>{r.zone || r.price_zone || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
