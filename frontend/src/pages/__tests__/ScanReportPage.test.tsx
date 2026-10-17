import { describe, it, expect, vi, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../api/mocks/server'
import { mockReport, mockScan1 } from '../../api/mocks/data'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ScanReportPage from '../ScanReportPage'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/scans/:id/report" element={<ScanReportPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ScanReportPage', () => {
  it('renders findings', async () => {
    renderAt('/scans/1/report')
    const mcp001 = await screen.findByText('MCP-001')
    expect(mcp001).toBeInTheDocument()
    const mcp002 = await screen.findByText('MCP-002')
    expect(mcp002).toBeInTheDocument()
  })

  it('shows severity badges', async () => {
    renderAt('/scans/1/report')
    const critical = await screen.findByText(/critical.*2/i)
    expect(critical).toBeInTheDocument()
    const high = await screen.findByText(/high.*2/i)
    expect(high).toBeInTheDocument()
    const medium = await screen.findByText(/medium.*2/i)
    expect(medium).toBeInTheDocument()
  })

  it('shows remediation text', async () => {
    renderAt('/scans/1/report')
    // Multiple findings share similar remediation text; just verify at least one renders
    const fixes = await screen.findAllByText(/Remove injection patterns/i)
    expect(fixes.length).toBeGreaterThanOrEqual(1)
  })

  it('shows subject for findings', async () => {
    renderAt('/scans/1/report')
    const subjects = await screen.findAllByText(/Subject:/i)
    expect(subjects.length).toBeGreaterThanOrEqual(1)
  })

  it('shows not completed for pending scan', async () => {
    renderAt('/scans/3/report')
    const msg = await screen.findByText(/still running/i)
    expect(msg).toBeInTheDocument()
  })

  it('shows the error for a failed scan, not "still running"', async () => {
    renderAt('/scans/9/report')
    expect(await screen.findByText(/Scan failed: Connection refused/)).toBeInTheDocument()
    expect(screen.queryByText(/still running/i)).not.toBeInTheDocument()
  })

  describe('polling', () => {
    afterEach(() => { vi.useRealTimers() })

    it('polls while running and renders the report once completed', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      let calls = 0
      server.use(http.get('/api/scans/:id/report', () => {
        calls++
        return calls < 3
          ? HttpResponse.json({ detail: 'Scan not finished yet' }, { status: 409 })
          : HttpResponse.json(mockReport)
      }))
      renderAt('/scans/1/report')
      expect(await screen.findByText(/still running/i)).toBeInTheDocument()
      await vi.advanceTimersByTimeAsync(1500)
      await vi.advanceTimersByTimeAsync(1500)
      expect(await screen.findByText('MCP-001')).toBeInTheDocument()
      expect(calls).toBe(3)
      await vi.advanceTimersByTimeAsync(5000)
      expect(calls).toBe(3)
    })

    it('stops polling on unmount', async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true })
      let calls = 0
      server.use(http.get('/api/scans/:id/report', () => {
        calls++
        return HttpResponse.json({ detail: 'Scan not finished yet' }, { status: 409 })
      }))
      const { unmount } = renderAt('/scans/3/report')
      await screen.findByText(/still running/i)
      unmount()
      await vi.advanceTimersByTimeAsync(6000)
      expect(calls).toBe(1)
    })
  })

  it('links to the diff page for other completed scans of the same target', async () => {
    renderAt('/scans/1/report')
    const link = await screen.findByRole('link', { name: /#2/ })
    expect(link).toHaveAttribute('href', '/scans/1/diff/2')
  })

  it('shows a hint when no other scan of the target exists', async () => {
    server.use(http.get('/api/scans', () => HttpResponse.json([mockScan1])))
    renderAt('/scans/1/report')
    expect(await screen.findByText(/no other completed scan of this target/i)).toBeInTheDocument()
  })
})
