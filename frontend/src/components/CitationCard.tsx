import { citationUrl } from '../api'
import type { AppConfig, Citation } from '../types'

type Props = { citation: Citation; config: AppConfig }

export default function CitationCard({ citation, config }: Props) {
  const url = citationUrl(citation, config.target_repo_url, config.target_repo_ref)
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      title={`Open ${citation.path} on GitHub`}
      className="group inline-flex max-w-full items-center gap-1.5 rounded-md border border-slate-700/60 bg-slate-800/40 px-2.5 py-1 font-mono text-xs text-slate-300 transition hover:border-indigo-500/40 hover:bg-indigo-500/10 hover:text-indigo-200"
    >
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-slate-500 group-hover:text-indigo-300">
        <path d="M14 3h7v7" />
        <path d="M10 14L21 3" />
        <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
      </svg>
      <span className="truncate">{citation.path}</span>
      <span className="shrink-0 text-slate-500">:{citation.start_line}-{citation.end_line}</span>
    </a>
  )
}
