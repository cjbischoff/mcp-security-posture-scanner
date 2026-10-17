import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { Report, Finding, Scan } from '../api/client'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#cc0000',
  high: '#cc6600',
  medium: '#ccaa00',
  low: '#666666',
}

/** Delay between report fetches while the scan is pending or running. */
const POLL_MS = 1500

/**
 * Report page for one scan. Polls the report endpoint every {@link POLL_MS}
 * while the API answers 409 (pending/running), then shows findings, or the
 * error for a failed scan, plus links to diff against sibling scans.
 *
 * @returns The report view for the `:id` route param.
 * @example
 * <Route path="/scans/:id/report" element={<ScanReportPage />} />
 */
export default function ScanReportPage() {
  const { id } = useParams<{ id: string }>()
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [notReady, setNotReady] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined
    const fetchReport = async () => {
      try {
        const data = await api.getReport(Number(id))
        if (cancelled) return
        setReport(data)
        setNotReady(false)
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 409) {
          setNotReady(true)
          timer = setTimeout(fetchReport, POLL_MS)
        } else {
          setError('Failed to load report')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchReport()
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [id])

  if (loading) return <p>Loading report...</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>
  if (!id) return <p>No scan ID provided.</p>
  if (notReady) return <p>Scan is still running... <Link to="/scans">Back to scans</Link></p>
  if (!report) return <p>Scan not found. <Link to="/scans">Back to scans</Link></p>
  if (report.scan.status === 'failed') return (
    <div>
      <h1>Scan Report #{id}</h1>
      <p style={{ color: 'red' }}>Scan failed: {report.scan.error || 'unknown error'}</p>
    </div>
  )

  const sortedFindings: Finding[] = [...report.findings].sort(
    (a, b) => sevOrder(a.severity) - sevOrder(b.severity)
  )

  if (sortedFindings.length === 0) return (
    <div>
      <h1>Scan Report #{id}</h1>
      <p style={{ color: '#00aa00', fontSize: '1.2em' }}>✓ No findings — clean scan</p>
      <CompareWith scan={report.scan} />
    </div>
  )

  return (
    <div>
      <h1>Scan Report #{id}</h1>
      <CompareWith scan={report.scan} />
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

/**
 * "Compare with" links to the diff page for every other completed scan of
 * the same target, or a hint when there is none.
 *
 * @param props.scan - The completed scan being viewed.
 * @returns A paragraph of diff links, or nothing until the scan list loads.
 * @example
 * <CompareWith scan={report.scan} />
 */
function CompareWith({ scan }: { scan: Scan }) {
  const [others, setOthers] = useState<Scan[] | null>(null)

  useEffect(() => {
    api.listScans()
      .then(all => setOthers(all.filter(s =>
        s.id !== scan.id && s.target.id === scan.target.id && s.status === 'completed')))
      .catch(() => setOthers([]))
  }, [scan.id, scan.target.id])

  if (!others) return null
  if (others.length === 0) return <p style={{ color: '#666' }}>No other completed scan of this target to compare with yet.</p>
  return (
    <p>
      Compare with:{' '}
      {others.map(o => (
        <Link key={o.id} to={`/scans/${Math.min(scan.id, o.id)}/diff/${Math.max(scan.id, o.id)}`} style={{ marginRight: '0.5rem' }}>
          #{o.id}
        </Link>
      ))}
    </p>
  )
}

function sevOrder(s: string): number {
  const order: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 }
  return order[s] ?? 99
}
