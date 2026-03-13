'use client'

import { useQuery } from '@tanstack/react-query'
import { api, type AgentStats } from '@/lib/api'
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip } from 'recharts'
import { Bot, Zap, Clock, CheckCircle } from 'lucide-react'

const AGENT_META: Record<string, { icon: string; color: string; desc: string }> = {
  product_manager_agent: {
    icon: '📊',
    color: '#22d3ee',
    desc: 'Market research, PRD generation, competitor analysis, feature prioritization',
  },
  architect_agent: {
    icon: '🏗️',
    color: '#6366f1',
    desc: 'System architecture, API contracts, data modeling, scalability analysis',
  },
  engineer_agent: {
    icon: '⚙️',
    color: '#10b981',
    desc: 'Code generation, tests, Dockerfiles, CI/CD configs with syntax validation',
  },
  qa_agent: {
    icon: '🛡️',
    color: '#a78bfa',
    desc: 'Code review, fact checking, security analysis, test coverage validation',
  },
  creative_agent: {
    icon: '🎨',
    color: '#f472b6',
    desc: 'Image prompts, video storyboards, marketing copy, creative direction',
  },
}

export function AgentRegistry() {
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: api.listAgents,
    refetchInterval: 5000,
  })

  if (isLoading) return <LoadingSkeleton />

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-display font-bold text-white">Agent Registry</h1>
        <p className="text-sm text-white/40 mt-1">
          All registered specialist agents with live reliability metrics
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center py-16 text-white/30">
          <Bot size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No agents registered yet</p>
          <p className="text-xs mt-1">Start the orchestrator to register default agents</p>
        </div>
      )}
    </div>
  )
}

function AgentCard({ agent }: { agent: AgentStats }) {
  const meta = AGENT_META[agent.agent_id]
  const reliabilityPct = Math.round(agent.reliability_score * 100)
  const successPct = Math.round(agent.recent_success_rate * 100)
  const confidencePct = Math.round(agent.avg_confidence * 100)

  const chartData = [{ value: reliabilityPct, fill: meta?.color ?? '#6366f1' }]

  return (
    <div className="card card-hover p-5">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="text-2xl">{meta?.icon ?? '🤖'}</div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-display font-semibold text-white">
            {agent.agent_id.replace(/_agent$/, '').replace(/_/g, ' ')
              .split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </h3>
          <p className="text-[11px] text-white/40 mt-0.5 leading-relaxed">
            {meta?.desc ?? 'Specialist AI agent'}
          </p>
        </div>
        {/* Reliability dial */}
        <div className="w-16 h-16 flex-shrink-0 relative">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%" cy="50%"
              innerRadius="65%" outerRadius="100%"
              startAngle={90} endAngle={-270}
              data={[{ value: reliabilityPct, fill: meta?.color ?? '#6366f1' }]}
            >
              <RadialBar dataKey="value" background={{ fill: 'rgba(255,255,255,0.05)' }} cornerRadius={4} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-[10px] font-mono font-bold" style={{ color: meta?.color ?? '#6366f1' }}>
              {reliabilityPct}%
            </span>
          </div>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3">
        <Metric
          icon={CheckCircle}
          label="Success"
          value={`${successPct}%`}
          color={successPct >= 80 ? 'text-success' : successPct >= 60 ? 'text-amber-400' : 'text-danger'}
        />
        <Metric
          icon={Zap}
          label="Confidence"
          value={`${confidencePct}%`}
          color={confidencePct >= 75 ? 'text-electric-300' : 'text-white/50'}
        />
        <Metric
          icon={Clock}
          label="Avg Latency"
          value={agent.avg_latency_ms > 1000
            ? `${(agent.avg_latency_ms / 1000).toFixed(1)}s`
            : `${Math.round(agent.avg_latency_ms)}ms`}
          color="text-white/50"
        />
      </div>

      {/* Progress bar — reliability */}
      <div className="mt-3">
        <div className="confidence-bar">
          <div
            className="confidence-fill"
            style={{
              width: `${reliabilityPct}%`,
              background: meta?.color ?? '#6366f1',
            }}
          />
        </div>
      </div>

      {/* Total tasks badge */}
      <div className="mt-3 flex items-center gap-1">
        <span className="text-[10px] font-mono text-white/25">Total tasks:</span>
        <span className="text-[10px] font-mono text-white/40">{agent.total_tasks}</span>
      </div>
    </div>
  )
}

function Metric({ icon: Icon, label, value, color }: {
  icon: any; label: string; value: string; color: string
}) {
  return (
    <div className="bg-carbon-800/60 rounded-lg p-2.5 text-center">
      <Icon size={10} className={`mx-auto mb-1 ${color}`} />
      <div className={`text-xs font-mono font-semibold ${color}`}>{value}</div>
      <div className="text-[9px] text-white/25 mt-0.5">{label}</div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="card p-5 h-40 shimmer" />
      ))}
    </div>
  )
}
