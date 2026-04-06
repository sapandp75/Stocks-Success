export default function WarningBadge({ warning }) {
  const isRed = ['EARNINGS SOON', 'IV CRUSH RISK', 'CASH BURN'].includes(warning)
  const bg = isRed ? '#e5484d' : '#d97b0e'
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[10px] font-semibold text-white whitespace-nowrap"
      style={{ backgroundColor: bg }}
    >
      {warning}
    </span>
  )
}
