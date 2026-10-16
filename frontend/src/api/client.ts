/// <reference types="vite/client" />

const BASE_URL = '/api'

export interface ScanTargetCreate {
  name: string
  transport: 'stdio' | 'http'
  command?: string
  args?: string[]
  url?: string
  allow_external?: boolean
}

export interface ScanTarget {
  id: number
  name: string
  transport: string
  command?: string | null
  args?: string[]
  url?: string | null
  allow_external: boolean
}

export interface Scan {
  id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: string | null
  target: ScanTarget
  created_at: string
  finished_at?: string | null
  finding_count: number
}

export interface Finding {
  id: number
  rule_id: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  remediation: string
  subject?: string | null
}

export interface Report {
  scan: Scan
  findings: Finding[]
  summary: Record<string, number>
}

export interface ScanDiff {
  scan_id: number
  other_id: number
  added: Finding[]
  removed: Finding[]
  unchanged: Finding[]
  drift: Array<{
    rule_id: string
    subject?: string | null
    detail: string
  }>
}

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.json().then((d) => d.detail || res.statusText).catch(() => res.statusText)
    throw new ApiError(detail, res.status)
  }
  return res.json()
}

export const api = {
  health: () => request<{ status: string }>('GET', '/health'),

  createScan: (target: ScanTargetCreate) =>
    request<Scan>('POST', '/scans', { target }),

  listScans: () => request<Scan[]>('GET', '/scans'),

  getScan: (id: number) => request<Scan>('GET', `/scans/${id}`),

  getReport: (id: number) => request<Report>('GET', `/scans/${id}/report`),

  diffScans: (id: number, otherId: number) =>
    request<ScanDiff>('GET', `/scans/${id}/diff/${otherId}`),
}

export { ApiError }
