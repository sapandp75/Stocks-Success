import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getDeepDive } from '../api'

export default function DeepDivePage() {
  const { ticker } = useParams()
  const [data, setData] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const loadData = (t) => {
    if (!t) return
    setLoading(true)
    getDeepDive(t).then(setData).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => {
    if (ticker) {
      setInput(ticker.toUpperCase())
      loadData(ticker)
    }
  }, [ticker])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Deep Dive</h1>

      {!ticker && (
        <div className="flex gap-2 mb-6">
          <input
            className="border rounded px-3 py-2 text-sm w-40"
            style={{ borderColor: '#e2e4e8' }}
            placeholder="Ticker (e.g. AAPL)"
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && loadData(input)}
          />
          <button
            onClick={() => loadData(input)}
            className="px-4 py-2 rounded text-sm font-medium text-white"
            style={{ backgroundColor: '#00a562' }}
          >
            Load
          </button>
        </div>
      )}

      {loading && <p style={{ color: '#6b7280' }}>Loading deep dive data...</p>}

      {data && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
            <h2 className="font-bold text-lg mb-3" style={{ color: '#1a1a2e' }}>
              {data.fundamentals?.name} ({data.ticker})
            </h2>
            <div className="grid grid-cols-4 gap-4 text-sm">
              <div><span style={{ color: '#6b7280' }}>Price</span><div className="font-semibold">${data.fundamentals?.price?.toFixed(2)}</div></div>
              <div><span style={{ color: '#6b7280' }}>Fwd P/E</span><div className="font-semibold">{data.fundamentals?.forward_pe?.toFixed(1) ?? '—'}</div></div>
              <div><span style={{ color: '#6b7280' }}>Op Margin</span><div className="font-semibold">{data.fundamentals?.operating_margin ? (data.fundamentals.operating_margin * 100).toFixed(1) + '%' : '—'}</div></div>
              <div><span style={{ color: '#6b7280' }}>Rev Growth</span><div className="font-semibold">{data.fundamentals?.revenue_growth ? (data.fundamentals.revenue_growth * 100).toFixed(1) + '%' : '—'}</div></div>
            </div>
          </div>

          {data.reverse_dcf && (
            <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
              <h3 className="font-bold mb-2" style={{ color: '#1a1a2e' }}>Reverse DCF</h3>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                Implied growth rate: <span className="font-semibold" style={{ color: '#1a1a2e' }}>{(data.reverse_dcf.implied_growth_rate * 100).toFixed(1)}%</span>
              </p>
              <p className="text-sm mt-1" style={{ color: '#6b7280' }}>{data.reverse_dcf.interpretation}</p>
            </div>
          )}

          {data.forward_dcf && (
            <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
              <h3 className="font-bold mb-3" style={{ color: '#1a1a2e' }}>Forward DCF (3 Scenarios)</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                {['bear', 'base', 'bull'].map(s => (
                  <div key={s} className="p-3 rounded" style={{ backgroundColor: '#f7f8fa' }}>
                    <div className="font-semibold capitalize mb-1" style={{
                      color: s === 'bear' ? '#e5484d' : s === 'bull' ? '#00a562' : '#1a1a2e'
                    }}>{s}</div>
                    <div className="text-lg font-bold">${data.forward_dcf[s]?.intrinsic_value_per_share}</div>
                    {data.forward_dcf[s]?.terminal_value_warning && (
                      <div className="text-[10px] mt-1" style={{ color: '#d97b0e' }}>TV &gt; 50%</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.ai_analysis && (
            <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
              <h3 className="font-bold mb-2" style={{ color: '#1a1a2e' }}>AI Analysis</h3>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                Verdict: <span className="font-semibold" style={{ color: '#1a1a2e' }}>{data.ai_analysis.verdict}</span>
                {' · '}Conviction: <span className="font-semibold">{data.ai_analysis.conviction}</span>
                {' · '}Date: {data.ai_analysis.dive_date}
              </p>
              {data.ai_analysis.first_impression && (
                <p className="text-sm mt-2" style={{ color: '#1a1a2e' }}>{data.ai_analysis.first_impression}</p>
              )}
            </div>
          )}

          {!data.ai_analysis && (
            <div className="bg-white rounded-lg border p-5 text-sm" style={{ borderColor: '#e2e4e8', color: '#6b7280' }}>
              No AI analysis yet. Run: <code className="bg-gray-100 px-1 rounded">python bridge/deep_dive_worker.py {data.ticker} --post</code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
