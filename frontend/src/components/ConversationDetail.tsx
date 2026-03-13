'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, createEventStream, type Conversation, type Event, type Task } from '@/lib/api'
import { 
  ChevronDown, ChevronRight, AlertTriangle, CheckCircle, 
  Clock, Zap, FileText, Code, Palette, Search, Shield, Brain
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const CAPABILITY_ICON: Record<string, any> = {
  research:     Search,
  architecture: Brain,
  code:         Code,
  qa:           Shield,
  creative:     Palette,
  planning:     FileText,
}

const CAPABILITY_COLOR: Record<string, string> = {
  research:     'text-acid-400 bg-acid-500/10 border-acid-500/20',
  architecture: 'text-electric-300 bg-electric-500/10 border-electric-500/20',
  code:         'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  qa:           'text-purple-400 bg-purple-500/10 border-purple-500/20',
  creative:     'text-pink-400 bg-pink-500/10 border-pink-500/20',
  planning:     'text-amber-400 bg-amber-500/10 border-amber-500/20',
}

export function ConversationDetail({ conversationId }: { conversationId: string }) {
  const [events, setEvents] = useState<Event[]>([])
  const [streamEnded, setStreamEnded] = useState(false)
  const [expandedTask, setExpandedTask] = useState<string | null>(null)

  const { data: conv, refetch } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.getConversation(conversationId),
    refetchInterval: streamEnded ? false : 2000,
  })

  // WebSocket event stream
  useEffect(() => {
    setEvents([])
    setStreamEnded(false)

    const cleanup = createEventStream(
      conversationId,
      (event) => setEvents(prev => [...prev, event]),
      (status) => {
        setStreamEnded(true)
        refetch()
      }
    )
    return cleanup
  }, [conversationId])

  if (!conv) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="w-6 h-6 border-2 border-electric-500/30 border-t-electric-500 rounded-full animate-spin" />
      </div>
    )
  }

  const tasks: Task[] = conv.tasks ?? []
  const isActive = ['planning', 'running', 'debate'].includes(conv.status)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/5 bg-carbon-900/30">
        <div className="flex items-start gap-3">
          <span className={`status-dot mt-1.5 ${conv.status}`} />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white/80 leading-relaxed">{conv.request}</p>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-[10px] font-mono text-white/30">
                {conv.conversation_id.slice(0, 8)}
              </span>
              <span className="text-[10px] font-mono text-white/30">
                {formatDistanceToNow(new Date(conv.created_at), { addSuffix: true })}
              </span>
              <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${
                conv.status === 'completed' ? 'text-success border-success/20 bg-success/10' :
                conv.status === 'failed'    ? 'text-danger border-danger/20 bg-danger/10' :
                isActive                   ? 'text-acid-400 border-acid-500/20 bg-acid-500/10' :
                'text-white/40 border-white/10'
              }`}>
                {conv.status}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content: tasks + event log */}
      <div className="flex-1 flex overflow-hidden">
        {/* Task DAG */}
        <div className="w-80 flex flex-col border-r border-white/5 overflow-y-auto">
          <div className="p-3 border-b border-white/5">
            <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
              Task DAG · {tasks.length}
            </span>
          </div>
          <div className="flex-1 p-3 space-y-1.5">
            {tasks.length === 0 && isActive && (
              <div className="flex items-center gap-2 text-xs text-white/30 p-3">
                <div className="w-3 h-3 border border-electric-500/40 border-t-electric-500 rounded-full animate-spin" />
                Planning tasks…
              </div>
            )}
            {tasks.map((task) => (
              <TaskCard
                key={task.task_id}
                task={task}
                result={conv.results?.[task.task_id]}
                expanded={expandedTask === task.task_id}
                onToggle={() => setExpandedTask(
                  expandedTask === task.task_id ? null : task.task_id
                )}
              />
            ))}
          </div>
        </div>

        {/* Right panel: deliverable + event log */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Deliverable */}
          {conv.deliverable && (
            <div className="p-4 border-b border-white/5">
              <DeliverableCard deliverable={conv.deliverable} />
            </div>
          )}

          {/* Event log */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b border-white/5 flex items-center gap-2">
              <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
                Event Stream
              </span>
              {isActive && (
                <div className="w-1.5 h-1.5 rounded-full bg-acid-400 animate-pulse" />
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono">
              {events.map((event, i) => (
                <EventLine key={i} event={event} />
              ))}
              {isActive && (
                <div className="flex items-center gap-2 text-[10px] text-white/20">
                  <span className="animate-pulse">▌</span>
                  <span>waiting for agents…</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function TaskCard({ task, result, expanded, onToggle }: {
  task: Task; result?: any; expanded: boolean; onToggle: () => void
}) {
  const Icon = CAPABILITY_ICON[task.capability] ?? FileText
  const colorClass = CAPABILITY_COLOR[task.capability] ?? 'text-white/40 bg-white/5 border-white/10'

  return (
    <div className="card card-hover overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 p-3 text-left"
      >
        <span className={`status-dot flex-shrink-0 ${task.status}`} />
        <div className={`p-1 rounded border ${colorClass}`}>
          <Icon size={10} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-white/80 font-medium truncate">{task.title}</p>
          <div className="flex items-center gap-1 mt-0.5">
            <span className={`text-[9px] font-mono border rounded px-1 ${colorClass}`}>
              {task.capability}
            </span>
            {result && (
              <span className="text-[9px] font-mono text-white/30">
                {(result.confidence * 100).toFixed(0)}% conf
              </span>
            )}
          </div>
        </div>
        {expanded ? <ChevronDown size={10} className="text-white/30" /> : <ChevronRight size={10} className="text-white/30" />}
      </button>

      {expanded && result && (
        <div className="px-3 pb-3 border-t border-white/5">
          <ConfidenceBar value={result.confidence} />
          <div className="mt-2 text-[10px] font-mono text-white/30 space-y-1">
            <div className="flex justify-between">
              <span>Tokens</span>
              <span className="text-white/50">{result.tokens_used?.toLocaleString() ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span>Latency</span>
              <span className="text-white/50">{result.latency_ms}ms</span>
            </div>
            <div className="flex justify-between">
              <span>Agent</span>
              <span className="text-white/50">{result.agent_id?.replace('_agent', '')}</span>
            </div>
          </div>
          {result.requires_human_review && (
            <div className="mt-2 flex items-center gap-1 text-[10px] text-amber-400">
              <AlertTriangle size={9} />
              Human review required
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = value >= 0.75 ? '#10b981' : value >= 0.60 ? '#f59e0b' : '#ef4444'
  return (
    <div className="mt-2">
      <div className="flex justify-between text-[9px] font-mono text-white/30 mb-1">
        <span>Confidence</span>
        <span style={{ color }}>{pct}%</span>
      </div>
      <div className="confidence-bar">
        <div className="confidence-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

function DeliverableCard({ deliverable }: { deliverable: any }) {
  return (
    <div className="card p-4 border-electric-500/20 bg-electric-500/5">
      <div className="flex items-center gap-2 mb-2">
        <CheckCircle size={12} className="text-success" />
        <span className="text-xs font-display font-semibold text-white">Deliverable Ready</span>
        <span className="ml-auto text-[10px] font-mono text-white/30">
          {deliverable.success_count}/{deliverable.task_count} tasks succeeded
        </span>
      </div>
      <p className="text-xs text-white/50 leading-relaxed">{deliverable.summary}</p>
      <div className="mt-2">
        <ConfidenceBar value={deliverable.avg_confidence} />
      </div>
      {deliverable.requires_human_review?.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-amber-400">
          <AlertTriangle size={9} />
          {deliverable.requires_human_review.length} section(s) need human review
        </div>
      )}
    </div>
  )
}

const EVENT_STYLE: Record<string, string> = {
  conversation_started: 'text-electric-300',
  planned:              'text-acid-300',
  task_started:         'text-white/60',
  task_completed:       'text-success',
  debate_completed:     'text-purple-400',
  human_review_required:'text-amber-400',
  adaptive_proposals:   'text-amber-300',
  completed:            'text-success',
  failed:               'text-danger',
}

function EventLine({ event }: { event: Event }) {
  const color = EVENT_STYLE[event.type] ?? 'text-white/30'
  const time = new Date(event.timestamp).toLocaleTimeString('en', { hour12: false })
  return (
    <div className={`text-[10px] leading-5 ${color}`}>
      <span className="text-white/20 mr-2 select-none">{time}</span>
      <span className="text-white/40 mr-1.5">[{event.type}]</span>
      <span>{JSON.stringify(event.data).slice(0, 100)}</span>
    </div>
  )
}
