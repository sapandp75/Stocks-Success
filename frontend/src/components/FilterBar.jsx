const SECTORS = [
  'All Sectors', 'Technology', 'Healthcare', 'Financial Services',
  'Consumer Cyclical', 'Communication Services', 'Industrials',
  'Consumer Defensive', 'Energy', 'Basic Materials', 'Real Estate', 'Utilities',
]

const SORTS = [
  { value: 'drop', label: 'Most Beaten Down' },
  { value: 'fcf_yield', label: 'Highest FCF Yield' },
  { value: 'pe', label: 'Cheapest P/E' },
  { value: 'margin', label: 'Highest Margin' },
  { value: 'growth', label: 'Fastest Growth' },
]

export default function FilterBar({ filters, onChange }) {
  const set = (key, val) => onChange({ ...filters, [key]: val })

  return (
    <div className="flex flex-wrap gap-3 mb-4">
      <select
        className="border rounded px-2 py-1 text-sm bg-white"
        style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
        value={filters.sector || 'All Sectors'}
        onChange={e => set('sector', e.target.value)}
      >
        {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      <select
        className="border rounded px-2 py-1 text-sm bg-white"
        style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
        value={filters.maxPE || ''}
        onChange={e => set('maxPE', e.target.value)}
      >
        <option value="">Max Fwd P/E</option>
        <option value="15">P/E &lt; 15</option>
        <option value="20">P/E &lt; 20</option>
        <option value="30">P/E &lt; 30</option>
        <option value="50">P/E &lt; 50</option>
      </select>

      <select
        className="border rounded px-2 py-1 text-sm bg-white"
        style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
        value={filters.minMargin || ''}
        onChange={e => set('minMargin', e.target.value)}
      >
        <option value="">Min Op Margin</option>
        <option value="0.20">20%+</option>
        <option value="0.30">30%+</option>
        <option value="0.40">40%+</option>
      </select>

      <select
        className="border rounded px-2 py-1 text-sm bg-white"
        style={{ borderColor: '#e2e4e8', color: '#1a1a2e' }}
        value={filters.sort || 'drop'}
        onChange={e => set('sort', e.target.value)}
      >
        {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
    </div>
  )
}
