import { useState, useEffect } from 'react'
import { getLatestScan, runScan } from '../api'
import StockCard from '../components/StockCard'
import SectorBar from '../components/SectorBar'
import FilterBar from '../components/FilterBar'

const TABS = ['B1', 'B2', 'Both', 'Watchlist']

function applySortAndFilter(candidates, filters) {
  let list = [...candidates]

  // Filter by sector
  if (filters.sector && filters.sector !== 'All Sectors') {
    list = list.filter(s => s.sector === filters.sector)
  }
  // Filter by max P/E
  if (filters.maxPE) {
    const max = parseFloat(filters.maxPE)
    list = list.filter(s => s.forward_pe != null && s.forward_pe <= max)
  }
  // Filter by min margin
  if (filters.minMargin) {
    const min = parseFloat(filters.minMargin)
    list = list.filter(s => s.operating_margin != null && s.operating_margin >= min)
  }

  // Sort
  const sort = filters.sort || 'drop'
  if (sort === 'drop') list.sort((a, b) => (b.drop_from_high || 0) - (a.drop_from_high || 0))
  else if (sort === 'fcf_yield') {
    list.sort((a, b) => {
      const ya = a.free_cash_flow && a.market_cap ? a.free_cash_flow / a.market_cap : 0
      const yb = b.free_cash_flow && b.market_cap ? b.free_cash_flow / b.market_cap : 0
      return yb - ya
    })
  }
  else if (sort === 'pe') list.sort((a, b) => (a.forward_pe || 999) - (b.forward_pe || 999))
  else if (sort === 'margin') list.sort((a, b) => (b.operating_margin || 0) - (a.operating_margin || 0))
  else if (sort === 'growth') list.sort((a, b) => (b.revenue_growth || 0) - (a.revenue_growth || 0))

  return list
}

export default function ScreenerPage() {
  const [scan, setScan] = useState(null)
  const [tab, setTab] = useState('B1')
  const [filters, setFilters] = useState({ sort: 'drop' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getLatestScan().then(setScan).catch(e => setError(e.message))
  }, [])

  const handleScan = async (type) => {
    setLoading(true)
    setError(null)
    try {
      const result = await runScan(type)
      setScan(result)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const getCandidates = () => {
    if (!scan) return []
    if (tab === 'B1') return scan.b1_candidates || []
    if (tab === 'B2') return scan.b2_candidates || []
    if (tab === 'Both') {
      const b1Tickers = new Set((scan.b1_candidates || []).map(s => s.ticker))
      return (scan.b2_candidates || []).filter(s => b1Tickers.has(s.ticker))
    }
    return []
  }

  const raw = getCandidates()
  const candidates = applySortAndFilter(raw, filters)

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>Stock Screener</h1>
          {scan?.scan_date && (
            <p className="text-xs mt-1" style={{ color: '#6b7280' }}>
              Last scan: {new Date(scan.scan_date).toLocaleString()} · {scan.total_scanned} scanned
              {scan.error_count > 0 && (
                <span style={{ color: '#e5484d' }}> · {scan.error_count} errors</span>
              )}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleScan('weekly')}
            disabled={loading}
            className="px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
            style={{ backgroundColor: '#00a562' }}
          >
            {loading ? 'Scanning...' : 'Run Weekly Scan'}
          </button>
          <button
            onClick={() => handleScan('daily')}
            disabled={loading}
            className="px-4 py-2 rounded text-sm font-medium border disabled:opacity-50"
            style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
          >
            Run Daily Scan
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded p-3 mb-4 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d' }}>
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b" style={{ borderColor: '#e2e4e8' }}>
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-[#00a562] text-[#00a562]' : 'border-transparent text-[#6b7280] hover:text-[#1a1a2e]'
            }`}
          >
            {t}
            {scan && t === 'B1' && ` (${(scan.b1_candidates || []).length})`}
            {scan && t === 'B2' && ` (${(scan.b2_candidates || []).length})`}
          </button>
        ))}
      </div>

      <FilterBar filters={filters} onChange={setFilters} />
      <SectorBar candidates={candidates} />

      {tab === 'Watchlist' ? (
        <p className="text-sm" style={{ color: '#6b7280' }}>
          Use the Watchlist page to manage your watchlist. Daily scan will refresh data for watched stocks.
        </p>
      ) : candidates.length === 0 ? (
        <p className="text-sm" style={{ color: '#6b7280' }}>
          {scan ? 'No candidates match current filters.' : 'No scan data. Run a weekly scan to get started.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {candidates.map(s => (
            <StockCard key={`${s.ticker}-${tab}`} stock={s} bucket={tab === 'Both' ? 'B1+B2' : tab} />
          ))}
        </div>
      )}
    </div>
  )
}
