'use client'

import { 
  MessageSquare, Bot, Zap, Plus, Activity, 
  ChevronRight, Settings, BarChart3
} from 'lucide-react'
import type { SystemStats } from '@/lib/api'

interface SidebarProps {
  view: string
  onViewChange: (v: 'conversations' | 'agents' | 'adaptive') => void
  onNewRequest: () => void
  stats?: SystemStats
}

const NAV = [
  { id: 'conversations', label: 'Conversations', icon: MessageSquare },
  { id: 'agents', label: 'Agent Registry', icon: Bot },
  { id: 'adaptive', label: 'Adaptive Layer', icon: Zap },
] as const

export function Sidebar({ view, onViewChange, onNewRequest, stats }: SidebarProps) {
  const pendingProposals = stats?.adaptive?.proposals_pending ?? 0

  return (
    <aside className="w-56 flex flex-col bg-carbon-900/80 border-r border-white/5 backdrop-blur-sm">
      {/* Logo */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-electric-500/20 border border-electric-500/40 flex items-center justify-center glow-electric">
            <span className="text-sm">🏢</span>
          </div>
          <div>
            <div className="text-sm font-display font-bold text-white tracking-tight">AI Office</div>
            <div className="text-[10px] text-white/30 font-mono">v1.0.0</div>
          </div>
        </div>
      </div>

      {/* New Request button */}
      <div className="p-3 border-b border-white/5">
        <button
          onClick={onNewRequest}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-electric-500 hover:bg-electric-400 text-white text-sm font-medium transition-all active:scale-95"
        >
          <Plus size={14} />
          New Request
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-0.5">
        {NAV.map(({ id, label, icon: Icon }) => {
          const active = view === id
          const badge = id === 'adaptive' && pendingProposals > 0 ? pendingProposals : null
          return (
            <button
              key={id}
              onClick={() => onViewChange(id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                active
                  ? 'bg-electric-500/15 text-electric-300 border border-electric-500/20'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/5'
              }`}
            >
              <Icon size={14} className={active ? 'text-electric-400' : ''} />
              <span className="flex-1 text-left font-medium">{label}</span>
              {badge && (
                <span className="w-4 h-4 rounded-full bg-amber-500 text-[9px] font-bold text-carbon-950 flex items-center justify-center">
                  {badge}
                </span>
              )}
              {active && <ChevronRight size={12} className="text-electric-400/60" />}
            </button>
          )
        })}
      </nav>

      {/* Footer stats */}
      <div className="p-3 border-t border-white/5 space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-[10px] text-white/30 font-mono uppercase tracking-wider">System</span>
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            <span className="text-[10px] text-success font-mono">online</span>
          </div>
        </div>
        {stats && (
          <div className="space-y-1">
            <Stat label="Conversations" value={stats.conversations.total} />
            <Stat label="Agents" value={stats.agents.total} />
            <Stat
              label="Reliability"
              value={`${(stats.agents.avg_reliability * 100).toFixed(0)}%`}
            />
          </div>
        )}
      </div>
    </aside>
  )
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between px-1">
      <span className="text-[10px] text-white/30">{label}</span>
      <span className="text-[10px] font-mono text-white/60">{value}</span>
    </div>
  )
}
