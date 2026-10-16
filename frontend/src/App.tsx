import { Routes, Route, Link } from 'react-router-dom'
import NewScanPage from './pages/NewScanPage'
import ScansPage from './pages/ScansPage'
import ScanReportPage from './pages/ScanReportPage'
import ScanDiffPage from './pages/ScanDiffPage'

export default function App() {
  return (
    <div>
      <nav style={{ padding: '1rem', borderBottom: '1px solid #ccc', marginBottom: '1rem' }}>
        <Link to="/" style={{ marginRight: '1rem' }}>New Scan</Link>
        <Link to="/scans">Scans</Link>
      </nav>
      <main style={{ padding: '0 1rem' }}>
        <Routes>
          <Route path="/" element={<NewScanPage />} />
          <Route path="/scans" element={<ScansPage />} />
          <Route path="/scans/:id/report" element={<ScanReportPage />} />
          <Route path="/scans/:id/diff/:otherId" element={<ScanDiffPage />} />
        </Routes>
      </main>
    </div>
  )
}
