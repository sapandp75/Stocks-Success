import { AreaChart, Area, ResponsiveContainer } from 'recharts'

export default function TrendSparkline({ data, color, label }) {
  if (!data || data.length < 2) return null

  const nums = data.filter(v => v != null)
  if (nums.length < 2) return null

  const trendUp = nums[nums.length - 1] >= nums[0]
  const lineColor = color || (trendUp ? '#00a562' : '#e5484d')
  const chartData = nums.map((v, i) => ({ i, v }))

  return (
    <div>
      {label && <div className="text-[10px] mb-0.5" style={{ color: '#6b7280' }}>{label}</div>}
      <ResponsiveContainer width={120} height={60} debounce={200}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.3} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="v" stroke={lineColor} fill={`url(#grad-${label})`} strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
