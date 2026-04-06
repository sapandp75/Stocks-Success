import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'

function Placeholder({ title }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-koyfin-text">{title}</h1>
      <p className="text-koyfin-muted mt-2">Coming soon.</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-koyfin-bg">
        <nav className="bg-koyfin-card border-b border-koyfin-border px-6 py-3 flex gap-6 items-center">
          <span className="font-bold text-lg text-koyfin-text">CIP</span>
          {[
            ['/', 'Regime'],
            ['/screener', 'Screener'],
            ['/deep-dive', 'Deep Dive'],
            ['/options', 'Options'],
            ['/watchlist', 'Watchlist'],
            ['/positions', 'Positions'],
          ].map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `text-sm font-medium ${isActive ? 'text-koyfin-green' : 'text-koyfin-muted hover:text-koyfin-text'}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <Routes>
          <Route path="/" element={<Placeholder title="Market Regime" />} />
          <Route path="/screener" element={<Placeholder title="Stock Screener" />} />
          <Route path="/deep-dive" element={<Placeholder title="Deep Dive" />} />
          <Route path="/deep-dive/:ticker" element={<Placeholder title="Deep Dive" />} />
          <Route path="/options" element={<Placeholder title="Options Scanner" />} />
          <Route path="/watchlist" element={<Placeholder title="Watchlist" />} />
          <Route path="/positions" element={<Placeholder title="Positions" />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
