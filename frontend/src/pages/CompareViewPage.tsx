import BeforeAfterSlider from '../components/BeforeAfterSlider'
import type { InferResponse } from '../types'

export default function CompareViewPage({ result, onGoToUpload }: { result: InferResponse | null; onGoToUpload: () => void }) {
  if (!result) {
    return (
      <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
        <h2 className="font-display text-xl font-semibold text-[var(--text)]">No result yet</h2>
        <p className="mt-2.5 max-w-sm text-sm text-[var(--text-dim)]">
          Run an enhancement first -- this view shows the before/after comparison for the most recent result.
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
    <div className="rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-1.5">
      <BeforeAfterSlider
        beforeSrc={`data:image/png;base64,${result.input_preview_png}`}
        afterSrc={`data:image/png;base64,${result.output_preview_png}`}
        beforeLabel={`Original (${result.input_resolution_m}m)`}
        afterLabel={`GeoSR-4 Output (${result.output_resolution_m}m)`}
      />
      <p className="pt-2.5 pb-1 text-center text-xs text-[var(--text-faint)]">Drag the handle to compare</p>
    </div>
  )
}
