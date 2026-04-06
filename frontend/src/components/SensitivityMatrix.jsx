export default function SensitivityMatrix({ matrix, currentPrice }) {
  if (!matrix || matrix.length === 0) return null

  return (
    <div>
      <div className="text-xs mb-2" style={{ color: '#6b7280' }}>
        WACC fixed at {((matrix[0]?.wacc ?? 0.10) * 100).toFixed(0)}% (spec rule). Varies growth only.
      </div>
      <div className="overflow-x-auto">
        <table className="text-sm w-full">
          <thead>
            <tr>
              <th className="py-1 px-2 text-left text-xs" style={{ color: '#6b7280' }}>Growth Yr 1-5</th>
              {matrix[0].values.map((v, i) => (
                <th key={i} className="py-1 px-2 text-center text-xs" style={{ color: '#6b7280' }}>
                  Yr 6-10: {(v.growth_6_10 * 100).toFixed(0)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, ri) => (
              <tr key={ri}>
                <td className="py-1 px-2 font-medium text-xs" style={{ color: '#1a1a2e' }}>
                  {(row.growth_1_5 * 100).toFixed(0)}%
                </td>
                {row.values.map((v, ci) => {
                  const above = currentPrice && v.per_share > currentPrice
                  return (
                    <td
                      key={ci}
                      className="py-1 px-2 text-center font-semibold text-xs rounded"
                      style={{
                        backgroundColor: above ? '#dcfce7' : '#fef2f2',
                        color: above ? '#00a562' : '#e5484d',
                      }}
                    >
                      ${v.per_share}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
