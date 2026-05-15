import type { AppConfig, ChatRequest, ChatResponse, HealthStatus } from './types'

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
