import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { AppConfig, Message } from '../types'
import CitationCard from './CitationCard'
import ReasoningPanel from './ReasoningPanel'

type Props = { message: Message; config: AppConfig | null }

export default function MessageBubble({ message, config }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-500/15 px-4 py-2.5 text-sm text-slate-100 ring-1 ring-indigo-500/25">
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <div className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-slate-800 text-[11px] font-semibold text-indigo-300 ring-1 ring-slate-700">
        A
      </div>
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm bg-slate-900/60 px-4 py-3 ring-1 ring-slate-800">
        {message.pending ? (
          <TypingIndicator />
        ) : (
          <>
            {message.refused && (
              <div className="mb-2 inline-flex items-center gap-1.5 rounded-md bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300 ring-1 ring-amber-500/20">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 9v4" />
                  <path d="M12 17h.01" />
                  <circle cx="12" cy="12" r="10" />
                </svg>
                Insufficient evidence in the indexed codebase
              </div>
            )}
            <div className={`markdown-body text-sm ${message.error ? 'text-rose-300' : 'text-slate-200'}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
            {config?.enable_reasoning_trace && message.events && message.events.length > 0 && (
              <ReasoningPanel events={message.events} />
            )}
            {config && message.citations && message.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {message.citations.map((c, i) => (
                  <CitationCard key={`${c.path}-${c.start_line}-${i}`} citation={c} config={config} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1.5">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" style={{ animationDelay: '150ms' }} />
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-400" style={{ animationDelay: '300ms' }} />
      <span className="ml-2 text-xs text-slate-400">Thinking…</span>
    </div>
  )
}
