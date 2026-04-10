export default function AnalysisStatus({ ai, staleness, gates, dataQuality, fundamentals, memoTrust, onReanalyze }) {
  const hasAi = !!ai
  const earningsDate = fundamentals?.earnings_date
  const earningsDays = earningsDate ? Math.ceil((new Date(earningsDate) - new Date()) / 86400000) : null
  const earningsNear = earningsDays != null && earningsDays > 0 && earningsDays <= 14

  let freshnessLabel = null
  let freshnessColor = '#6b7280'
  if (hasAi && staleness != null) {
    if (staleness <= 3) { freshnessLabel = 'Fresh'; freshnessColor = '#00a562' }
    else if (staleness <= 14) { freshnessLabel = `${staleness}d old`; freshnessColor = '#d97b0e' }
    else { freshnessLabel = `Stale: ${staleness}d`; freshnessColor = '#e5484d' }
  }

  const trustColors = { Complete: '#00a562', Partial: '#d97b0e', Incomplete: '#e5484d' }

  return (
    <div className="flex items-center gap-3 flex-wrap px-5 py-2 text-[11px] max-w-5xl mx-auto" style={{ backgroundColor: '#f7f8fa', borderBottom: '1px solid #e2e4e8' }}>
      {/* AI status */}
      <span className="px-2 py-0.5 rounded font-medium" style={{
        backgroundColor: hasAi ? '#dcfce7' : '#f3f4f6',
        color: hasAi ? '#00a562' : '#6b7280'
      }}>
        {hasAi ? 'AI Generated' : 'No AI Analysis'}
      </span>

      {/* Freshness */}
      {freshnessLabel && (
        <button
          onClick={onReanalyze}
          className="px-2 py-0.5 rounded font-medium hover:opacity-80"
          style={{ backgroundColor: `${freshnessColor}20`, color: freshnessColor }}
          title="Click to re-analyze"
        >
          {freshnessLabel}
        </button>
      )}

      {/* Gates */}
      {gates && (
        <span
          className="px-2 py-0.5 rounded font-bold text-white"
          style={{ backgroundColor: gates.passes_all ? '#00a562' : '#e5484d' }}
          title={gates.details ? JSON.stringify(gates.details) : undefined}
        >
          {gates.passes_all ? 'GATES PASS' : 'GATES FAIL'}
        </span>
      )}

      {/* Completeness */}
      {memoTrust && (
        <span className="px-2 py-0.5 rounded font-medium" style={{
          backgroundColor: `${trustColors[memoTrust.state] || '#6b7280'}20`,
          color: trustColors[memoTrust.state] || '#6b7280'
        }}>
          {memoTrust.state === 'Complete' ? 'Complete' : `${memoTrust.state} — ${memoTrust.gaps} gap${memoTrust.gaps !== 1 ? 's' : ''}`}
        </span>
      )}

      {/* Critical gaps */}
      {memoTrust?.criticalGaps?.length > 0 && (
        <span style={{ color: '#e5484d' }}>
          Missing: {memoTrust.criticalGaps.join(', ')}
        </span>
      )}

      {/* Earnings proximity */}
      {earningsNear && (
        <span className="px-2 py-0.5 rounded font-medium" style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>
          Earnings in {earningsDays}d
        </span>
      )}

      {/* Data quality */}
      {dataQuality && (
        <span style={{ color: '#6b7280' }}>
          {(dataQuality.completeness * 100).toFixed(0)}% complete
        </span>
      )}
    </div>
  )
}
