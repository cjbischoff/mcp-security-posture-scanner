import { http, HttpResponse } from 'msw'
import {
  mockScan1,
  mockScan2,
  mockPendingScan,
  mockReport,
  mockDiff,
} from './data'

let scanIdCounter = 4

export const handlers = [
  http.get('/api/health', () => HttpResponse.json({ status: 'ok' })),

  http.post('/api/scans', async ({ request }) => {
    const body = (await request.json()) as { target?: Record<string, unknown> }
    const target = body?.target || {}

    const targetUrl = typeof target.url === 'string' ? target.url : ''
    const allowExt = Boolean(target.allow_external)

    // Consent enforcement
    if (targetUrl && !targetUrl.includes('localhost') && !targetUrl.includes('127.0.0.1') && !allowExt) {
      return HttpResponse.json({ detail: "External target requires allow_external=true" }, { status: 422 })
    }

    const targetName = typeof target.name === 'string' ? target.name : 'test'
    const id = scanIdCounter++
    return HttpResponse.json({
      id,
      status: 'running',
      target: { id, name: targetName, transport: 'stdio', command: 'python', args: [], url: null, allow_external: false },
      created_at: new Date().toISOString(),
      finished_at: null,
      finding_count: 0,
    }, { status: 201 })
  }),

  http.get('/api/scans', () => HttpResponse.json([mockScan1, mockScan2, mockPendingScan])),

  http.get('/api/scans/:id', ({ params }) => {
    const id = Number(params.id)
    if (id === 1) return HttpResponse.json(mockScan1)
    if (id === 2) return HttpResponse.json(mockScan2)
    if (id === 3) return HttpResponse.json(mockPendingScan)
    return HttpResponse.json({ detail: 'Scan not found' }, { status: 404 })
  }),

  http.get('/api/scans/:id/report', ({ params }) => {
    const id = Number(params.id)
    if (id === 3) return HttpResponse.json({ detail: 'Scan not finished yet' }, { status: 409 })
    if (id === 1 || id === 2) return HttpResponse.json(mockReport)
    return HttpResponse.json({ detail: 'Scan not found' }, { status: 404 })
  }),

  http.get('/api/scans/:id/diff/:otherId', ({ params }) => {
    const id = Number(params.id)
    const otherId = Number(params.otherId)
    if ((id === 1 || id === 2) && (otherId === 1 || otherId === 2)) {
      return HttpResponse.json(mockDiff)
    }
    return HttpResponse.json({ detail: 'Scans target different servers or are not finished' }, { status: 409 })
  }),
]
