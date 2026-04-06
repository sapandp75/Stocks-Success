/**
 * Contrarian-inverted sentiment badge.
 * Negative sentiment = green (opportunity for contrarian).
 * Positive sentiment = grey (consensus, less edge).
 */
export default function SentimentBadge({ score, label, contrarianRating }) {
  if (score === null || score === undefined) {
    return <span className="text-xs" style={{ color: '#6b7280' }}>—</span>
  }

  const colorMap = {
    HIGH_INTEREST: { bg: '#dcfce7', text: '#00a562', border: '#86efac' },
    MODERATE_INTEREST: { bg: '#fef9c3', text: '#d97b0e', border: '#fde68a' },
    CONSENSUS: { bg: '#f7f8fa', text: '#6b7280', border: '#e2e4e8' },
    UNKNOWN: { bg: '#f7f8fa', text: '#6b7280', border: '#e2e4e8' },
  }

  const c = colorMap[contrarianRating] || colorMap.UNKNOWN

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border"
      style={{ backgroundColor: c.bg, color: c.text, borderColor: c.border }}
      title={`Crowd sentiment: ${label} (${score.toFixed(2)}) — Contrarian interest: ${contrarianRating}`}
    >
      {score.toFixed(2)}
    </span>
  )
}
