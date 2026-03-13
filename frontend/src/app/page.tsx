'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Sidebar } from '@/components/Sidebar'
import { NewRequestPanel } from '@/components/NewRequestPanel'
import { ConversationList } from '@/components/ConversationList'
import { ConversationDetail } from '@/components/ConversationDetail'
import { AgentRegistry } from '@/components/AgentRegistry'
import { AdaptivePanel } from '@/components/AdaptivePanel'
import { StatsBar } from '@/components/StatsBar'

type View = 'conversations' | 'agents' | 'adaptive'

export default function Dashboard() {
  const [view, setView] = useState<View>('conversations')
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null)
  const [showNewRequest, setShowNewRequest] = useState(false)

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 5000,
  })

  return (
    <div className="flex h-screen overflow-hidden bg-carbon-950 grid-bg">
      {/* Sidebar */}
      <Sidebar
        view={view}
        onViewChange={(v) => { setView(v); setSelectedConvId(null) }}
        onNewRequest={() => setShowNewRequest(true)}
        stats={stats}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top stats bar */}
        <StatsBar stats={stats} />

        {/* Content area */}
        <div className="flex-1 flex overflow-hidden">
          {view === 'conversations' && (
            <>
              <ConversationList
                selectedId={selectedConvId}
                onSelect={setSelectedConvId}
              />
              <div className="flex-1 overflow-hidden">
                {selectedConvId ? (
                  <ConversationDetail conversationId={selectedConvId} />
                ) : (
                  <EmptyState onNew={() => setShowNewRequest(true)} />
                )}
              </div>
            </>
          )}

          {view === 'agents' && (
            <div className="flex-1 overflow-auto p-6">
              <AgentRegistry />
            </div>
          )}

          {view === 'adaptive' && (
            <div className="flex-1 overflow-auto p-6">
              <AdaptivePanel />
            </div>
          )}
        </div>
      </div>

      {/* New Request Modal */}
      {showNewRequest && (
        <NewRequestPanel
          onClose={() => setShowNewRequest(false)}
          onCreated={(id) => {
            setShowNewRequest(false)
            setView('conversations')
            setSelectedConvId(id)
          }}
        />
      )}
    </div>
  )
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <div className="text-center space-y-4">
        <div className="w-20 h-20 mx-auto rounded-2xl bg-carbon-800 border border-electric-500/20 flex items-center justify-center">
          <span className="text-3xl">🏢</span>
        </div>
        <h2 className="text-xl font-display font-semibold text-white">AI Office</h2>
        <p className="text-sm text-white/40 max-w-xs">
          Select a conversation or start a new one to put your AI team to work.
        </p>
        <button
          onClick={onNew}
          className="mt-2 px-5 py-2.5 rounded-lg bg-electric-500 hover:bg-electric-400 text-white text-sm font-medium transition-colors"
        >
          New Request
        </button>
      </div>
    </div>
  )
}
