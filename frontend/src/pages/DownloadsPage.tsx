import type { InferResponse } from '../types'

export default function DownloadsPage({
  result,
  onDownload,
  onGoToUpload,
}: {
  result: InferResponse | null
  onDownload: () => void
  onGoToUpload: () => void
}) {
  if (!result) {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
        <h2 className="font-display text-xl font-semibold text-[var(--text)]">Nothing to download yet</h2>
        <p className="mt-2.5 max-w-sm text-sm text-[var(--text-dim)]">
          Run an enhancement first -- the output GeoTIFF becomes available here.
        </p>
        <button
          onClick={onGoToUpload}
          className="mt-6 rounded-[10px] bg-[var(--accent)] px-4 py-2.5 font-display text-sm font-semibold text-[var(--bg)] hover:opacity-90"
        >
          Go to Upload &amp; Enhance
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-xl rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
      <p className="mb-4 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Download results</p>

      <div className="flex items-center justify-between rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3.5">
        <div>
          <p className="text-sm font-medium text-[var(--text)]">Enhanced GeoTIFF</p>
          <p className="mt-0.5 font-mono text-xs text-[var(--text-faint)]">
            {result.output_shape[1]}&times;{result.output_shape[2]} &middot; {result.output_resolution_m}m &middot; CRS preserved
          </p>
        </div>
        <button
          onClick={onDownload}
          className="flex items-center gap-1.5 rounded-md bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-[var(--bg)] hover:opacity-90"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Download
        </button>
      </div>

      <p className="mt-4 text-xs text-[var(--text-faint)]">
        Uncertainty map and analysis-report exports aren't built yet -- only what the model actually produces
        (the enhanced GeoTIFF) is offered here.
      </p>
    </div>
  )
}
