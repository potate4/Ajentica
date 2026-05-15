export type Citation = {
  path: string
  start_line: number
  end_line: number
}

export type TraceEvent = {
  kind: string
  payload: Record<string, unknown>
}

export type ChatRequest = {
  question: string
  session_id?: string
  options?: Record<string, unknown>
}

export type ChatResponse = {
  answer: string
  citations: Citation[]
  refused: boolean
  session_id: string
  events: TraceEvent[]
}

export type AppConfig = {
  agent_mode: 'single' | 'crew'
  llm_model: string
  target_repo_url: string
  target_repo_ref: string
  enable_streaming: boolean
  enable_reasoning_trace: boolean
  enable_session_memory: boolean
}

export type HealthStatus = {
  status: 'ok' | 'degraded'
  indexed_chunks: number
  ingested: boolean
  error?: string
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  events?: TraceEvent[]
  refused?: boolean
  pending?: boolean
  error?: boolean
}
