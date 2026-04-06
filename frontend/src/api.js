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
export const getLatestScan = () => fetchJSON('/screener/latest')
export const runScan = (type = 'weekly') => fetchJSON(`/screener/scan?scan_type=${type}`)
export const getDeepDive = (ticker) => fetchJSON(`/deep-dive/${ticker}`)
export const postDeepDive = (ticker, data) => postJSON(`/deep-dive/${ticker}`, data)
export const scanOptions = (tickers) => fetchJSON(`/options/scan?tickers=${tickers}`)
export const getWatchlist = () => fetchJSON('/watchlist')
export const addToWatchlist = (entry) => postJSON('/watchlist', entry)
export const removeFromWatchlist = (ticker) => deleteJSON(`/watchlist/${ticker}`)
export const getPositions = () => fetchJSON('/positions')
export const getOpenPositions = () => fetchJSON('/positions/open')
export const getPnlSummary = () => fetchJSON('/positions/summary')
export const addPosition = (entry) => postJSON('/positions', entry)
export const closePosition = (id, data) => putJSON(`/positions/${id}/close`, data)
