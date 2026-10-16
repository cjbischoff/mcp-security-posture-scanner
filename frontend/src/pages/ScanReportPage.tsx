import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Report, Finding } from '../api/client'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#cc0000',
  high: '#cc6600',
  medium: '#ccaa00',
  low: '#666666',
}

export default function ScanReportPage() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [notReady, setNotReady] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    const fetchReport = async () => {
      try {
        const data = await api.getReport(Number(id))
        setReport(data)
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setNotReady(true)
        } else {
          setError('Failed to load report')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchReport()
  }, [id])

  if (loading) return <p>Loading report...</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>
  if (!id) return <p>No scan ID provided.</p>
  if (notReady) return <p>Scan is still running. <Link to="/scans">Back to scans</Link></p>
  if (!report) return <p>Scan not found. <Link to="/scans">Back to scans</Link></p>

  const sortedFindings: Finding[] = [...report.findings].sort(
    (a, b) => sevOrder(a.severity) - sevOrder(b.severity)
  )

  if (sortedFindings.length === 0) return (
    <div>
      <h1>Scan Report #{id}</h1>
      <p style={{ color: '#00aa00', fontSize: '1.2em' }}>✓ No findings — clean scan</p>
    </div>
  )

  return (
    <div>
      <h1>Scan Report #{id}</h1>
      <div style={{ marginBottom: '1rem' }}>
        {Object.entries(report.summary).map(([sev, count]) => (
          <span key={sev} style={{
            display: 'inline-block',
            padding: '4px 10px',
            margin: '2px',
            borderRadius: '4px',
            backgroundColor: SEVERITY_COLORS[sev] || '#999',
            color: '#fff',
            fontWeight: 'bold',
          }}>
            {sev}: {count}
          </span>
        ))}
      </div>
      {sortedFindings.map(f => (
        <div key={f.id} style={{
          border: '1px solid #ddd',
          borderRadius: '6px',
          padding: '12px',
          marginBottom: '8px',
          borderLeft: `4px solid ${SEVERITY_COLORS[f.severity] || '#999'}`,
        }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{
              backgroundColor: SEVERITY_COLORS[f.severity] || '#999',
              color: '#fff',
              padding: '2px 6px',
              borderRadius: '3px',
              fontSize: '0.8em',
              fontWeight: 'bold',
            }}>{f.severity}</span>
            <span style={{ fontWeight: 'bold' }}>{f.rule_id}</span>
            <span style={{ color: '#666' }}>{f.title}</span>
          </div>
          {f.subject && <div style={{ color: '#444', fontSize: '0.9em' }}>Subject: {f.subject}</div>}
          <div style={{ marginTop: '4px' }}>{f.description}</div>
          <div style={{ marginTop: '4px', color: '#006600', fontSize: '0.9em' }}>Fix: {f.remediation}</div>
        </div>
      ))}
    </div>
  )
}

function sevOrder(s: string): number {
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
  return order[s] ?? 99
}
