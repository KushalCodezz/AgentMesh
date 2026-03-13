'use client'

import { Activity, CheckCircle, Clock, XCircle } from 'lucide-react'
import type { SystemStats } from '@/lib/api'

export function StatsBar({ stats }: { stats?: SystemStats }) {
  const byStatus = stats?.conversations?.by_status ?? {}
  const running = (byStatus['running'] ?? 0) + (byStatus['planning'] ?? 0)
  const completed = byStatus['completed'] ?? 0
  const failed = byStatus['failed'] ?? 0

  return (
    <div className="h-10 flex items-center gap-6 px-6 border-b border-white/5 bg-carbon-900/50 backdrop-blur-sm">
      <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">AI Office Control</span>

      <div className="flex-1" />

      <div className="flex items-center gap-4">
        <StatPill icon={Activity} value={running} label="Running" color="text-acid-400" />
        <StatPill icon={CheckCircle} value={completed} label="Done" color="text-success" />
        <StatPill icon={XCircle} value={failed} label="Failed" color="text-danger" />
        <StatPill icon={Clock} value={stats?.adaptive?.proposals_pending ?? 0} label="Proposals" color="text-amber-400" />
      </div>
    </div>
  )
}

function StatPill({
  icon: Icon, value, label, color,
}: {
  icon: any; value: number; label: string; color: string
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon size={12} className={color} />
      <span className={`text-xs font-mono font-semibold ${color}`}>{value}</span>
      <span className="text-[10px] text-white/30">{label}</span>
    </div>
  )
}
