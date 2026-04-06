import { SECTOR_COLORS } from '../theme'

export default function SectorBar({ candidates }) {
  if (!candidates || candidates.length === 0) return null

  const counts = {}
  candidates.forEach(c => {
    const s = c.sector || 'Unknown'
    counts[s] = (counts[s] || 0) + 1
  })

  const total = candidates.length
  const sectors = Object.entries(counts).sort((a, b) => b[1] - a[1])

  return (
    <div className="mb-4">
      <div className="flex rounded overflow-hidden h-6">
        {sectors.map(([sector, count]) => (
          <div
            key={sector}
            className="flex items-center justify-center text-[10px] font-medium text-white"
            style={{
              width: `${(count / total) * 100}%`,
              backgroundColor: SECTOR_COLORS[sector] || '#94a3b8',
              minWidth: count / total > 0.05 ? 'auto' : '0',
            }}
            title={`${sector}: ${count}`}
          >
            {count / total > 0.08 ? `${sector.split(' ')[0]} (${count})` : ''}
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 mt-2">
        {sectors.map(([sector, count]) => (
          <span key={sector} className="flex items-center gap-1 text-[11px]" style={{ color: '#6b7280' }}>
            <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: SECTOR_COLORS[sector] || '#94a3b8' }} />
            {sector} ({count})
          </span>
        ))}
      </div>
    </div>
  )
}
