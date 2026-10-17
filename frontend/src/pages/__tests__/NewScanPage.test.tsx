import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import NewScanPage from '../NewScanPage'

function renderPage() {
  return render(
    <BrowserRouter>
      <NewScanPage />
    </BrowserRouter>
  )
}

describe('NewScanPage', () => {
  it('renders form fields', () => {
    renderPage()
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/transport/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/command/i)).toBeInTheDocument()
  })

  it('shows command field for stdio, hides URL', () => {
    renderPage()
    expect(screen.getByLabelText(/command/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/url/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/allow external/i)).not.toBeInTheDocument()
  })

  it('shows URL and consent for http transport', async () => {
    renderPage()
    const select = screen.getByLabelText(/transport/i)
    await userEvent.selectOptions(select, 'http')

    expect(screen.getByLabelText(/url/i)).toBeInTheDocument()
    expect(screen.getByText(/allow external/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/command/i)).not.toBeInTheDocument()
  })

  it('requires name via HTML5 validation', () => {
    renderPage()
    const input = screen.getByLabelText(/name/i)
    expect(input).toHaveAttribute('required')
  })

  it('has a submit button', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /start scan/i })).toBeInTheDocument()
  })

  it('hints that the fixture command is vulnerable-demo', () => {
    renderPage()
    expect(screen.getByLabelText(/command/i)).toHaveAttribute('placeholder', expect.stringMatching(/vulnerable-demo/))
  })
})
