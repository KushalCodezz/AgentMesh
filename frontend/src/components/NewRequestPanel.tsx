'use client'

import { useState } from 'react'
import { X, Send, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'

const EXAMPLES = [
  'Research the AI tutoring market in India, design a 3-month MVP architecture, build a sample auth microservice with tests, and create a promo video brief.',
  'Analyze competitors for a B2B SaaS project management tool, produce a PRD with top 10 features, and design the backend architecture.',
  'Build a REST API for a URL shortener service with rate limiting, authentication, analytics tracking, and full test coverage.',
  'Create a social media campaign for a sustainable fashion brand: 5 image concepts, ad copy, and a 30-second video storyboard.',
]

interface Props {
  onClose: () => void
  onCreated: (conversationId: string) => void
}

export function NewRequestPanel({ onClose, onCreated }: Props) {
  const [request, setRequest] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    if (!request.trim()) return
    setLoading(true)
    setError('')
    try {
      const result = await api.startConversation(request)
      onCreated(result.conversation_id)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl card p-6 space-y-5 shadow-2xl border-electric-500/25">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-electric-400" />
            <h2 className="text-base font-display font-semibold text-white">New Request</h2>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white/80 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Text area */}
        <div>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="Describe what you want your AI team to work on…"
            rows={6}
            autoFocus
            className="w-full bg-carbon-800/80 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/90 placeholder-white/25 resize-none focus:outline-none focus:border-electric-500/50 focus:ring-1 focus:ring-electric-500/20 transition-all font-mono"
          />
          <div className="mt-1 text-right text-[10px] text-white/20 font-mono">
            {request.length} chars
          </div>
        </div>

        {/* Example prompts */}
        <div>
          <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider mb-2">Examples</p>
          <div className="space-y-1.5">
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                onClick={() => setRequest(ex)}
                className="w-full text-left text-xs text-white/40 hover:text-white/70 bg-carbon-800/40 hover:bg-carbon-800 border border-white/5 hover:border-electric-500/20 rounded-lg px-3 py-2 transition-all line-clamp-1"
              >
                <span className="text-electric-400/60 mr-2">→</span>
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="text-xs text-danger bg-danger/10 border border-danger/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-white/10 text-white/50 hover:text-white/80 text-sm transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!request.trim() || loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-electric-500 hover:bg-electric-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-all"
          >
            {loading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Dispatching to agents…
              </>
            ) : (
              <>
                <Send size={14} />
                Dispatch to AI Team
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
