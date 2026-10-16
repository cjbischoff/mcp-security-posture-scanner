import { describe, it, expect } from 'vitest'
import { api, ApiError } from '../client'

describe('api client', () => {
  it('health returns ok', async () => {
    const result = await api.health()
    expect(result.status).toBe('ok')
  })

  it('createScan returns scan with id', async () => {
    const scan = await api.createScan({
      name: 'test',
      transport: 'stdio',
      command: 'python',
      args: ['-m', 'server'],
    })
    expect(scan.id).toBeGreaterThan(0)
    expect(scan.status).toBe('running')
  })

  it('createScan rejects external without consent', async () => {
    await expect(
      api.createScan({
        name: 'external-test',
        transport: 'http',
        url: 'http://example.com/mcp',
      })
    ).rejects.toThrow(ApiError)
  })

  it('listScans returns array', async () => {
    const scans = await api.listScans()
    expect(Array.isArray(scans)).toBe(true)
    expect(scans.length).toBeGreaterThan(0)
  })

  it('getReport returns findings + summary', async () => {
    const report = await api.getReport(1)
    expect(report.findings).toBeDefined()
    expect(report.summary).toBeDefined()
    expect(report.findings.length).toBeGreaterThan(0)
    expect(typeof report.summary.critical).toBe('number')
  })

  it('getReport returns 409 for pending scan', async () => {
    await expect(api.getReport(3)).rejects.toThrow(ApiError)
  })

  it('diffScans returns diff with sections', async () => {
    const diff = await api.diffScans(1, 2)
    expect(diff.added).toBeDefined()
    expect(diff.removed).toBeDefined()
    expect(diff.unchanged).toBeDefined()
    expect(diff.drift).toBeDefined()
  })

  it('diffScans returns 409 for mismatched scans', async () => {
    await expect(api.diffScans(1, 99)).rejects.toThrow(ApiError)
  })
})
