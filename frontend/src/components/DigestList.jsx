import { useState, useEffect } from 'react'
import { fetchWatchlistDigest, markDigestSeen } from '../api'

const EVENT_META = {
  insider_buy: { label: 'Insider Buy', color: '#00a562' },
  insider_sell: { label: 'Insider Sell', color: '#e5484d' },
  press_release: { label: 'Press Release', color: '#3b82f6' },
  analyst_change: { label: 'Analyst Change', color: '#d97b0e' },
  new_article: { label: 'Article', color: '#6b7280' },
}

export default function DigestList() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchWatchlistDigest()
      .then(data => setEvents(data.events || []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-sm py-2" style={{ color: '#6b7280' }}>Checking for updates...</div>
  if (error) return <div className="text-sm py-2" style={{ color: '#e5484d' }}>Failed to load digest: {error}</div>
  if (events.length === 0) return null

  const unseenCount = events.filter(e => !e.seen).length

  const handleMarkSeen = () => {
    const ids = events.filter(e => !e.seen).map(e => e.id)
    markDigestSeen(ids).then(() => {
      setEvents(events.map(e => ({ ...e, seen: 1 })))
    })
  }

  return (
    <div className="mb-6 bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: '#1a1a2e' }}>What Changed</span>
          {unseenCount > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded font-medium"
              style={{ backgroundColor: '#fef9c3', color: '#d97b0e' }}>
              {unseenCount} new
            </span>
          )}
        </div>
        {unseenCount > 0 && (
          <button onClick={handleMarkSeen} className="text-xs hover:underline" style={{ color: '#6b7280' }}>
            Mark all seen
          </button>
        )}
      </div>
      <ul className="space-y-1.5">
        {events.slice(0, 15).map(event => {
          const meta = EVENT_META[event.event_type] || EVENT_META.new_article
          return (
            <li key={event.id} className="flex items-start gap-2 text-sm"
              style={{ fontWeight: event.seen ? 'normal' : '500' }}>
              <span className="text-xs mt-0.5 shrink-0" style={{ color: meta.color }}>[{meta.label}]</span>
              <span className="text-xs w-12 shrink-0 font-mono" style={{ color: '#6b7280' }}>{event.ticker}</span>
              <span className="flex-1" style={{ color: '#1a1a2e' }}>{event.headline}</span>
              <span className="text-xs shrink-0" style={{ color: '#6b7280' }}>{event.event_date?.split('T')[0]}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
