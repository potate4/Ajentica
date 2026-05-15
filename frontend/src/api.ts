import type { AppConfig, ChatRequest, ChatResponse, Citation, HealthStatus, TraceEvent } from './types'

const BASE = '/api'

async function jsonOrThrow<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text().catch(() => '')
    throw new Error(`HTTP ${r.status}: ${text || r.statusText}`)
  }
  return r.json() as Promise<T>
}

export async function getHealth(): Promise<HealthStatus> {
  const r = await fetch(`${BASE}/health`)
  return jsonOrThrow<HealthStatus>(r)
}

export async function getConfig(): Promise<AppConfig> {
  const r = await fetch(`${BASE}/config`)
  return jsonOrThrow<AppConfig>(r)
}

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  return jsonOrThrow<ChatResponse>(r)
}

/** Build a clickable GitHub URL from a citation. */
export function citationUrl(c: { path: string; start_line: number; end_line: number }, repoUrl: string, ref: string): string {
  const repo = repoUrl.replace(/\.git$/, '').replace(/\/$/, '')
  return `${repo}/blob/${ref}/${c.path}#L${c.start_line}-L${c.end_line}`
}

// ---------------------------------------------------------------------------
// Streaming chat (SSE)
// ---------------------------------------------------------------------------

export type StreamCallbacks = {
  onSession?: (sessionId: string) => void
  onTrace?: (event: TraceEvent) => void
  onDone?: (result: { answer: string; citations: Citation[]; refused: boolean; session_id: string }) => void
  onError?: (message: string) => void
}

/**
 * POST to /api/chat/stream and dispatch SSE events to callbacks.
 * Resolves when the stream closes.
 */
export async function streamChat(req: ChatRequest, cb: StreamCallbacks): Promise<void> {
  let r: Response
  try {
    r = await fetch(`${BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    })
  } catch (e) {
    cb.onError?.(e instanceof Error ? e.message : String(e))
    return
  }
  if (!r.ok || !r.body) {
    cb.onError?.(`HTTP ${r.status}: ${r.statusText}`)
    return
  }

  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      buffer = drainEventBlocks(buffer, cb)
    }
    // Flush anything left
    drainEventBlocks(buffer + '\n\n', cb)
  } catch (e) {
    cb.onError?.(e instanceof Error ? e.message : String(e))
  }
}

function drainEventBlocks(buffer: string, cb: StreamCallbacks): string {
  let idx: number
  while ((idx = buffer.indexOf('\n\n')) >= 0) {
    const block = buffer.slice(0, idx).trim()
    buffer = buffer.slice(idx + 2)
    if (!block) continue
    dispatchBlock(block, cb)
  }
  return buffer
}

function dispatchBlock(block: string, cb: StreamCallbacks): void {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim()
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
  }
  const raw = dataLines.join('\n')
  let data: unknown
  try {
    data = raw ? JSON.parse(raw) : {}
  } catch {
    data = raw
  }
  switch (event) {
    case 'session':
      cb.onSession?.((data as { session_id: string }).session_id)
      break
    case 'trace':
      cb.onTrace?.(data as TraceEvent)
      break
    case 'done':
      cb.onDone?.(data as { answer: string; citations: Citation[]; refused: boolean; session_id: string })
      break
    case 'error':
      cb.onError?.((data as { error: string }).error ?? String(data))
      break
  }
}
