import type { Scan, Report, ScanDiff } from '../client'

export const mockScan1: Scan = {
  id: 1,
  status: 'completed',
  target: {
    id: 1,
    name: 'test-server',
    transport: 'stdio',
    command: 'python',
    args: ['-m', 'stub_server'],
    url: null,
    allow_external: false,
  },
  created_at: '2026-10-16T12:00:00Z',
  finished_at: '2026-10-16T12:00:05Z',
  finding_count: 6,
}

export const mockScan2: Scan = {
  id: 2,
  status: 'completed',
  target: {
    id: 1,
    name: 'test-server',
    transport: 'stdio',
    command: 'python',
    args: ['-m', 'stub_server'],
    url: null,
    allow_external: false,
  },
  created_at: '2026-10-16T12:05:00Z',
  finished_at: '2026-10-16T12:05:05Z',
  finding_count: 5,
}

export const mockPendingScan: Scan = {
  id: 3,
  status: 'pending',
  target: {
    id: 2,
    name: 'pending-scan',
    transport: 'stdio',
    command: 'python',
    args: ['-m', 'stub_server'],
    url: null,
    allow_external: false,
  },
  created_at: '2026-10-16T14:00:00Z',
  finished_at: null,
  finding_count: 0,
}

export const mockReport: Report = {
  scan: mockScan1,
  findings: [
    {
      id: 1,
      rule_id: 'MCP-001',
      severity: 'critical',
      title: 'Injection patterns in tool descriptions',
      description: "Tool 'injected_tool': contains hidden unicode characters; matches injection pattern.",
      remediation: 'Remove injection patterns from tool descriptions.',
      subject: 'injected_tool',
    },
    {
      id: 2,
      rule_id: 'MCP-009',
      severity: 'critical',
      title: 'Prompt-injection patterns in resource/prompt content descriptions',
      description: "Prompt 'analyze': matches injection pattern.",
      remediation: 'Remove injection patterns from resource and prompt descriptions.',
      subject: 'analyze',
    },
    {
      id: 3,
      rule_id: 'MCP-002',
      severity: 'high',
      title: 'Unconstrained input schema on sensitive parameters',
      description: "Tool 'injected_tool' has unconstrained params: command.",
      remediation: 'Add pattern, format, or enum constraints to sensitive parameters.',
      subject: 'injected_tool',
    },
    {
      id: 4,
      rule_id: 'MCP-004',
      severity: 'high',
      title: 'Read + write capability pairing (confused-deputy)',
      description: 'Read-capable tools: read_write_tool; write-capable tools: read_write_tool.',
      remediation: 'Separate read-only and write-capable tools onto different servers.',
      subject: null,
    },
    {
      id: 5,
      rule_id: 'MCP-006',
      severity: 'medium',
      title: 'Overly broad resource URI patterns',
      description: "Resource 'config_wildcard' URI 'config:///**': broad pattern '**'.",
      remediation: 'Restrict resource URIs to specific paths.',
      subject: 'config_wildcard',
    },
    {
      id: 6,
      rule_id: 'MCP-008',
      severity: 'medium',
      title: 'Missing or malformed schema on required parameters',
      description: "Tool 'injected_tool' has malformed required params.",
      remediation: 'Ensure every required parameter has a type and constraints.',
      subject: 'injected_tool',
    },
  ],
  summary: { critical: 2, high: 2, medium: 2 },
}

export const mockDiff: ScanDiff = {
  scan_id: 1,
  other_id: 2,
  added: [
    {
      id: 7,
      rule_id: 'MCP-002',
      severity: 'high',
      title: 'Unconstrained input schema',
      description: 'New tool with unconstrained command param.',
      remediation: 'Add constraints.',
      subject: 'new_tool',
    },
  ],
  removed: [
    {
      id: 6,
      rule_id: 'MCP-008',
      severity: 'medium',
      title: 'Missing schema',
      description: 'Tool no longer has this issue.',
      remediation: 'N/A',
      subject: 'injected_tool',
    },
  ],
  unchanged: [
    {
      id: 1,
      rule_id: 'MCP-001',
      severity: 'critical',
      title: 'Injection patterns',
      description: 'Still present.',
      remediation: 'Fix.',
      subject: 'injected_tool',
    },
  ],
  drift: [
    {
      rule_id: 'MCP-003',
      subject: 'echo_tool',
      detail: "Finding 'MCP-003' on 'echo_tool' changed severity from 'high' to 'medium'.",
    },
  ],
}

export const mockFailedScan: Scan = {
  id: 9,
  status: 'failed',
  error: 'Connection refused',
  target: {
    id: 3,
    name: 'broken',
    transport: 'http',
    command: null,
    args: [],
    url: 'http://127.0.0.1:9/mcp',
    allow_external: false,
  },
  created_at: '2026-10-16T15:00:00Z',
  finished_at: '2026-10-16T15:00:01Z',
  finding_count: 0,
}
