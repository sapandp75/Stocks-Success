import { NavLink } from 'react-router-dom'
import { useRegime } from '../RegimeContext'
import RegimeBadge from './RegimeBadge'

const links = [
  ['/', 'Regime'],
  ['/screener', 'Screener'],
  ['/deep-dive', 'Deep Dive'],
  ['/options', 'Options'],
  ['/breadth', 'Breadth'],
  ['/watchlist', 'Watchlist'],
  ['/positions', 'Positions'],
]

export default function Navbar() {
  const { data } = useRegime()
  const regime = data?.regime

  return (
    <nav className="bg-white border-b px-6 py-3 flex gap-6 items-center" style={{ borderColor: '#e2e4e8' }}>
      <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>CIP</span>
      {links.map(([to, label]) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `text-sm font-medium ${isActive ? 'text-[#00a562]' : 'text-[#6b7280] hover:text-[#1a1a2e]'}`
          }
        >
          {label}
        </NavLink>
      ))}
      <div className="ml-auto">
        {regime && <RegimeBadge verdict={regime.verdict} vix={regime.vix} />}
      </div>
    </nav>
  )
}
