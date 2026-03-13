// lib/api.ts — Typed API client for the AI Office backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

// ── Types ──────────────────────────────────────────────────────────────────

export interface Conversation {
  conversation_id: string
  trace_id: string
  request: string
  status: 'planning' | 'running' | 'completed' | 'failed'
  tasks: Task[]
  results: Record<string, AgentResult>
  deliverable?: Deliverable
  error?: string
  created_at: string
  events: Event[]
}

export interface Task {
  task_id: string
  conversation_id: string
  capability: string
  title: string
  description: string
  status: string
  priority: number
  depends_on: string[]
  confidence: number
  error?: string
  created_at: string
}

export interface AgentResult {
  task_id: string
  agent_id: string
  success: boolean
  output: Record<string, any>
  confidence: number
  latency_ms: number
  tokens_used: number
  requires_human_review: boolean
  error?: string
  timestamp: string
}

export interface Deliverable {
  summary: string
  task_results: Record<string, any>
  avg_confidence: number
  task_count: number
  success_count: number
  requires_human_review: string[]
  assembled_at: string
}

export interface AgentStats {
  agent_id: string
  reliability_score: number
  total_tasks: number
  recent_success_rate: number
  avg_confidence: number
  avg_latency_ms: number
}

export interface AdaptiveProposal {
  proposal_id: string
  triggered_by: string
  agent_name: string
  failure_count: number
  avg_confidence: number
  sandbox_passed: boolean
  status: string
  requires_human_approval: boolean
  created_at: string
}

export interface Event {
  type: string
  data: Record<string, any>
  timestamp: string
}

export interface SystemStats {
  conversations: { total: number; by_status: Record<string, number> }
  agents: { total: number; avg_reliability: number }
  adaptive: { proposals_total: number; proposals_pending: number }
}

// ── API Client ─────────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(`API ${res.status}: ${err}`)
  }
  return res.json()
}

// Conversations
export const api = {
  startConversation: (req: string, metadata?: Record<string, any>) =>
    request<{ conversation_id: string; trace_id: string; status: string }>(
      '/api/v1/conversations',
      { method: 'POST', body: JSON.stringify({ request: req, metadata }) }
    ),

  listConversations: () =>
    request<Conversation[]>('/api/v1/conversations'),

  getConversation: (id: string) =>
    request<Conversation>(`/api/v1/conversations/${id}`),

  getDeliverable: (id: string) =>
    request<Deliverable>(`/api/v1/conversations/${id}/deliverable`),

  // Agents
  listAgents: () =>
    request<AgentStats[]>('/api/v1/agents'),

  // Adaptive
  listProposals: () =>
    request<AdaptiveProposal[]>('/api/v1/adaptive/proposals'),

  actionProposal: (id: string, action: 'approve' | 'reject') =>
    request<{ status: string }>(`/api/v1/adaptive/proposals/${id}`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  // Stats
  getStats: () =>
    request<SystemStats>('/api/v1/stats'),
}

// ── WebSocket ──────────────────────────────────────────────────────────────

export function createEventStream(
  conversationId: string,
  onEvent: (event: Event) => void,
  onEnd: (status: string) => void
): () => void {
  const ws = new WebSocket(`${WS_BASE}/ws/${conversationId}`)

  ws.onmessage = (msg) => {
    const event: Event = JSON.parse(msg.data)
    if (event.type === 'stream_end') {
      onEnd((event as any).status)
    } else {
      onEvent(event)
    }
  }

  ws.onerror = (err) => {
    console.error('WS error', err)
  }

  return () => ws.close()
}
