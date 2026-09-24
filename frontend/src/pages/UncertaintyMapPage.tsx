import type { InferResponse } from '../types'

export default function UncertaintyMapPage({ result, onGoToUpload }: { result: InferResponse | null; onGoToUpload: () => void }) {
  if (!result) {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
        <h2 className="font-display text-xl font-semibold text-[var(--text)]">No result yet</h2>
        <p className="mt-2.5 max-w-sm text-sm text-[var(--text-dim)]">
          Run an enhancement first -- the uncertainty map is computed per-request from a second model.
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
        <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Model confidence</p>
        <span className="rounded-full bg-[var(--warn)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--warn)]">where the model is unsure</span>
      </div>
      <img
        src={`data:image/png;base64,${result.uncertainty_preview_png}`}
        alt="Per-pixel uncertainty heatmap"
        className="w-full rounded-lg border border-[var(--border-soft)]"
      />
      <p className="mt-4 text-sm text-[var(--text-dim)] leading-relaxed">
        This heatmap comes from a second model (EDSR trained with a heteroscedastic uncertainty head) run
        alongside the main SwinIR reconstruction -- it predicts its own uncertainty (standard deviation) per
        pixel, not a post-hoc estimate.
      </p>
      <p className="mt-3 text-xs text-[var(--text-faint)] leading-relaxed">
        Brighter = higher predicted uncertainty. Reconstructed detail is an inference, not a direct observation --
        sharp edges (roads, building outlines) are typically where the model is least certain. This signal is real
        but modest (measured calibration correlation ~0.21 on held-out validation data, n=279) -- treat it as a
        rough guide, not a precise confidence score.
      </p>
    </div>
  )
}
