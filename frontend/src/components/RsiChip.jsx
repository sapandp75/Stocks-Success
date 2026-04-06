export default function RsiChip({ rsi }) {
  if (rsi == null) return null

  const val = Math.round(rsi)
  let bg = '#6b7280'
  if (rsi < 30) bg = '#00a562'
  else if (rsi > 70) bg = '#d97b0e'

  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-bold text-white"
      style={{ backgroundColor: bg }}
    >
      RSI {val}
    </span>
  )
}
