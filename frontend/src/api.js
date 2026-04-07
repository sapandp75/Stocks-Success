const BASE = '/api'

export async function fetchJSON(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function postJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function deleteJSON(path) {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function putJSON(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// API helpers
export const getRegime = () => fetchJSON('/regime')
export const getBreadth = () => fetchJSON('/breadth')
export const getLatestScan = () => fetchJSON('/screener/latest')
export const startScan = (type = 'weekly') => postJSON(`/screener/scan?scan_type=${type}`, {})
export const getScanStatus = () => fetchJSON('/screener/scan/status')
export const getDeepDive = (ticker) => fetchJSON(`/deep-dive/${ticker}`)
export const postDeepDive = (ticker, data) => postJSON(`/deep-dive/${ticker}`, data)
export const scanOptions = (tickers) => fetchJSON(`/options/scan?tickers=${encodeURIComponent(tickers)}`)
export const getWatchlist = () => fetchJSON('/watchlist')
export const addToWatchlist = (entry) => postJSON('/watchlist', entry)
export const removeFromWatchlist = (ticker) => deleteJSON(`/watchlist/${ticker}`)
export const getPositions = () => fetchJSON('/positions')
export const getOpenPositions = () => fetchJSON('/positions/open')
export const getPnlSummary = () => fetchJSON('/positions/summary')
export const addPosition = (entry) => postJSON('/positions', entry)
export const closePosition = (id, data) => putJSON(`/positions/${id}/close`, data)

// Research endpoints
export const fetchResearch = (ticker) => fetchJSON(`/research/${ticker}`)
export const fetchSentiment = (ticker) => fetchJSON(`/research/${ticker}/sentiment`)
export const fetchWatchlistDigest = () => fetchJSON('/watchlist/digest')
export const markDigestSeen = (eventIds) => postJSON('/research/digest/mark-seen', { event_ids: eventIds })
export const fetchEarningsCalendar = () => fetchJSON('/regime/earnings-calendar')

// AI analysis
export const triggerAiAnalysis = (ticker) => postJSON(`/deep-dive/${ticker}/analyze`, {})
