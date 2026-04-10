import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from 'recharts'

export default function QuarterlyBarChart({ data, label, valueFormatter }) {
  if (!data || data.length === 0) return null

  // Filter out quarters with null values, keep most recent first
  const valid = data.filter(d => d.value != null)
  if (valid.length === 0) return null

  const fmtVal = valueFormatter || (v => v?.toLocaleString())

  const chartData = valid.map(d => {
    // Use yoy if available, fall back to qoq
    const growthVal = d.yoy ?? d.qoq
    const suffix = d.yoy != null ? '' : d.qoq != null ? 'q' : ''
    return {
      ...d,
      fill: growthVal != null ? (growthVal >= 0 ? '#00a562' : '#e5484d') : '#94a3b8',
      growthLabel: growthVal != null
        ? `${growthVal >= 0 ? '+' : ''}${(growthVal * 100).toFixed(1)}%${suffix}`
        : '',
    }
  })

  return (
    <div>
      {label && <div className="text-xs font-medium mb-2" style={{ color: '#1a1a2e' }}>{label}</div>}
      <ResponsiveContainer width="100%" height={200} debounce={200}>
        <BarChart data={chartData} margin={{ top: 25, right: 10, left: 10, bottom: 5 }}>
          <XAxis dataKey="quarter" tick={{ fontSize: 10, fill: '#6b7280' }} />
          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} tickFormatter={fmtVal} width={60} />
          <Tooltip
            formatter={(value, name) => [fmtVal(value), 'Value']}
            contentStyle={{ fontSize: 12, borderColor: '#e2e4e8' }}
          />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {chartData.map((d, i) => <Cell key={i} fill={d.fill} />)}
            <LabelList dataKey="growthLabel" position="top" style={{ fontSize: 9, fill: '#6b7280' }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
