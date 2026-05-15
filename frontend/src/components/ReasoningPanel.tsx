import { useState } from 'react'
import type { TraceEvent } from '../types'

const KIND_COLORS: Record<string, string> = {
  agent_started: 'text-indigo-300',
  agent_thought: 'text-sky-300',
  tool_call: 'text-emerald-300',
  tool_result: 'text-emerald-200',
  agent_finished: 'text-violet-300',
  answer_token: 'text-slate-400',
}

function formatPayload(payload: Record<string, unknown>): string {
  try {
    const json = JSON.stringify(payload)
    return json.length > 220 ? json.slice(0, 220) + '…' : json
  } catch {
    return String(payload)
  }
}

export default function ReasoningPanel({ events }: { events: TraceEvent[] }) {
  const [open, setOpen] = useState(false)
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
          Reasoning trace ({events.length} {events.length === 1 ? 'event' : 'events'})
        </span>
      </button>
      {open && (
        <ul className="space-y-0.5 border-t border-slate-800 px-3 py-2 font-mono text-xs">
          {events.map((e, i) => (
            <li key={i} className="leading-relaxed">
              <span className={KIND_COLORS[e.kind] ?? 'text-slate-300'}>{e.kind}</span>
              <span className="ml-2 text-slate-500">{formatPayload(e.payload)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
