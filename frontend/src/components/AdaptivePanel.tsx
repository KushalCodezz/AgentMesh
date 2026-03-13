'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, type AdaptiveProposal } from '@/lib/api'
import { 
  Zap, CheckCircle, XCircle, Clock, AlertTriangle,
  ChevronDown, ChevronRight, Beaker
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const STATUS_CONFIG = {
  pending:  { color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Pending Review' },
  approved: { color: 'text-success',   bg: 'bg-success/10 border-success/20',     label: 'Approved' },
  rejected: { color: 'text-danger',    bg: 'bg-danger/10 border-danger/20',       label: 'Rejected' },
  deployed: { color: 'text-electric-300', bg: 'bg-electric-500/10 border-electric-500/20', label: 'Deployed' },
}

export function AdaptivePanel() {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: proposals = [], isLoading } = useQuery({
    queryKey: ['proposals'],
    queryFn: api.listProposals,
    refetchInterval: 8000,
  })

  const actionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      api.actionProposal(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['proposals'] }),
  })

  const pending = proposals.filter(p => p.status === 'pending')
  const others  = proposals.filter(p => p.status !== 'pending')

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-display font-bold text-white">Adaptive Layer</h1>
        <p className="text-sm text-white/40 mt-1">
          Auto-detected capability gaps — proposed specialist agents awaiting approval
        </p>
      </div>

      {/* How it works */}
      <div className="card p-4 mb-6 border-electric-500/15 bg-electric-500/5">
        <div className="flex items-start gap-3">
          <Zap size={14} className="text-electric-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-white/50 leading-relaxed space-y-1">
            <p><span className="text-white/80 font-medium">How it works:</span> The adaptive layer monitors a rolling window of {200} task outcomes. When a capability shows ≥8 failures or avg confidence &lt;60%, Claude designs a new specialized agent, runs it through sandbox tests, and queues it here for your approval.</p>
            <p className="text-white/30">Auto-registration is <span className="text-amber-400 font-mono">disabled</span> — all proposals require human ops approval.</p>
          </div>
        </div>
      </div>

      {/* Pending proposals */}
      {pending.length > 0 && (
        <section className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Clock size={12} className="text-amber-400" />
            <h2 className="text-xs font-mono text-amber-400 uppercase tracking-widest">
              Pending Approval · {pending.length}
            </h2>
          </div>
          <div className="space-y-3">
            {pending.map(p => (
              <ProposalCard
                key={p.proposal_id}
                proposal={p}
                expanded={expanded === p.proposal_id}
                onToggle={() => setExpanded(expanded === p.proposal_id ? null : p.proposal_id)}
                onApprove={() => actionMutation.mutate({ id: p.proposal_id, action: 'approve' })}
                onReject={() => actionMutation.mutate({ id: p.proposal_id, action: 'reject' })}
                loading={actionMutation.isPending}
              />
            ))}
          </div>
        </section>
      )}

      {/* History */}
      {others.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-xs font-mono text-white/30 uppercase tracking-widest">
              History · {others.length}
            </h2>
          </div>
          <div className="space-y-2">
            {others.map(p => (
              <ProposalCard
                key={p.proposal_id}
                proposal={p}
                expanded={expanded === p.proposal_id}
                onToggle={() => setExpanded(expanded === p.proposal_id ? null : p.proposal_id)}
                readonly
              />
            ))}
          </div>
        </section>
      )}

      {!isLoading && proposals.length === 0 && (
        <div className="text-center py-16 text-white/20">
          <Beaker size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No proposals yet</p>
          <p className="text-xs mt-1">Proposals appear when capability gaps are detected</p>
        </div>
      )}
    </div>
  )
}

function ProposalCard({
  proposal, expanded, onToggle, onApprove, onReject, loading, readonly = false,
}: {
  proposal: AdaptiveProposal
  expanded: boolean
  onToggle: () => void
  onApprove?: () => void
  onReject?: () => void
  loading?: boolean
  readonly?: boolean
}) {
  const cfg = STATUS_CONFIG[proposal.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending

  return (
    <div className="card overflow-hidden">
      <button onClick={onToggle} className="w-full flex items-center gap-3 p-4 text-left">
        <Zap size={14} className={cfg.color} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-white">{proposal.agent_name}</span>
            <span className={`text-[10px] font-mono border rounded px-1.5 py-0.5 ${cfg.bg} ${cfg.color}`}>
              {cfg.label}
            </span>
            {proposal.sandbox_passed && (
              <span className="text-[10px] font-mono text-success flex items-center gap-0.5">
                <Beaker size={8} /> sandbox ✓
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-[10px] text-white/30">
              Gap: <span className="text-white/50 font-mono">{proposal.triggered_by}</span>
            </span>
            <span className="text-[10px] text-white/30">
              {proposal.failure_count} failures · {(proposal.avg_confidence * 100).toFixed(0)}% avg confidence
            </span>
            <span className="text-[10px] text-white/20 ml-auto">
              {formatDistanceToNow(new Date(proposal.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        {expanded ? <ChevronDown size={12} className="text-white/30" /> : <ChevronRight size={12} className="text-white/30" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 space-y-3">
          {/* Human approval warning */}
          {proposal.requires_human_approval && (
            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5">
              <AlertTriangle size={11} />
              This agent is classified as high-impact and requires explicit human ops approval.
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'Failures Detected', value: proposal.failure_count },
              { label: 'Avg Confidence', value: `${(proposal.avg_confidence * 100).toFixed(0)}%` },
              { label: 'Sandbox', value: proposal.sandbox_passed ? 'Passed ✓' : 'Failed ✗' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-carbon-800/60 rounded-lg p-2 text-center">
                <div className="text-xs font-mono font-semibold text-white/60">{value}</div>
                <div className="text-[9px] text-white/25 mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          {/* Actions */}
          {!readonly && proposal.status === 'pending' && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={onReject}
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-danger/30 text-danger hover:bg-danger/10 text-xs font-medium transition-all disabled:opacity-40"
              >
                <XCircle size={12} /> Reject
              </button>
              <button
                onClick={onApprove}
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-success/15 border border-success/30 text-success hover:bg-success/25 text-xs font-medium transition-all disabled:opacity-40"
              >
                <CheckCircle size={12} /> Approve & Deploy
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
