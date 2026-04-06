import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import RegimePage from './pages/RegimePage'
import ScreenerPage from './pages/ScreenerPage'
import DeepDivePage from './pages/DeepDivePage'
import OptionsPage from './pages/OptionsPage'
import WatchlistPage from './pages/WatchlistPage'
import PositionsPage from './pages/PositionsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen" style={{ backgroundColor: '#f0f1f3', color: '#1a1a2e' }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<RegimePage />} />
          <Route path="/screener" element={<ScreenerPage />} />
          <Route path="/deep-dive" element={<DeepDivePage />} />
          <Route path="/deep-dive/:ticker" element={<DeepDivePage />} />
          <Route path="/options" element={<OptionsPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/positions" element={<PositionsPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
