const LEVELS = ['NONE', 'WEAK', 'MODERATE', 'STRONG']
const LEVEL_COLORS = { NONE: '#d1d5db', WEAK: '#e5484d', MODERATE: '#d97b0e', STRONG: '#00a562' }

function scoreToLevel(score, max = 10) {
  if (score == null) return 0
  const pct = score / max
  if (pct >= 0.7) return 3  // STRONG
  if (pct >= 0.4) return 2  // MODERATE
  if (pct > 0) return 1     // WEAK
  return 0                   // NONE
}

function ratingIndex(rating) {
  const idx = LEVELS.indexOf((rating || '').toUpperCase())
  return idx >= 0 ? idx : 0
}

export default function MoatRatingBars({ ratings }) {
  if (!ratings || ratings.length === 0) return null

  return (
    <div className="space-y-3">
      {ratings.map((r, i) => {
        // Support both formats: {factor, rating, evidence} and {name, score, max, note}
        const label = r.factor || r.name || `Factor ${i + 1}`
        const level = r.rating ? ratingIndex(r.rating) : scoreToLevel(r.score, r.max || 10)
        const detail = r.evidence || r.note
        const scoreLabel = r.score != null ? `${r.score}/${r.max || 10}` : null

        return (
          <div key={i}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium" style={{ color: '#1a1a2e' }}>{label}</span>
              <div className="flex items-center gap-2">
                {scoreLabel && (
                  <span className="text-[10px] font-medium" style={{ color: '#6b7280' }}>{scoreLabel}</span>
                )}
                <span className="text-[10px] font-bold" style={{ color: LEVEL_COLORS[LEVELS[level]] }}>
                  {LEVELS[level]}
                </span>
              </div>
            </div>
            <div className="flex gap-1">
              {LEVELS.map((_, si) => (
                <div
                  key={si}
                  className="h-2 flex-1 rounded-sm"
                  style={{ backgroundColor: si <= level ? LEVEL_COLORS[LEVELS[level]] : '#e5e7eb' }}
                />
              ))}
            </div>
            {detail && (
              <div className="text-xs mt-1" style={{ color: '#6b7280' }}>{detail}</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
