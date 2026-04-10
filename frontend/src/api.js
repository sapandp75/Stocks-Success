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

export async function downloadDeepDiveExport(ticker) {
  const res = await fetch(`${BASE}/deep-dive/${ticker}/export`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)

  const disposition = res.headers.get('content-disposition') || ''
  const filenameMatch = disposition.match(/filename="([^"]+)"/i)
  const filename = filenameMatch?.[1] || `deep-dive-${ticker}.json`

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// API helpers
export const getRegime = () => fetchJSON('/regime')
export const getBreadth = () => fetchJSON('/breadth')
export const getLatestScan = (universe = 'spx') => fetchJSON(`/screener/latest?universe=${universe}`)
export const startScan = (type = 'weekly', universe = 'spx') => postJSON(`/screener/scan?scan_type=${type}&universe=${universe}`, {})
export const getScanStatus = (universe = 'spx') => fetchJSON(`/screener/scan/status?universe=${universe}`)
export const resetScan = (universe = 'spx') => postJSON(`/screener/scan/reset?universe=${universe}`, {})
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
