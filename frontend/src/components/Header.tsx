import type { AppConfig, HealthStatus } from '../types'

type Props = {
  config: AppConfig | null
  health: HealthStatus | null
  onClear: () => void
  hasMessages: boolean
}

function repoLabel(url?: string): string {
  if (!url) return 'codebase'
  return url.replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, '')
}

export default function Header({ config, health, onClear, hasMessages }: Props) {
  const repoUrl = config?.target_repo_url.replace(/\.git$/, '')

  return (
    <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3.5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-indigo-500/15 ring-1 ring-indigo-500/30">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-300">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold text-slate-100">Codebase Q&amp;A Agent</h1>
            <p className="mt-0.5 truncate text-xs text-slate-400">
              {config ? (
                <>
                  Indexing{' '}
                  <a href={repoUrl} target="_blank" rel="noreferrer" className="hover:text-indigo-300">
                    {repoLabel(config.target_repo_url)}
                  </a>
                  <span className="mx-1.5 text-slate-600">·</span>
                  <span className="font-mono">{config.llm_model}</span>
                </>
              ) : (
                'Loading…'
              )}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {health && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                health.ingested
                  ? 'bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/20'
                  : 'bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/20'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${health.ingested ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              {health.ingested ? `${health.indexed_chunks.toLocaleString()} chunks` : 'Not indexed'}
            </span>
          )}
          <button
            onClick={onClear}
            disabled={!hasMessages}
            className="rounded-md border border-slate-700/60 bg-slate-800/40 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-700/40 hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear
          </button>
        </div>
      </div>
    </header>
  )
}
