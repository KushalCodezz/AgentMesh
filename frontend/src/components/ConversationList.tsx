'use client'

import { useQuery } from '@tanstack/react-query'
import { api, type Conversation } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'
import { MessageSquare } from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  planning:       'text-white/40',
  running:        'text-acid-400',
  completed:      'text-success',
  failed:         'text-danger',
  awaiting_human: 'text-amber-400',
}

interface Props {
  selectedId: string | null
  onSelect: (id: string) => void
}

export function ConversationList({ selectedId, onSelect }: Props) {
  const { data: conversations = [], isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: api.listConversations,
  })

  return (
    <div className="w-72 flex flex-col border-r border-white/5 bg-carbon-900/30">
      <div className="p-3 border-b border-white/5">
        <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest">
          Conversations · {conversations.length}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="p-4 space-y-2">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 rounded-lg shimmer" />
            ))}
          </div>
        )}

        {!isLoading && conversations.length === 0 && (
          <div className="p-6 text-center">
            <MessageSquare size={24} className="mx-auto text-white/20 mb-2" />
            <p className="text-xs text-white/30">No conversations yet</p>
          </div>
        )}

        {conversations.map((conv: Conversation) => (
          <button
            key={conv.conversation_id}
            onClick={() => onSelect(conv.conversation_id)}
            className={`w-full text-left p-3 border-b border-white/5 transition-all hover:bg-white/3 ${
              selectedId === conv.conversation_id
                ? 'bg-electric-500/8 border-l-2 border-l-electric-500'
                : ''
            }`}
          >
            <div className="flex items-start gap-2">
              <span className={`status-dot mt-1.5 flex-shrink-0 ${conv.status}`} />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-white/80 line-clamp-2 leading-relaxed">
                  {conv.request}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-[10px] font-mono font-semibold ${STATUS_COLORS[conv.status] ?? 'text-white/40'}`}>
                    {conv.status}
                  </span>
                  <span className="text-[10px] text-white/20">·</span>
                  <span className="text-[10px] text-white/20">
                    {(conv as any).task_count ?? 0} tasks
                  </span>
                  <span className="text-[10px] text-white/20 ml-auto">
                    {formatDistanceToNow(new Date(conv.created_at), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
