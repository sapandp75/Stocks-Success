import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { getLatestScan, startScan, getScanStatus, resetScan } from '../api'
import StockCard from '../components/StockCard'
import SectorBar from '../components/SectorBar'
import FilterBar from '../components/FilterBar'

const TABS = ['B1', 'B2', 'Both', 'Watchlist']
const UNIVERSES = [
  { key: 'spx', label: 'S&P 500', defaultTotal: 503 },
  { key: 'ndx', label: 'NDX 100', defaultTotal: 103 },
]

function applySortAndFilter(candidates, filters) {
  let list = [...candidates]

  if (filters.sector && filters.sector !== 'All Sectors') {
    list = list.filter(s => s.sector === filters.sector)
  }
  if (filters.maxPE) {
    const max = parseFloat(filters.maxPE)
    list = list.filter(s => s.forward_pe != null && s.forward_pe <= max)
  }
  if (filters.minMargin) {
    const min = parseFloat(filters.minMargin)
    list = list.filter(s => s.operating_margin != null && s.operating_margin >= min)
  }
  if (filters.direction) {
    list = list.filter(s => s.direction === filters.direction)
  }
  if (filters.rsiFilter) {
    if (filters.rsiFilter === 'oversold') list = list.filter(s => s.rsi != null && s.rsi < 30)
    else if (filters.rsiFilter === 'neutral') list = list.filter(s => s.rsi != null && s.rsi >= 30 && s.rsi <= 70)
    else if (filters.rsiFilter === 'overbought') list = list.filter(s => s.rsi != null && s.rsi > 70)
  }

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
  else if (sort === 'rsi') list.sort((a, b) => (a.rsi || 999) - (b.rsi || 999))
  else if (sort === 'direction') {
    const order = { FULL_DOWNTREND: 0, TREND_WEAKENING: 1, CORRECTION_IN_UPTREND: 2, PULLBACK_IN_UPTREND: 3, FULL_UPTREND: 4, MIXED: 2.5 }
    list.sort((a, b) => (order[a.direction] ?? 2.5) - (order[b.direction] ?? 2.5))
  }

  return list
}

function UniverseToggle({ universe, onChange }) {
  return (
    <div className="inline-flex rounded-lg border p-0.5 mb-4" style={{ borderColor: '#e2e4e8', backgroundColor: '#f0f1f3' }}>
      {UNIVERSES.map(u => (
        <button
          key={u.key}
          onClick={() => onChange(u.key)}
          className="px-4 py-1.5 rounded-md text-sm font-medium transition-all"
          style={{
            backgroundColor: universe === u.key ? '#ffffff' : 'transparent',
            color: universe === u.key ? '#1a1a2e' : '#6b7280',
            boxShadow: universe === u.key ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
            border: universe === u.key ? '1px solid #e2e4e8' : '1px solid transparent',
          }}
        >
          {u.label}
        </button>
      ))}
    </div>
  )
}

function ScanProgress({ scanned, total, universe }) {
  const pct = total > 0 ? Math.round((scanned / total) * 100) : 0
  const uConfig = UNIVERSES.find(u => u.key === universe) || UNIVERSES[0]
  return (
    <div className="bg-white rounded-lg border p-6 mb-6" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center gap-4 mb-3">
        <div className="animate-spin w-5 h-5 border-2 rounded-full" style={{ borderColor: '#e2e4e8', borderTopColor: '#00a562' }} />
        <div>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>Scanning {uConfig.label}...</div>
          <div className="text-xs" style={{ color: '#6b7280' }}>
            Scanning ~{uConfig.defaultTotal} stocks through B1/B2 gates.
          </div>
        </div>
      </div>
      <div className="w-full rounded-full h-2 mb-2" style={{ backgroundColor: '#e2e4e8' }}>
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: '#00a562' }} />
      </div>
      <div className="text-xs" style={{ color: '#6b7280' }}>
        {scanned > 0 ? `${scanned} / ~${total || uConfig.defaultTotal} stocks processed` : 'Starting scan...'}
      </div>
    </div>
  )
}

