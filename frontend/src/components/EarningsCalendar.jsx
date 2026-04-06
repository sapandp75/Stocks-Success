import { useState, useEffect } from 'react'

export default function EarningsCalendar() {
  const [earnings, setEarnings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/regime/earnings-calendar')
      .then(r => r.json())
      .then(data => setEarnings(data.upcoming_earnings || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading || earnings.length === 0) return null

  const now = new Date()
  const twoWeeks = new Date(now.getTime() + 14 * 86400000)
  const upcoming = earnings.filter(e => {
    const d = new Date(e.earnings_date)
    return d >= now && d <= twoWeeks
  })

  if (upcoming.length === 0) return null

  return (
    <div className="mt-4 bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
      <div className="text-sm font-semibold mb-2" style={{ color: '#1a1a2e' }}>
        Watchlist Earnings — Next 14 Days
      </div>
      <div className="flex flex-wrap gap-3">
        {upcoming.map(e => (
          <div key={e.ticker} className="flex items-center gap-1.5 rounded px-2 py-1 border"
            style={{ backgroundColor: '#fef9c3', borderColor: '#fde68a' }}>
            <span className="font-mono text-sm font-medium" style={{ color: '#1a1a2e' }}>{e.ticker}</span>
            <span className="text-xs" style={{ color: '#d97b0e' }}>
              {new Date(e.earnings_date).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs mt-2" style={{ color: '#6b7280' }}>
        Options rule: No new positions within 14 days of earnings.
      </p>
    </div>
  )
}
