import type { InferResponse } from '../types'

export default function CropMonitoringPage({ result, onGoToUpload }: { result: InferResponse | null; onGoToUpload: () => void }) {
  if (!result) {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
        <h2 className="font-display text-xl font-semibold text-[var(--text)]">No result yet</h2>
        <p className="mt-2.5 max-w-sm text-sm text-[var(--text-dim)]">
          Run an enhancement first -- NDVI is computed from the enhanced image's Red and NIR bands.
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
    <div className="max-w-2xl rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Crop monitoring</p>
        <span className="rounded-full bg-[var(--good)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--good)]">live</span>
      </div>
      <img
        src={`data:image/png;base64,${result.ndvi_preview_png}`}
        alt="NDVI vegetation index map"
        className="w-full rounded-lg border border-[var(--border-soft)]"
      />
      <p className="mt-4 text-sm text-[var(--text-dim)] leading-relaxed">
        NDVI (Normalized Difference Vegetation Index) is a standard remote-sensing formula --{' '}
        <code className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 font-mono text-xs text-[var(--text)]">
          (NIR - Red) / (NIR + Red)
        </code>{' '}
        -- computed directly from the enhanced image's real Red and NIR bands, not a trained model. Higher values
        (green) indicate denser, healthier vegetation; values near zero or negative (red/yellow) indicate bare
        soil, water, or built-up surfaces.
      </p>
      <p className="mt-3 text-xs text-[var(--text-faint)] leading-relaxed">
        This is a direct band computation, not a claim that super-resolution improves NDVI accuracy over
        bicubic upsampling -- that specific question hasn't been tested (see the project's downstream-task
        validation notes for related, inconclusive attempts on other tasks).
      </p>
    </div>
  )
}
