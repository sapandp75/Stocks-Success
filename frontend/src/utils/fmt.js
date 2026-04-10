/**
 * Shared formatting utilities for the deep dive UI.
 */

export function fmt(val, type = 'pct') {
  if (val == null) return '\u2014'
  if (type === 'pct') return `${(val * 100).toFixed(1)}%`
  if (type === 'pctSigned') return `${val >= 0 ? '+' : ''}${(val * 100).toFixed(1)}%`
  if (type === 'pe') return val.toFixed(1)
  if (type === 'ratio') return val.toFixed(2)
  if (type === 'money') return fmtMoney(val)
  if (type === 'int') return Math.round(val).toString()
  return String(val)
}

export function fmtMoney(val) {
  if (val == null) return '\u2014'
  if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`
  if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`
  if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`
  return `$${val.toFixed(0)}`
}
