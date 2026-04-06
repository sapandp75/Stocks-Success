import { useState } from 'react'

export default function CollapsibleSection({ title, number, accentColor = '#e2e4e8', defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="bg-white rounded-lg border overflow-hidden" style={{ borderColor: '#e2e4e8', borderLeftWidth: 3, borderLeftColor: accentColor }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-[#f7f8fa] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ backgroundColor: accentColor, color: '#fff' }}>
            {number}
          </span>
          <span className="font-semibold text-sm" style={{ color: '#1a1a2e' }}>{title}</span>
        </div>
        <span className="text-sm" style={{ color: '#6b7280' }}>{open ? '▼' : '▶'}</span>
      </button>
      {open && (
        <div className="px-5 pb-4 pt-1 border-t" style={{ borderColor: '#e2e4e8' }}>
          {children}
        </div>
      )}
    </div>
  )
}
