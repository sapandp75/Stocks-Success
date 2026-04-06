import { useState } from 'react'
import { triggerAiAnalysis } from '../api'

export default function AiAnalyzeButton({ ticker, onComplete }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleClick = async () => {
    setLoading(true)
    setError(null)
    try {
      await triggerAiAnalysis(ticker)
      if (onComplete) onComplete()
    } catch (e) {
      if (e.message.includes('429')) {
        setError('Rate limited -- please wait a moment and try again.')
      } else {
        setError(`Analysis failed: ${e.message}`)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mb-4">
      <button
        onClick={handleClick}
        disabled={loading}
        className="px-4 py-2 rounded text-sm font-medium text-white"
        style={{ backgroundColor: loading ? '#6b7280' : '#3b82f6' }}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="3" strokeDasharray="31.4 31.4" />
            </svg>
            Analyzing...
          </span>
        ) : (
          'AI Analyze with Gemini'
        )}
      </button>
      {error && (
        <div className="text-xs mt-1" style={{ color: '#e5484d' }}>{error}</div>
      )}
    </div>
  )
}
