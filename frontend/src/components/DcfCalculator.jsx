import { useState } from 'react'

export default function DcfCalculator({ defaults }) {
  const [inputs, setInputs] = useState({
    starting_fcf: defaults?.starting_fcf || 1000000000,
    growth_1_5: defaults?.growth_1_5 || 0.12,
    growth_6_10: defaults?.growth_6_10 || 0.07,
    terminal_growth: 0.025,
    wacc: 0.10,
    shares: defaults?.shares || 1000000000,
    net_debt: defaults?.net_debt || 0,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const calculate = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        starting_fcf: inputs.starting_fcf,
        growth_rate_1_5: inputs.growth_1_5,
        growth_rate_6_10: inputs.growth_6_10,
        terminal_growth: inputs.terminal_growth,
        wacc: inputs.wacc,
        shares_outstanding: inputs.shares,
        net_debt: inputs.net_debt,
      })
      // Calculate locally using the formula
      const fcfs = []
      let fcf = parseFloat(inputs.starting_fcf)
      const g1 = parseFloat(inputs.growth_1_5)
      const g2 = parseFloat(inputs.growth_6_10)
      const tg = parseFloat(inputs.terminal_growth)
      const wacc = parseFloat(inputs.wacc)
      const shares = parseFloat(inputs.shares)
      const netDebt = parseFloat(inputs.net_debt)

      for (let y = 1; y <= 5; y++) { fcf *= (1 + g1); fcfs.push({ year: y, fcf }) }
      for (let y = 6; y <= 10; y++) {
        const blend = (y - 5) / 5
        const rate = g2 * (1 - blend) + tg * blend
        fcf *= (1 + rate)
        fcfs.push({ year: y, fcf })
      }

      const pvFcfs = fcfs.reduce((sum, p) => sum + p.fcf / Math.pow(1 + wacc, p.year), 0)
      const terminalValue = wacc > tg ? (fcf * (1 + tg)) / (wacc - tg) : 0
      const pvTerminal = terminalValue / Math.pow(1 + wacc, 10)
      const ev = pvFcfs + pvTerminal
      const equity = ev - netDebt
      const perShare = shares > 0 ? equity / shares : 0
      const terminalPct = ev > 0 ? pvTerminal / ev : 0

      setResult({
        intrinsic_value: perShare.toFixed(2),
        enterprise_value: (ev / 1e9).toFixed(2),
        terminal_pct: (terminalPct * 100).toFixed(1),
        terminal_warning: terminalPct > 0.5,
      })
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const set = (key, val) => setInputs(prev => ({ ...prev, [key]: val }))

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {[
          { label: 'Starting FCF', key: 'starting_fcf', fmt: 'number' },
          { label: 'Growth Yr 1-5', key: 'growth_1_5', fmt: 'pct' },
          { label: 'Growth Yr 6-10', key: 'growth_6_10', fmt: 'pct' },
          { label: 'Terminal Growth', key: 'terminal_growth', fmt: 'pct' },
          { label: 'WACC (fixed)', key: 'wacc', fmt: 'pct', disabled: true },
          { label: 'Shares Outstanding', key: 'shares', fmt: 'number' },
          { label: 'Net Debt', key: 'net_debt', fmt: 'number' },
        ].map(f => (
          <div key={f.key}>
            <label className="text-[11px] block mb-1" style={{ color: '#6b7280' }}>{f.label}</label>
            <input
              type="number"
              step={f.fmt === 'pct' ? '0.01' : '1000000'}
              className="border rounded px-2 py-1 text-sm w-full disabled:bg-gray-100"
              style={{ borderColor: '#e2e4e8' }}
              value={inputs[f.key]}
              onChange={e => set(f.key, e.target.value)}
              disabled={f.disabled}
            />
          </div>
        ))}
        <div className="flex items-end">
          <button
            onClick={calculate}
            disabled={loading}
            className="px-4 py-1.5 rounded text-sm font-medium text-white w-full"
            style={{ backgroundColor: '#00a562' }}
          >
            Calculate
          </button>
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-3 gap-4 p-3 rounded" style={{ backgroundColor: '#f7f8fa' }}>
          <div>
            <div className="text-xs" style={{ color: '#6b7280' }}>Intrinsic Value/Share</div>
            <div className="text-xl font-bold" style={{ color: '#1a1a2e' }}>${result.intrinsic_value}</div>
          </div>
          <div>
            <div className="text-xs" style={{ color: '#6b7280' }}>Enterprise Value</div>
            <div className="text-xl font-bold" style={{ color: '#1a1a2e' }}>${result.enterprise_value}B</div>
          </div>
          <div>
            <div className="text-xs" style={{ color: '#6b7280' }}>Terminal Value %</div>
            <div className="text-xl font-bold" style={{ color: result.terminal_warning ? '#e5484d' : '#1a1a2e' }}>
              {result.terminal_pct}%
            </div>
            {result.terminal_warning && (
              <div className="text-[10px]" style={{ color: '#d97b0e' }}>Exceeds 50% — review assumptions</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
