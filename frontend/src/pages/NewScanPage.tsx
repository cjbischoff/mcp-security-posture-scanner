import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api/client'

export default function NewScanPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [transport, setTransport] = useState<'stdio' | 'http'>('stdio')
  const [command, setCommand] = useState('')
  const [args, setArgs] = useState('')
  const [url, setUrl] = useState('')
  const [allowExternal, setAllowExternal] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setError('Name is required'); return }
    setLoading(true)
    setError('')

    try {
      const target: Parameters<typeof api.createScan>[0] = {
        name: name.trim(),
        transport,
      }
      if (transport === 'stdio') {
        target.command = command.trim()
        target.args = args.trim() ? args.split(/\s+/) : []
      } else {
        target.url = url.trim()
        target.allow_external = allowExternal
      }

      const scan = await api.createScan(target)
      navigate(`/scans/${scan.id}/report`)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to create scan')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>New Scan</h1>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <form onSubmit={handleSubmit}>
        <div><label>Name: <input value={name} onChange={e => setName(e.target.value)} required disabled={loading} /></label></div>
        <div><label>Transport:
          <select value={transport} onChange={e => setTransport(e.target.value as 'stdio' | 'http')} disabled={loading}>
            <option value="stdio">stdio</option>
            <option value="http">HTTP</option>
          </select>
        </label></div>
        {transport === 'stdio' ? (
          <>
            <div><label>Command: <input value={command} onChange={e => setCommand(e.target.value)} disabled={loading} /></label></div>
            <div><label>Args: <input value={args} onChange={e => setArgs(e.target.value)} placeholder="space-separated" disabled={loading} /></label></div>
          </>
        ) : (
          <>
            <div><label>URL: <input value={url} onChange={e => setUrl(e.target.value)} disabled={loading} /></label></div>
            <div><label><input type="checkbox" checked={allowExternal} onChange={e => setAllowExternal(e.target.checked)} disabled={loading} /> Allow external target</label></div>
          </>
        )}
        <button type="submit" disabled={loading}>{loading ? 'Scanning...' : 'Start Scan'}</button>
      </form>
    </div>
  )
}
