import type { AppConfig } from '../types'

type Props = {
  config: AppConfig
  value: Record<string, unknown>
  onChange: (next: Record<string, unknown>) => void
}

/**
 * Per-request bonus toggles. Only renders if the backend reports that at
 * least one bonus is available. In core mode (Phase 1, all bonuses off) this
 * component renders nothing.
 */
export default function OptionsBar({ config, value, onChange }: Props) {
  const anyBonus =
    config.enable_streaming ||
    config.enable_reasoning_trace ||
    config.enable_session_memory ||
    config.agent_mode === 'crew'

  if (!anyBonus) return null

  function toggle(key: string) {
    onChange({ ...value, [key]: !value[key] })
  }

  return (
    <div className="border-b border-slate-800/60 bg-slate-950/40">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-6 py-2 text-xs text-slate-400">
        <span className="font-medium uppercase tracking-wide text-slate-500">Per-request</span>
        {config.enable_reasoning_trace && (
          <Toggle label="Show reasoning" checked={value.enable_reasoning_trace !== false} onChange={() => toggle('enable_reasoning_trace')} />
        )}
        {config.enable_streaming && (
          <Toggle label="Stream tokens" checked={value.enable_streaming !== false} onChange={() => toggle('enable_streaming')} />
        )}
        {config.enable_session_memory && (
          <Toggle label="Use chat memory" checked={value.enable_session_memory !== false} onChange={() => toggle('enable_session_memory')} />
        )}
        {config.agent_mode === 'crew' && (
          <Toggle
            label="Multi-agent crew"
            checked={value.agent_mode !== 'single'}
            onChange={() => onChange({ ...value, agent_mode: value.agent_mode === 'single' ? 'crew' : 'single' })}
          />
        )}
      </div>
    </div>
  )
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-1.5 select-none">
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
