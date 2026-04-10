import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getDeepDive, triggerAiAnalysis, downloadDeepDiveExport } from '../api'

// Header / Status / Data Strip
import StickyHeader from '../components/deep-dive/StickyHeader'
import AnalysisStatus from '../components/deep-dive/AnalysisStatus'
import DataStrip from '../components/deep-dive/DataStrip'

// Core Flow §1-8
import DataSnapshot from '../components/deep-dive/sections/DataSnapshot'
import FirstImpression from '../components/deep-dive/sections/FirstImpression'
import BearCase from '../components/deep-dive/sections/BearCase'
import BullCase from '../components/deep-dive/sections/BullCase'
import Valuation from '../components/deep-dive/sections/Valuation'
import WholePicture from '../components/deep-dive/sections/WholePicture'
import SelfReview from '../components/deep-dive/sections/SelfReview'
import VerdictAction from '../components/deep-dive/sections/VerdictAction'

// Appendices A-D
import GrowthEstimates from '../components/deep-dive/sections/GrowthEstimates'
import MoatAssessment from '../components/deep-dive/sections/MoatAssessment'
import OpportunitiesThreats from '../components/deep-dive/sections/OpportunitiesThreats'
import Scenarios from '../components/deep-dive/sections/Scenarios'

function computeMemoTrust(data) {
  const ai = data?.ai_analysis
  const criticalGaps = []
  if (!data?.fundamentals?.price) criticalGaps.push('fundamentals')
  if (!ai?.bear_case_stock && !ai?.bear_case_business) criticalGaps.push('bear case')
  if (!ai?.bull_case_rebuttal && !ai?.bull_case_upside) criticalGaps.push('bull case')
  if (!data?.reverse_dcf && !data?.forward_dcf) criticalGaps.push('valuation')
  if (!ai?.verdict) criticalGaps.push('verdict')

  const importantGaps = []
  if (!ai?.whole_picture && !data?.fund_flow) importantGaps.push('whole picture')
  if (!ai?.self_review) importantGaps.push('self-review')

  const gaps = criticalGaps.length + importantGaps.length
  const state = criticalGaps.length > 0 ? 'Incomplete' : importantGaps.length > 0 ? 'Partial' : 'Complete'
  return { state, gaps, criticalGaps }
}

