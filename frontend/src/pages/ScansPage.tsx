import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Scan } from '../api/client'

const STATUS_COLORS: Record<string, string> = {
  pending: '#999',
  running: '#0066cc',
  completed: '#00aa00',
  failed: '#cc0000',
}

export default function ScansPage() {
  const [scans, setScans] = useState<Scan[]>([])
  const [error, setError] = useState('')

  const fetchScans = useCallback(async () => {
    try {
      const data = await api.listScans()
      setScans(data)
    } catch {
      setError('Failed to load scans')
    }
  }, [])

  useEffect(() => { fetchScans() }, [fetchScans])

  useEffect(() => {
    const hasPending = scans.some(s => s.status === 'pending' || s.status === 'running')
    if (!hasPending) return
    const interval = setInterval(fetchScans, 3000)
    return () => clearInterval(interval)
  }, [scans, fetchScans])

  if (error) return <p style={{ color: 'red' }}>{error}</p>

  if (scans.length === 0) return <p>No scans yet. <Link to="/">Create your first scan.</Link></p>

  return (
    <div>
      <h1>Scans</h1>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr>
          <th style={thStyle}>ID</th>
          <th style={thStyle}>Target</th>
          <th style={thStyle}>Status</th>
          <th style={thStyle}>Findings</th>
          <th style={thStyle}>Created</th>
        </tr></thead>
        <tbody>
          {scans.map(scan => (
            <tr key={scan.id} style={{ cursor: 'pointer' }} onClick={() => window.location.href = `/scans/${scan.id}/report`}>
              <td style={tdStyle}>{scan.id}</td>
              <td style={tdStyle}>{scan.target.name}</td>
              <td style={{ ...tdStyle, color: STATUS_COLORS[scan.status] || '#000' }}>{scan.status}</td>
              <td style={tdStyle}>{scan.finding_count}</td>
              <td style={tdStyle}>{new Date(scan.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const thStyle: React.CSSProperties = { textAlign: 'left', borderBottom: '2px solid #ddd', padding: '8px' }
const tdStyle: React.CSSProperties = { borderBottom: '1px solid #eee', padding: '8px' }
