export default function MissingSeverity({ severity = 'optional', label }) {
  if (severity === 'critical') {
    return (
      <div className="rounded-lg p-3 mb-3 flex items-center gap-2 text-sm" style={{ backgroundColor: '#fffbeb', border: '1px solid #d97b0e', color: '#92400e' }}>
        <span>⚠</span>
        <span>{label || 'Critical data unavailable'} — decision quality reduced</span>
      </div>
    )
  }

  if (severity === 'important') {
    return (
      <div className="p-3 mb-3 rounded text-sm" style={{ borderLeft: '3px solid #d97b0e', backgroundColor: '#f7f8fa', color: '#92400e' }}>
        {label || 'Data unavailable'}
      </div>
    )
  }

  return (
    <p className="text-sm italic" style={{ color: '#6b7280' }}>
      {label || 'Data unavailable'}
    </p>
  )
}