export default function DeepDivePage() {
  const { ticker: urlTicker } = useParams()
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState(null)

  const loadData = (t) => {
    if (!t) return
    setLoading(true)
    setError(null)
    getDeepDive(t)
      .then(setData)
      .catch(e => { setError(e.message); setData(null) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (urlTicker) {
      setInput(urlTicker.toUpperCase())
      loadData(urlTicker)
    }
  }, [urlTicker])

  const handleLoad = () => { if (input) navigate(`/deep-dive/${input}`) }
  const handleReload = () => { if (data?.ticker) loadData(data.ticker) }
  const handleReanalyze = async () => {
    if (!data?.ticker) return
    await triggerAiAnalysis(data.ticker)
    loadData(data.ticker)
  }
  const handleExport = async () => {
    if (!data?.ticker || exporting) return
    setExporting(true)
    setError(null)
    try {
      await downloadDeepDiveExport(data.ticker)
    } catch (e) {
      setError(e.message)
    } finally {
      setExporting(false)
    }
  }

  const ai = data?.ai_analysis
  const memoTrust = data ? computeMemoTrust(data) : null

  return (
    <div style={{ backgroundColor: '#f0f1f3', minHeight: '100vh' }}>
      {/* Search bar (shown when no data) */}
      {!data && (
        <div className="p-6 max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold mb-4" style={{ color: '#1a1a2e' }}>Deep Dive</h1>
          <div className="flex gap-2 mb-6">
            <input
              className="border rounded px-3 py-2 text-sm w-40"
              style={{ borderColor: '#e2e4e8' }}
              placeholder="Ticker (e.g. AAPL)"
              value={input}
              onChange={e => setInput(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && handleLoad()}
            />
            <button onClick={handleLoad} className="px-4 py-2 rounded text-sm font-medium text-white" style={{ backgroundColor: '#00a562' }}>
              Load
            </button>
          </div>
          {loading && <p style={{ color: '#6b7280' }}>Loading deep dive data...</p>}
          {error && (
            <div className="rounded-lg p-4 mb-4 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d', border: '1px solid #fca5a5' }}>
              Failed to load data for {input}: {error}
            </div>
          )}
        </div>
      )}

      {/* Main layout when data loaded */}
      {data && (
        <>
          {/* Tier 1: Sticky Header */}
          <StickyHeader
            ticker={data.ticker}
            fundamentals={data.fundamentals}
            ai={ai}
            onReload={handleReload}
            onExport={handleExport}
            exporting={exporting}
          />

          {error && (
            <div className="px-5 pt-3 max-w-5xl mx-auto">
              <div className="rounded-lg p-3 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d', border: '1px solid #fca5a5' }}>
                {error}
              </div>
            </div>
          )}

          {/* Tier 2: Analysis Status */}
          <AnalysisStatus
            ai={ai} staleness={data.staleness_days} gates={data.gates}
            dataQuality={data.data_quality} fundamentals={data.fundamentals}
            memoTrust={memoTrust} onReanalyze={handleReanalyze}
          />

          {/* Tier 3: Data Strip */}
          <DataStrip
            ticker={data.ticker}
            fundamentals={data.fundamentals} technicals={data.technicals}
            financialHistory={data.financial_history} growthMetrics={data.growth_metrics}
            quarterly={data.quarterly} forwardEstimates={data.forward_estimates}
            optionsSnapshot={data.options_snapshot}
          />

          {/* Search bar inline */}
          <div className="px-5 py-3 max-w-5xl mx-auto flex gap-2">
            <input
              className="border rounded px-3 py-2 text-sm w-40"
              style={{ borderColor: '#e2e4e8' }}
              placeholder="Ticker"
              value={input}
              onChange={e => setInput(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === 'Enter' && handleLoad()}
            />
            <button onClick={handleLoad} className="px-4 py-2 rounded text-sm font-medium text-white" style={{ backgroundColor: '#00a562' }}>
              Load
            </button>
          </div>

          {/* Core Flow */}
          <div className="px-5 pb-6 max-w-5xl mx-auto space-y-3">
            <DataSnapshot ticker={data.ticker} fundamentals={data.fundamentals} gates={data.gates} dataQuality={data.data_quality} fcf3yrAvg={data.fcf_3yr_avg} netDebt={data.net_debt} sbc={data.sbc} sbcAdjusted={data.sbc_adjusted} growthMetrics={data.growth_metrics} reverseDcf={data.reverse_dcf} analyst={data.analyst} optionsSnapshot={data.options_snapshot} />
            <FirstImpression ai={ai} ticker={data.ticker} />
            <BearCase ai={ai} />
            <BullCase ai={ai} />
            <Valuation data={data} ai={ai} />
            <WholePicture ai={ai} fundFlow={data.fund_flow} insiderActivity={data.insider_activity} institutional={data.institutional} />
            <SelfReview ai={ai} />
            <VerdictAction ai={ai} memoTrust={memoTrust} />

            {/* Appendices divider */}
            <div className="pt-4 pb-1">
              <div className="text-xs font-medium tracking-wider" style={{ color: '#6b7280' }}>APPENDICES — Supporting Analysis</div>
              <div className="mt-1 h-px" style={{ backgroundColor: '#e2e4e8' }} />
            </div>

            <GrowthEstimates quarterly={data.quarterly} growthMetrics={data.growth_metrics} forwardEstimates={data.forward_estimates} reverseDcf={data.reverse_dcf} ai={ai} />
            <MoatAssessment ai={ai} />
            <OpportunitiesThreats ai={ai} />
            <Scenarios ai={ai} currentPrice={data.fundamentals?.price} />
          </div>
        </>
      )}
    </div>
  )
}
