import { useState } from 'react'
import Dropzone from '../components/Dropzone'

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

interface ChangeResult {
  before_preview_png: string
  after_preview_png: string
  change_preview_png: string
}

export default function ChangeDetectionPage() {
  const [beforeFile, setBeforeFile] = useState<File | null>(null)
  const [afterFile, setAfterFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ChangeResult | null>(null)

  const runComparison = async () => {
    if (!beforeFile || !afterFile) return
    setLoading(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('before', beforeFile)
    formData.append('after', afterFile)

    try {
      const res = await fetch('/api/change-detection', { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(body.detail ?? `request failed (${res.status})`)
      }
      const data: ChangeResult = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Change detection</p>
          <span className="rounded-full bg-[var(--good)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--good)]">live</span>
        </div>
        <p className="mb-5 text-sm text-[var(--text-dim)]">
          Upload two Sentinel-2 GeoTIFFs of the <strong className="text-[var(--text)]">same area</strong>, at
          different dates -- both get super-resolved, then compared. Both files must be the exact same pixel
          grid (same crop, same shape) -- this demo doesn't align mismatched extents.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Dropzone file={beforeFile} onFileSelect={setBeforeFile} label="Before" />
          <Dropzone file={afterFile} onFileSelect={setAfterFile} label="After" />
        </div>

        <button
          onClick={runComparison}
          disabled={!beforeFile || !afterFile || loading}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-[10px] bg-[var(--accent)] px-4 py-3 font-display text-sm font-semibold text-[var(--bg)] shadow-[0_0_22px_rgba(255,122,69,0.3)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-[var(--surface-2)] disabled:text-[var(--text-faint)] disabled:shadow-none sm:w-auto"
        >
          {loading && <Spinner />}
          {loading ? 'Comparing…' : 'Compare'}
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

      {result && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--text-dim)]">Before (enhanced)</p>
              <img src={`data:image/png;base64,${result.before_preview_png}`} alt="Before, super-resolved" className="w-full rounded-lg border border-[var(--border-soft)]" />
            </div>
            <div>
              <p className="mb-2 text-xs font-medium text-[var(--text-dim)]">After (enhanced)</p>
              <img src={`data:image/png;base64,${result.after_preview_png}`} alt="After, super-resolved" className="w-full rounded-lg border border-[var(--border-soft)]" />
            </div>
          </div>

          <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-5">
            <p className="mb-3 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Change map</p>
            <img src={`data:image/png;base64,${result.change_preview_png}`} alt="Change intensity map" className="w-full rounded-lg border border-[var(--border-soft)]" />
            <p className="mt-3 text-xs text-[var(--text-faint)] leading-relaxed">
              Mean absolute difference between the two enhanced images, per pixel -- a simple, real computation
              (not a trained damage classifier). Bright areas indicate more change between the two dates.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
