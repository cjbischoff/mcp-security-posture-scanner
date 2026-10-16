import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError } from '../api/client'
import type { ScanDiff, Finding } from '../api/client'

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#cc0000',
  high: '#cc6600',
  medium: '#ccaa00',
  low: '#666666',
}

export default function ScanDiffPage() {
  const { id, otherId } = useParams<{ id: string; otherId: string }>()
  const [diff, setDiff] = useState<ScanDiff | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [noDiff, setNoDiff] = useState(false)

  useEffect(() => {
    if (!id || !otherId) return
    const fetchDiff = async () => {
      try {
        const data = await api.diffScans(Number(id), Number(otherId))
        setDiff(data)
        setNoDiff(data.added.length === 0 && data.removed.length === 0 && data.drift.length === 0)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load diff')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchDiff()
  }, [id, otherId])

  if (loading) return <p>Loading diff...</p>
  if (error) return <p style={{ color: 'red' }}>{error}</p>
  if (!id || !otherId) return <p>Missing scan IDs.</p>
  if (!diff) return <p>Diff not available. <Link to="/scans">Back to scans</Link></p>
  if (noDiff) return (
    <div>
      <h1>Diff: Scan #{id} vs #{otherId}</h1>
      <p>No differences found between the two scans.</p>
    </div>
  )

  return (
    <div>
      <h1>Diff: Scan #{id} vs #{otherId}</h1>

      {diff.drift.length > 0 && (
        <section style={{ marginBottom: '1rem' }}>
          <h2 style={{ color: '#cc6600' }}>⚠ Drift Detected</h2>
          {diff.drift.map((d, i) => (
            <div key={i} style={{ backgroundColor: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px', padding: '8px', marginBottom: '4px' }}>
              <strong>{d.rule_id}</strong> on <em>{d.subject || '(global)'}</em>: {d.detail}
            </div>
          ))}
        </section>
      )}

      <DiffSection title="Added" findings={diff.added} bgColor="#d4edda" />
      <DiffSection title="Removed" findings={diff.removed} bgColor="#f8d7da" />
      <DiffSection title="Unchanged" findings={diff.unchanged} bgColor="#f8f9fa" />
    </div>
  )
}

function DiffSection({ title, findings, bgColor }: { title: string; findings: Finding[]; bgColor: string }) {
  if (findings.length === 0) return null
  return (
    <section style={{ marginBottom: '1rem' }}>
      <h2>{title} ({findings.length})</h2>
      {findings.map(f => (
        <div key={f.id} style={{ backgroundColor: bgColor, border: '1px solid #ddd', borderRadius: '4px', padding: '8px', marginBottom: '4px' }}>
          <span style={{ backgroundColor: SEVERITY_COLORS[f.severity] || '#999', color: '#fff', padding: '2px 6px', borderRadius: '3px', fontSize: '0.8em', fontWeight: 'bold', marginRight: '8px' }}>{f.severity}</span>
          <strong>{f.rule_id}</strong>
          {f.subject && <span style={{ marginLeft: '8px', color: '#666' }}>on <em>{f.subject}</em></span>}
          <div style={{ marginTop: '4px', fontSize: '0.9em' }}>{f.description}</div>
        </div>
      ))}
    </section>
  )
}
