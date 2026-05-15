import { useEffect, useRef } from 'react'
import type { AppConfig, HealthStatus, Message } from '../types'
import MessageBubble from './MessageBubble'

type Props = {
  messages: Message[]
  config: AppConfig | null
  health: HealthStatus | null
  onSelectExample?: (q: string) => void
}

const EXAMPLES = [
  'Where does Flask resolve a URL to a view function?',
  'How does the application context get pushed and popped?',
  'Explain the routing system at a high level.',
  "What's the entry point when you call app.run()?",
]

export default function MessageList({ messages, config, health, onSelectExample }: Props) {
  const scrollerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollerRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages])

  return (
    <div className="h-full overflow-y-auto" ref={scrollerRef}>
      {messages.length === 0 ? (
        <div className="mx-auto flex h-full max-w-3xl items-center justify-center px-6 py-10">
          <EmptyState health={health} config={config} onSelectExample={onSelectExample} />
        </div>
      ) : (
        <div className="mx-auto w-full max-w-3xl space-y-5 px-6 py-6">
          {messages.map(m => (
            <MessageBubble key={m.id} message={m} config={config} />
          ))}
        </div>
      )}
    </div>
  )
}

function EmptyState({ health, config, onSelectExample }: { health: HealthStatus | null; config: AppConfig | null; onSelectExample?: (q: string) => void }) {
  if (health && !health.ingested) {
    return (
      <div className="max-w-md rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-6 text-center">
        <h2 className="text-base font-semibold text-amber-200">Index is empty</h2>
        <p className="mt-2 text-sm text-amber-100/80">
          Run the ingest pipeline once to populate the vector store:
        </p>
        <pre className="mt-3 rounded-md bg-slate-950/60 px-3 py-2 text-left font-mono text-xs text-slate-300">
          python -m app.ingest.pipeline
        </pre>
        <p className="mt-2 text-xs text-amber-100/60">Refresh this page when it finishes.</p>
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl">
      <h2 className="text-center text-lg font-medium text-slate-200">
        Ask anything about the indexed codebase
      </h2>
      <p className="mt-1 text-center text-sm text-slate-400">
        The agent will search the code, read the relevant files, and cite line ranges.
        {config && (
          <>
            {' '}Provider: <span className="font-mono text-slate-300">{config.llm_model}</span>.
          </>
        )}
      </p>
      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        {EXAMPLES.map(e => (
          <button
            key={e}
            onClick={() => onSelectExample?.(e)}
            className="rounded-lg border border-slate-800 bg-slate-900/50 px-3.5 py-2.5 text-left text-sm text-slate-300 transition hover:border-indigo-500/40 hover:bg-slate-800/60 hover:text-slate-100"
          >
            {e}
          </button>
        ))}
      </div>
    </div>
  )
}
