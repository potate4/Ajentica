import type { AppConfig } from '../types'

type Props = {
  config: AppConfig
  value: Record<string, unknown>
  onChange: (next: Record<string, unknown>) => void
}

/**
 * Per-request overrides. Reads the effective state for each toggle as
 * "explicit override (if set) else server default", and writes back the
 * negation on click. This way the FIRST click always flips the visible
 * state, and the toggle actually controls behavior on the next request.
 */
export default function OptionsBar({ config, value, onChange }: Props) {
  const effectiveCrew = (value.agent_mode as string | undefined) === 'crew'
    || ((value.agent_mode as string | undefined) === undefined && config.agent_mode === 'crew')
  const effectiveStreaming = (value.enable_streaming as boolean | undefined)
    ?? config.enable_streaming
  const effectiveMemory = (value.enable_session_memory as boolean | undefined)
    ?? config.enable_session_memory

  function setKey(key: string, val: unknown) {
    onChange({ ...value, [key]: val })
  }

  return (
    <div className="border-b border-slate-800/60 bg-slate-950/40">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-6 py-2 text-xs text-slate-400">
        <span className="font-medium uppercase tracking-wide text-slate-500">Per-request</span>

        <Toggle
          label="Multi-agent crew"
          checked={effectiveCrew}
          onChange={() => setKey('agent_mode', effectiveCrew ? 'single' : 'crew')}
          title="Toggle between single agent (faster) and 4-agent crew (planner/researcher/module/synth)"
        />
        <Toggle
          label="Live trace"
          checked={effectiveStreaming}
          onChange={() => setKey('enable_streaming', !effectiveStreaming)}
          title="When on, tool call events stream live as the agent works"
        />
        <Toggle
          label="Use chat memory"
          checked={effectiveMemory}
          onChange={() => setKey('enable_session_memory', !effectiveMemory)}
          title="When on, prior turns in this session are surfaced to the agent"
        />

        {Object.keys(value).length > 0 && (
          <button
            onClick={() => onChange({})}
            className="ml-auto text-[11px] text-slate-500 underline-offset-2 hover:text-slate-300 hover:underline"
          >
            reset to server defaults
          </button>
        )}
      </div>
    </div>
  )
}

function Toggle({
  label, checked, onChange, title,
}: { label: string; checked: boolean; onChange: () => void; title?: string }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-1.5 select-none" title={title}>
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-3.5 w-3.5 rounded border border-slate-600 bg-slate-800 text-indigo-500 accent-indigo-500"
      />
      <span>{label}</span>
    </label>
  )
}
