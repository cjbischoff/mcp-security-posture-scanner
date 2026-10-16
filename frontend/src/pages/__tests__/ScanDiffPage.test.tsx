import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ScanDiffPage from '../ScanDiffPage'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/scans/:id/diff/:otherId" element={<ScanDiffPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ScanDiffPage', () => {
  it('renders added section', async () => {
    renderAt('/scans/1/diff/2')
    await waitFor(() => {
      expect(screen.getByText(/Added/i)).toBeInTheDocument()
    })
  })

  it('renders drift warnings', async () => {
    renderAt('/scans/1/diff/2')
    await waitFor(() => {
      expect(screen.getByText(/Drift Detected/i)).toBeInTheDocument()
    })
  })

  it('shows drift detail text', async () => {
    renderAt('/scans/1/diff/2')
    await waitFor(() => {
      expect(screen.getByText(/changed severity/i)).toBeInTheDocument()
    })
  })

  it('shows removed section', async () => {
    renderAt('/scans/1/diff/2')
    await waitFor(() => {
      expect(screen.getByText(/Removed/i)).toBeInTheDocument()
    })
  })

  it('shows unchanged section', async () => {
    renderAt('/scans/1/diff/2')
    await waitFor(() => {
      expect(screen.getByText(/Unchanged/i)).toBeInTheDocument()
    })
  })
})
