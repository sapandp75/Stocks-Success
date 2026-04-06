import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getWatchlist, removeFromWatchlist } from '../api'
import DigestList from '../components/DigestList'

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const load = () => {
    getWatchlist()
      .then(setWatchlist)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const handleRemove = async (ticker) => {
    await removeFromWatchlist(ticker)
    load()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Watchlist</h1>

      <DigestList />

      {error && (
        <div className="rounded-lg p-4 mb-4 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d', border: '1px solid #fca5a5' }}>
          Failed to load watchlist: {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm" style={{ color: '#6b7280' }}>Loading watchlist...</p>
      ) : watchlist.length === 0 ? (
        <p className="text-sm" style={{ color: '#6b7280' }}>No stocks on watchlist. Use the Screener to add stocks.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: '#e2e4e8' }}>
                {['Ticker', 'Bucket', 'Added', 'Conviction', 'Entry Zone', 'Thesis', 'Status', 'Actions'].map(h => (
                  <th key={h} className="text-left py-2 px-2 font-medium" style={{ color: '#6b7280' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {watchlist.map(w => (
                <tr key={w.ticker} className="border-b hover:bg-[#f7f8fa]" style={{ borderColor: '#e2e4e8' }}>
                  <td className="py-2 px-2 font-bold" style={{ color: '#1a1a2e' }}>{w.ticker}</td>
                  <td className="py-2 px-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
                      style={{ backgroundColor: w.bucket === 'B1' ? '#3b82f6' : '#8b5cf6' }}>
                      {w.bucket}
                    </span>
                  </td>
                  <td className="py-2 px-2" style={{ color: '#6b7280' }}>{w.added_date}</td>
                  <td className="py-2 px-2">{w.conviction}</td>
                  <td className="py-2 px-2" style={{ color: '#6b7280' }}>
                    {w.entry_zone_low && w.entry_zone_high ? `$${w.entry_zone_low} - $${w.entry_zone_high}` : '—'}
                  </td>
                  <td className="py-2 px-2 max-w-[200px] truncate" style={{ color: '#6b7280' }}>{w.thesis_note || '—'}</td>
                  <td className="py-2 px-2">{w.status}</td>
                  <td className="py-2 px-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => navigate(`/deep-dive/${w.ticker}`)}
                        className="text-xs font-medium"
                        style={{ color: '#00a562' }}
                      >
                        Deep Dive
                      </button>
                      <button
                        onClick={() => handleRemove(w.ticker)}
                        className="text-xs font-medium"
                        style={{ color: '#e5484d' }}
                      >
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
