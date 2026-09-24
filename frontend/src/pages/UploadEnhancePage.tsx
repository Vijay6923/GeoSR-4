import Dropzone from '../components/Dropzone'
import BeforeAfterSlider from '../components/BeforeAfterSlider'
import MetricsPanel from '../components/MetricsPanel'
import type { InferResponse } from '../types'

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

interface UploadEnhancePageProps {
  file: File | null
  hrFile: File | null
  showRefUpload: boolean
  loading: boolean
  error: string | null
  result: InferResponse | null
  onFileSelect: (f: File | null) => void
  onHrFileSelect: (f: File | null) => void
  onShowRefUpload: () => void
  onGenerate: () => void
  onDownload: () => void
}

export default function UploadEnhancePage({
  file,
  hrFile,
  showRefUpload,
  loading,
  error,
  result,
  onFileSelect,
  onHrFileSelect,
  onShowRefUpload,
  onGenerate,
  onDownload,
}: UploadEnhancePageProps) {
  return (
    <div className="flex flex-col items-start gap-7 lg:flex-row">
      {/* Left: controls */}
      <div className="flex w-full flex-col gap-5 lg:w-[360px] lg:shrink-0">
        <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
          <p className="mb-1.5 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Input</p>
          <p className="mb-3.5 font-display text-base font-semibold">Sentinel-2 scene</p>

          <Dropzone file={file} onFileSelect={onFileSelect} />

          {!showRefUpload ? (
            <button
              onClick={onShowRefUpload}
              className="mt-3 flex items-center gap-1 text-xs font-medium text-[var(--text-dim)] hover:text-[var(--text)]"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add a ground-truth reference for accuracy metrics
            </button>
          ) : (
            <div className="mt-4">
              <Dropzone
                file={hrFile}
                onFileSelect={onHrFileSelect}
                label="Ground-truth reference (optional)"
                hint="PSNR/SSIM/SAM/ERGAS need something to compare against -- without one we won't show numbers we can't back up."
                compact
              />
            </div>
          )}

          <button
            onClick={onGenerate}
            disabled={!file || loading}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-[10px] bg-[var(--accent)] px-4 py-3 font-display text-sm font-semibold text-[var(--bg)] shadow-[0_0_22px_rgba(255,122,69,0.3)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-[var(--surface-2)] disabled:text-[var(--text-faint)] disabled:shadow-none"
          >
            {loading && <Spinner />}
            {loading ? 'Reconstructing…' : 'Generate super-resolution'}
          </button>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-400">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}
        </div>

        <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-5">
          <p className="mb-2.5 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Resolution</p>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-2xl text-[var(--text)]">{result ? `${result.input_resolution_m}m` : '10.0m'}</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2.5" strokeLinecap="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
            <span className="font-mono text-2xl font-medium text-[var(--accent)]">{result ? `${result.output_resolution_m}m` : '2.5m'}</span>
          </div>
          <p className="mt-2 text-xs text-[var(--text-dim)]">4&times; super-resolution &middot; SwinIR + confidence fusion</p>
        </div>
      </div>

      {/* Right: results */}
      <div className="min-w-0 flex-1">
        {!result && !loading && (
          <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
            <h2 className="max-w-md font-display text-2xl font-semibold text-[var(--text)]">
              Reconstruct fine detail from 10m Sentinel&#8209;2 imagery
            </h2>
            <p className="mt-3 max-w-sm text-sm text-[var(--text-dim)]">
              Upload a 4-band GeoTIFF on the left and a trained deep-learning model reconstructs &lt;4m detail --
              not interpolation.
            </p>
          </div>
        )}

        {result && (
          <div className="flex flex-col gap-6">
            <div className="-mb-1 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-[var(--text-dim)]">
                <span className="font-mono tabular-nums">
                  {result.input_shape[1]}&times;{result.input_shape[2]}
                </span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-[var(--text-faint)]">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
                <span className="font-mono tabular-nums">
                  {result.output_shape[1]}&times;{result.output_shape[2]}
                </span>
              </div>
              <button
                onClick={onDownload}
                className="flex items-center gap-1.5 rounded-md border border-[var(--border-c)] bg-[var(--surface-2)] px-3 py-1.5 text-sm font-medium text-[var(--text-dim)] hover:text-[var(--text)]"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download GeoTIFF
              </button>
            </div>

            <div className="rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-1.5">
              <BeforeAfterSlider
                beforeSrc={`data:image/png;base64,${result.input_preview_png}`}
                afterSrc={`data:image/png;base64,${result.output_preview_png}`}
                beforeLabel={`Original (${result.input_resolution_m}m)`}
                afterLabel={`GeoSR-4 Output (${result.output_resolution_m}m)`}
              />
              <p className="pt-2.5 pb-1 text-center text-xs text-[var(--text-faint)]">Drag the handle to compare</p>
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-5">
                {result.metrics ? (
                  <MetricsPanel metrics={result.metrics} />
                ) : (
                  <>
                    <p className="mb-3 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Validation metrics</p>
                    <p className="text-sm text-[var(--text-dim)]">
                      No ground-truth reference provided -- accuracy metrics unavailable for this image.
                    </p>
                  </>
                )}
              </div>

              <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-5">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Model confidence</p>
                  <span className="rounded-full bg-[var(--warn)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--warn)]">
                    where the model is unsure
                  </span>
                </div>
                <img
                  src={`data:image/png;base64,${result.uncertainty_preview_png}`}
                  alt="Per-pixel uncertainty heatmap"
                  className="w-full rounded-lg border border-[var(--border-soft)]"
                />
                <p className="mt-2.5 text-xs text-[var(--text-faint)]">
                  Brighter = higher predicted uncertainty (see color scale above). Reconstructed detail is an
                  inference, not a direct observation -- sharp edges (roads, building outlines) are typically where
                  the model is least certain. This signal is real but modest (measured calibration correlation
                  ~0.21 on held-out data) -- treat it as a rough guide, not a precise confidence score.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
