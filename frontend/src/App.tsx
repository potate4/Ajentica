import { useEffect, useState } from 'react'
import Header from './components/Header'
import OptionsBar from './components/OptionsBar'
import MessageList from './components/MessageList'
import Composer from './components/Composer'
import { getConfig, getHealth, sendChat, streamChat } from './api'
import type { AppConfig, HealthStatus, Message, TraceEvent } from './types'

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)
  const [requestOptions, setRequestOptions] = useState<Record<string, unknown>>({})
  const [composerValue, setComposerValue] = useState('')

  useEffect(() => {
    getConfig().then(setConfig).catch(() => {})
    getHealth().then(setHealth).catch(() => {})
  }, [])

  function patchPending(pendingId: string, patch: (m: Message) => Message) {
    setMessages(curr => curr.map(m => (m.id === pendingId ? patch(m) : m)))
  }

  async function handleSend(question: string) {
    if (!question.trim() || sending) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: question }
    const pendingId = crypto.randomUUID()
    const pendingMsg: Message = {
      id: pendingId,
      role: 'assistant',
      content: '',
      pending: true,
      events: [],
    }
    setMessages(m => [...m, userMsg, pendingMsg])
    setSending(true)

    const opts = Object.keys(requestOptions).length > 0 ? requestOptions : undefined
    // Per-request override beats server default. This is what makes the
    // "Stream tokens" toggle actually switch endpoints.
    const useStream =
      (requestOptions.enable_streaming as boolean | undefined)
      ?? config?.enable_streaming
      ?? false

    try {
      if (useStream) {
        await streamChat(
          { question, session_id: sessionId, options: opts },
          {
            onSession: id => setSessionId(id),
            onTrace: (e: TraceEvent) =>
              patchPending(pendingId, m => ({ ...m, events: [...(m.events ?? []), e] })),
            onDone: r => {
              setSessionId(r.session_id)
              patchPending(pendingId, m => ({
                ...m,
                pending: false,
                content: r.answer,
                citations: r.citations,
                refused: r.refused,
              }))
            },
            onError: err =>
              patchPending(pendingId, m => ({
                ...m,
                pending: false,
                content: `**Error:** ${err}`,
                error: true,
              })),
          },
        )
      } else {
        const res = await sendChat({ question, session_id: sessionId, options: opts })
        setSessionId(res.session_id)
        patchPending(pendingId, m => ({
          ...m,
          pending: false,
          content: res.answer,
          citations: res.citations,
          events: res.events,
          refused: res.refused,
        }))
      }
    } catch (e: unknown) {
      const err = e instanceof Error ? e.message : String(e)
      patchPending(pendingId, m => ({
        ...m,
        pending: false,
        content: `**Error:** ${err}`,
        error: true,
      }))
    } finally {
      setSending(false)
    }
  }

  function handleClear() {
    setMessages([])
    setSessionId(undefined)
  }

  return (
    <div className="flex h-full flex-col">
      <Header config={config} health={health} onClear={handleClear} hasMessages={messages.length > 0} />
      {config && (
        <OptionsBar config={config} value={requestOptions} onChange={setRequestOptions} />
      )}
      <main className="min-h-0 flex-1 overflow-hidden">
        <MessageList messages={messages} config={config} health={health} onSelectExample={setComposerValue} />
      </main>
      <Composer
        onSend={q => { handleSend(q); setComposerValue('') }}
        value={composerValue}
        onValueChange={setComposerValue}
        disabled={sending || (health !== null && !health.ingested)}
        placeholder={
          health && !health.ingested
            ? 'Index is empty — run `python -m app.ingest.pipeline` first.'
            : undefined
        }
      />
    </div>
  )
}

export default App
