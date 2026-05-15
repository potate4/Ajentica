import { useState } from 'react'
import type { TraceEvent } from '../types'

type Pair = { call: TraceEvent; result?: TraceEvent }

const TOOL_ICONS: Record<string, string> = {
  search_code: '🔎',
  read_file: '📄',
  list_directory: '📁',
  summarize_module: '📚',
}

function pairUp(events: TraceEvent[]): Pair[] {
  const pairs: Pair[] = []
  let pending: TraceEvent | null = null
  for (const e of events) {
    if (e.kind === 'tool_call') {
      if (pending) pairs.push({ call: pending })
      pending = e
    } else if (e.kind === 'tool_result' && pending) {
      pairs.push({ call: pending, result: e })
      pending = null
    }
  }
  if (pending) pairs.push({ call: pending })
  return pairs
}

function formatArgs(args: unknown): string {
  if (args && typeof args === 'object') {
    return Object.entries(args as Record<string, unknown>)
      .filter(([, v]) => v !== undefined && v !== null && v !== '' && v !== 0)
      .map(([k, v]) => {
        const s = typeof v === 'string' ? `"${v}"` : String(v)
        return `${k}=${s.length > 60 ? s.slice(0, 60) + '…' : s}`
      })
      .join(', ')
  }
  return String(args)
}

export default function ReasoningPanel({ events, live = false }: { events: TraceEvent[]; live?: boolean }) {
  const [open, setOpen] = useState(live)
  const pairs = pairUp(events)
  const callCount = pairs.length
  const agentEvents = events.filter(e => e.kind === 'agent_started' || e.kind === 'agent_finished')

  if (callCount === 0 && agentEvents.length === 0) return null

  return (
    <div className="mt-3 overflow-hidden rounded-md border border-slate-800 bg-slate-950/40">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-3 py-1.5 text-xs text-slate-400 transition hover:text-slate-200"
      >
        <span className="inline-flex items-center gap-2">
          <svg
            width="11"
            height="11"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={`transition-transform ${open ? 'rotate-90' : ''}`}
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          {callCount} tool {callCount === 1 ? 'call' : 'calls'}
          {agentEvents.length > 0 && (
            <span className="text-slate-500">
              · {agentEvents.filter(e => e.kind === 'agent_finished').length}/{agentEvents.filter(e => e.kind === 'agent_started').length} agents
            </span>
          )}
          {live && (
            <span className="ml-1 inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" title="Live" />
          )}
        </span>
      </button>
      {open && (
        <ul className="divide-y divide-slate-800/60 border-t border-slate-800 text-xs">
          {pairs.map((p, i) => {
            const tool = (p.call.payload.tool as string) ?? '?'
            const args = p.call.payload.args ?? {}
            const result = p.result?.payload as Record<string, unknown> | undefined
            const elapsed = result?.elapsed_ms as number | undefined
            const error = result?.error as string | undefined
            const preview = result?.preview as string | undefined

            return (
              <li key={i} className="px-3 py-1.5">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-slate-200">
                    <span className="mr-1">{TOOL_ICONS[tool] ?? '⚙'}</span>
                    <span className="text-emerald-300">{tool}</span>
                    <span className="text-slate-500">(</span>
                    <span className="text-slate-400">{formatArgs(args)}</span>
                    <span className="text-slate-500">)</span>
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-slate-500">
                    {error ? <span className="text-rose-400">error</span> : elapsed !== undefined ? `${elapsed} ms` : p.result ? 'ok' : 'pending'}
                  </span>
                </div>
                {error && (
                  <div className="mt-1 truncate font-mono text-[11px] text-rose-400">{error}</div>
                )}
                {preview && !error && (
                  <div className="mt-1 truncate font-mono text-[11px] text-slate-500">↳ {preview}</div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
