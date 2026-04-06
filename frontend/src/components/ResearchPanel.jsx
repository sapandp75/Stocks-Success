import { useState, useEffect } from 'react'
import SentimentBadge from './SentimentBadge'

export default function ResearchPanel({ ticker, initialData }) {
  const [data, setData] = useState(initialData || null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (initialData) {
      setData(initialData)
      return
    }
    if (!ticker) return
    setLoading(true)
    fetch(`/api/research/${ticker}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [ticker, initialData])

  if (loading) return <p className="text-sm" style={{ color: '#6b7280' }}>Loading research...</p>
  if (!data) return <p className="text-sm italic" style={{ color: '#6b7280' }}>No research data available.</p>

  return (
    <div className="space-y-4">
      {/* Sentiment Summary */}
      {data.sentiment && (
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-medium" style={{ color: '#6b7280' }}>Crowd Sentiment:</span>
          <SentimentBadge
            score={data.sentiment.av_sentiment_score}
            label={data.sentiment.av_sentiment_label}
            contrarianRating={data.sentiment.contrarian_rating}
          />
          {data.sentiment.contrarian_note && (
            <span className="text-xs italic" style={{ color: '#6b7280' }}>{data.sentiment.contrarian_note}</span>
          )}
        </div>
      )}

      {/* Analyst Targets */}
      {data.sentiment?.finnhub_target_mean && (
        <div className="text-sm" style={{ color: '#6b7280' }}>
          Analyst target: ${data.sentiment.finnhub_target_low?.toFixed(0)} —
          <span className="font-semibold" style={{ color: '#1a1a2e' }}> ${data.sentiment.finnhub_target_mean?.toFixed(0)} </span>
          — ${data.sentiment.finnhub_target_high?.toFixed(0)}
          {data.sentiment.finnhub_recent_change && data.sentiment.finnhub_recent_change !== "maintain" && (
            <span className="ml-2 text-xs" style={{
              color: data.sentiment.finnhub_recent_change === "downgrade" ? '#00a562' : '#6b7280'
            }}>
              ({data.sentiment.finnhub_recent_change})
            </span>
          )}
        </div>
      )}

      {/* Seeking Alpha Articles */}
      {data.articles?.length > 0 && (
        <div>
          <div className="text-sm font-medium mb-1" style={{ color: '#1a1a2e' }}>Recent Analysis (Seeking Alpha)</div>
          <ul className="space-y-1">
            {data.articles.map((a, i) => (
              <li key={i} className="text-sm">
                <a href={a.url} target="_blank" rel="noopener noreferrer"
                   className="hover:underline" style={{ color: '#3b82f6' }}>
                  {a.title}
                </a>
                <span className="text-xs ml-2" style={{ color: '#6b7280' }}>{a.published_date}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Substack Mentions */}
      {data.newsletters?.length > 0 && (
        <div>
          <div className="text-sm font-medium mb-1" style={{ color: '#1a1a2e' }}>Newsletter Mentions</div>
          <ul className="space-y-1">
            {data.newsletters.map((a, i) => (
              <li key={i} className="text-sm">
                <a href={a.url} target="_blank" rel="noopener noreferrer"
                   className="hover:underline" style={{ color: '#3b82f6' }}>
                  {a.title}
                </a>
                <span className="text-xs ml-2" style={{ color: '#6b7280' }}>{a.published_date}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Transcript */}
      {data.transcript?.available && (
        <div className="text-sm" style={{ color: '#6b7280' }}>
          Latest transcript: <span className="font-semibold" style={{ color: '#1a1a2e' }}>{data.transcript.title}</span>
          <span className="text-xs ml-2">(full text available via bridge --context)</span>
        </div>
      )}

      {data.total_research_items === 0 && (
        <p className="text-sm italic" style={{ color: '#6b7280' }}>
          No recent research found for {ticker}. RSS feeds and API keys expand coverage.
        </p>
      )}
    </div>
  )
}
