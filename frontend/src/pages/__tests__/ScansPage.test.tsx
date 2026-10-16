import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import ScansPage from '../ScansPage'

function renderPage() {
  return render(
    <BrowserRouter>
      <ScansPage />
    </BrowserRouter>
  )
}

describe('ScansPage', () => {
  it('renders scan rows from API', async () => {
    renderPage()
    await waitFor(() => {
      // Two mock scans share the target name "test-server"
      expect(screen.getAllByText('test-server').length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.getByText('pending-scan')).toBeInTheDocument()
  })

  it('shows status badges for each scan', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText('completed').length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('shows finding counts', async () => {
    renderPage()
    await waitFor(() => {
      expect((screen.getAllByText('6').length +
        screen.getAllByText('5').length +
        screen.getAllByText('0').length) > 0).toBe(true)
    })
  })
})