export default function ScreenerPage() {
  const [universe, setUniverse] = useState('spx')
  const [scans, setScans] = useState({})  // keyed by universe
  const [tab, setTab] = useState('B1')
  const [filters, setFilters] = useState({ sort: 'drop' })
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState(null)
  const defaultTotal = UNIVERSES.find(u => u.key === universe)?.defaultTotal || 503
  const [scanProgress, setScanProgress] = useState({ scanned: 0, total: defaultTotal })

  const scan = scans[universe] || null

  // Load latest scan for the active universe + detect running scans
  // Always fetches from API to pick up scans that completed while viewing another universe
  useEffect(() => {
    let cancelled = false
    const hasCached = !!scans[universe]
    if (!hasCached) setInitialLoading(true)

    const load = async () => {
      // Check if a scan is running on the server for this universe
      try {
        const status = await getScanStatus(universe)
        if (!cancelled && status.status === 'running') {
          setLoading(true)
          setScanProgress({ scanned: status.progress || 0, total: status.total || defaultTotal })
          pollStatus(universe)
          if (!hasCached) setInitialLoading(false)
          return
        }
      } catch {}

      // Always fetch latest from API (DB) so completed scans are never missed
      try {
        const data = await getLatestScan(universe)
        if (!cancelled && data && !data.error) setScans(prev => ({ ...prev, [universe]: data }))
      } catch {}
      if (!cancelled) setInitialLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [universe])

  const pollRef = useRef(null)
  const universeRef = useRef(universe)
  universeRef.current = universe

  const pollStatus = useCallback((scanUniverse) => {
    const uTotal = UNIVERSES.find(u => u.key === scanUniverse)?.defaultTotal || 503
    pollRef.current = setInterval(async () => {
      try {
        const status = await getScanStatus(scanUniverse)
        if (universeRef.current === scanUniverse) {
          setScanProgress({ scanned: status.progress || 0, total: status.total || uTotal })
        }
        if (status.status === 'complete') {
          clearInterval(pollRef.current)
          const result = await getLatestScan(scanUniverse)
          if (result && !result.error) setScans(prev => ({ ...prev, [scanUniverse]: result }))
          if (universeRef.current === scanUniverse) {
            setLoading(false)
            setScanProgress({ scanned: 0, total: uTotal })
          }
        } else if (status.status === 'error') {
          clearInterval(pollRef.current)
          if (universeRef.current === scanUniverse) {
            setError(status.error || 'Scan failed')
            setLoading(false)
            setScanProgress({ scanned: 0, total: uTotal })
          }
        }
      } catch {
        clearInterval(pollRef.current)
        if (universeRef.current === scanUniverse) {
          setError('Lost connection to scan')
          setLoading(false)
          setScanProgress({ scanned: 0, total: uTotal })
        }
      }
    }, 3000)
  }, [])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleUniverseChange = (newUniverse) => {
    setUniverse(newUniverse)
    setFilters({ sort: 'drop' })
    setError(null)
    // Stop polling if switching away from a running scan's universe
    if (loading && pollRef.current) {
      clearInterval(pollRef.current)
      setLoading(false)
      setScanProgress({ scanned: 0, total: UNIVERSES.find(u => u.key === newUniverse)?.defaultTotal || 503 })
    }
  }

  const handleScan = async (type) => {
    setLoading(true)
    setError(null)
    try {
      if (type === 'daily') {
        const result = await startScan(type, universe)
        setScans(prev => ({ ...prev, [universe]: result }))
        setLoading(false)
      } else {
        await startScan(type, universe)
        pollStatus(universe)
      }
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (pollRef.current) clearInterval(pollRef.current)
    try { await resetScan(universe) } catch {}
    setLoading(false)
    setScanProgress({ scanned: 0, total: defaultTotal })
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
  const b1Count = (scan?.b1_candidates || []).length
  const b2Count = (scan?.b2_candidates || []).length
  const bothCount = useMemo(() => {
    if (!scan) return 0
    const b1Set = new Set((scan.b1_candidates || []).map(s => s.ticker))
    return (scan.b2_candidates || []).filter(s => b1Set.has(s.ticker)).length
  }, [scan])

  const universeLabel = UNIVERSES.find(u => u.key === universe)?.label || 'S&P 500'

  if (initialLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <UniverseToggle universe={universe} onChange={handleUniverseChange} />
        <div className="flex items-center gap-3">
          <div className="animate-spin w-5 h-5 border-2 rounded-full" style={{ borderColor: '#e2e4e8', borderTopColor: '#00a562' }} />
          <span style={{ color: '#6b7280' }}>Loading {universeLabel} screener data...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Universe Toggle */}
      <UniverseToggle universe={universe} onChange={handleUniverseChange} />

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>Stock Screener</h1>
          <p className="text-xs mt-1" style={{ color: '#6b7280' }}>
            {scan?.scan_date
              ? <>{universeLabel} · Last scan: {new Date(scan.scan_date).toLocaleString()} · {scan.total_scanned} scanned
                  {scan.error_count > 0 && <span style={{ color: '#d97b0e' }}> · {scan.error_count} errors</span>}</>
              : `${universeLabel} · Fail-closed gates: missing data = FAIL. Only quality passes through.`}
          </p>
        </div>
        <div className="flex gap-2">
          {loading ? (
            <button
              onClick={handleCancel}
              className="px-4 py-2 rounded text-sm font-medium text-white"
              style={{ backgroundColor: '#e5484d' }}
            >
              Cancel Scan
            </button>
          ) : (
            <>
              <button
                onClick={() => handleScan('weekly')}
                className="px-4 py-2 rounded text-sm font-medium text-white"
                style={{ backgroundColor: '#00a562' }}
              >
                Scan {universeLabel}
              </button>
              <button
                onClick={() => handleScan('daily')}
                className="px-4 py-2 rounded text-sm font-medium border"
                style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
              >
                Daily Refresh
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg p-4 mb-4 text-sm" style={{ backgroundColor: '#fef2f2', color: '#e5484d', border: '1px solid #fca5a5' }}>
          {error}
        </div>
      )}

      {loading && (
        <ScanProgress scanned={scanProgress.scanned} total={scanProgress.total} universe={universe} />
      )}

      {scan && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
            <div className="text-xs font-medium mb-1" style={{ color: '#6b7280' }}>Total Scanned</div>
            <div className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>{scan.total_scanned}</div>
          </div>
          <div className="bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
            <div className="text-xs font-medium mb-1" style={{ color: '#3b82f6' }}>B1 Candidates</div>
            <div className="text-2xl font-bold" style={{ color: '#3b82f6' }}>{b1Count}</div>
            <div className="text-[10px]" style={{ color: '#6b7280' }}>Quality + Value</div>
          </div>
          <div className="bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
            <div className="text-xs font-medium mb-1" style={{ color: '#8b5cf6' }}>B2 Candidates</div>
            <div className="text-2xl font-bold" style={{ color: '#8b5cf6' }}>{b2Count}</div>
            <div className="text-[10px]" style={{ color: '#6b7280' }}>High Growth</div>
          </div>
          <div className="bg-white rounded-lg border p-4" style={{ borderColor: '#e2e4e8' }}>
            <div className="text-xs font-medium mb-1" style={{ color: '#6b7280' }}>Pass Rate</div>
            <div className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>
              {scan.total_scanned > 0 ? ((b1Count + b2Count) / scan.total_scanned * 100).toFixed(1) : 0}%
            </div>
          </div>
        </div>
      )}

      {scan && (
        <>
          <div className="flex gap-1 mb-4 border-b" style={{ borderColor: '#e2e4e8' }}>
            {TABS.map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className="px-4 py-2 text-sm font-medium border-b-2 transition-colors"
                style={{
                  borderColor: tab === t ? '#00a562' : 'transparent',
                  color: tab === t ? '#00a562' : '#6b7280',
                }}
              >
                {t}
                {t === 'B1' && ` (${b1Count})`}
                {t === 'B2' && ` (${b2Count})`}
                {t === 'Both' && ` (${bothCount})`}
              </button>
            ))}
          </div>

          <FilterBar filters={filters} onChange={setFilters} />
          <SectorBar candidates={candidates} />

          {tab === 'Watchlist' ? (
            <div className="bg-white rounded-lg border p-6 text-center" style={{ borderColor: '#e2e4e8' }}>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                Use the Watchlist page to manage your watchlist. Daily scan refreshes data for watched stocks.
              </p>
            </div>
          ) : candidates.length === 0 ? (
            <div className="bg-white rounded-lg border p-8 text-center" style={{ borderColor: '#e2e4e8' }}>
              <div className="text-lg font-semibold mb-2" style={{ color: '#1a1a2e' }}>No candidates match</div>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                {filters.sector !== 'All Sectors' || filters.maxPE || filters.minMargin
                  ? 'Try adjusting your filters above.'
                  : `No stocks passed ${tab} gates. This is expected — fail-closed screening is strict by design.`}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {candidates.map(s => (
                <StockCard key={`${s.ticker}-${tab}`} stock={s} bucket={tab === 'Both' ? 'B1+B2' : tab} />
              ))}
            </div>
          )}
        </>
      )}

      {!scan && !loading && (
        <div className="bg-white rounded-lg border p-12 text-center" style={{ borderColor: '#e2e4e8' }}>
          <div className="text-4xl mb-4">📊</div>
          <div className="text-lg font-semibold mb-2" style={{ color: '#1a1a2e' }}>No {universeLabel} Scan Data Yet</div>
          <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: '#6b7280' }}>
            Run a scan to screen all {universeLabel} stocks through B1 (Quality + Value) and B2 (High Growth) gates.
            Fail-closed: missing data = automatic fail.
          </p>
          <button
            onClick={() => handleScan('weekly')}
            className="px-6 py-3 rounded-lg text-sm font-medium text-white"
            style={{ backgroundColor: '#00a562' }}
          >
            Scan {universeLabel}
          </button>
        </div>
      )}
    </div>
  )
}
