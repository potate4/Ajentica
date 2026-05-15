import { useEffect, useRef, useState } from 'react'

type Props = {
  onSend: (q: string) => void
  disabled?: boolean
  placeholder?: string
  value?: string
  onValueChange?: (v: string) => void
}

export default function Composer({ onSend, disabled, placeholder, value: externalValue, onValueChange }: Props) {
  const [internalValue, setInternalValue] = useState('')
  const value = externalValue !== undefined ? externalValue : internalValue
  const setValue = (v: string) => {
    setInternalValue(v)
    onValueChange?.(v)
  }
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-grow textarea up to a max height
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [value])

  function submit() {
    const v = value.trim()
    if (!v || disabled) return
    onSend(v)
    setValue('')
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-slate-800/80 bg-slate-950/60 px-6 py-4 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl">
        <div className="flex items-end gap-2 rounded-xl border border-slate-700/60 bg-slate-900/60 px-3 py-1.5 transition focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/30">
          <textarea
            ref={ref}
            value={value}
            disabled={disabled}
            onChange={e => setValue(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={placeholder ?? 'Ask anything about the indexed codebase…  (Enter to send · Shift+Enter for newline)'}
            rows={1}
            className="flex-1 resize-none bg-transparent py-2 text-sm text-slate-100 placeholder-slate-500 outline-none disabled:opacity-50"
          />
          <button
            onClick={submit}
            disabled={disabled || !value.trim()}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            Send
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
