export default function AiProvenance({ type = 'AI synthesis', sourceBacked = false, confidence }) {
  const confColors = { low: '#e5484d', medium: '#d97b0e', high: '#00a562' }

  return (
    <div className="flex items-center gap-2 text-[11px] px-3 py-1.5 rounded mb-3" style={{ backgroundColor: '#f7f8fa', color: '#6b7280' }}>
      <span>🤖 {type}</span>
      <span>·</span>
      <span style={{ color: sourceBacked ? '#00a562' : '#d97b0e' }}>
        {sourceBacked ? 'Source-backed' : 'Not source-backed'}
      </span>
      {confidence && (
        <>
          <span>·</span>
          <span style={{ color: confColors[confidence] || '#6b7280' }}>
            Confidence: {confidence}
          </span>
        </>
      )}
    </div>
  )
}
