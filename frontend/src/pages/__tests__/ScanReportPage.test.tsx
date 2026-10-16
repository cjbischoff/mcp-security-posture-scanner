import { describe, it, expect } from 'vitest'
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
})
