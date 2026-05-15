import { useEffect, useState } from 'react'
import Header from './components/Header'
import OptionsBar from './components/OptionsBar'
import MessageList from './components/MessageList'
import Composer from './components/Composer'
import { getConfig, getHealth, sendChat } from './api'
import type { AppConfig, HealthStatus, Message } from './types'

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)
  const [requestOptions, setRequestOptions] = useState<Record<string, unknown>>({})

  useEffect(() => {
    getConfig().then(setConfig).catch(() => {
      // Backend unreachable — UI degrades gracefully.
    })
    refreshHealth()
  }, [])

  function refreshHealth() {
    getHealth().then(setHealth).catch(() => {})
  }

  async function handleSend(question: string) {
    if (!question.trim() || sending) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    }
    const pendingId = crypto.randomUUID()
    const pendingMsg: Message = {
      id: pendingId,
      role: 'assistant',
      content: '',
      pending: true,
    }
    setMessages(m => [...m, userMsg, pendingMsg])
    setSending(true)

    try {
      const res = await sendChat({
        question,
        session_id: sessionId,
        options: Object.keys(requestOptions).length > 0 ? requestOptions : undefined,
      })
      setSessionId(res.session_id)
      setMessages(m =>
        m.map(msg =>
          msg.id === pendingId
            ? {
                ...msg,
                pending: false,
                content: res.answer,
                citations: res.citations,
                events: res.events,
                refused: res.refused,
              }
            : msg,
        ),
      )
    } catch (e: unknown) {
      const err = e instanceof Error ? e.message : String(e)
      setMessages(m =>
        m.map(msg =>
          msg.id === pendingId
            ? {
                ...msg,
                pending: false,
                content: `**Error:** ${err}`,
                error: true,
              }
            : msg,
        ),
      )
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
        <MessageList messages={messages} config={config} health={health} />
      </main>
      <Composer
        onSend={handleSend}
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
