import { useState } from 'react'
import urbanImage from '../assets/urban-satellite.jpg'
import type { InferResponse } from '../types'

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function HeaderBanner() {
  return (
    <div className="relative mb-6 h-36 overflow-hidden rounded-[14px] border border-[var(--border-c)]">
      <img src={urbanImage} alt="" className="h-full w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg)] via-[var(--bg)]/40 to-transparent" />
      <p className="absolute right-3 bottom-2 text-[10px] text-[var(--text-faint)]">
        Paris, France &middot; Landsat / NGA, public domain
      </p>
    </div>
  )
}

export default function UrbanAnalysisPage({ result, onGoToUpload }: { result: InferResponse | null; onGoToUpload: () => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [overlay, setOverlay] = useState<{ png: string; count: number } | null>(null)

  if (!result) {
    return (
      <div>
        <HeaderBanner />
        <div className="flex min-h-[420px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 text-center">
          <h2 className="font-display text-xl font-semibold text-[var(--text)]">No result yet</h2>
          <p className="mt-2.5 max-w-sm text-sm text-[var(--text-dim)]">
            Run an enhancement first -- structure detection runs on the enhanced image.
          </p>
          <button
            onClick={onGoToUpload}
            className="mt-6 rounded-[10px] bg-[var(--accent)] px-4 py-2.5 font-display text-sm font-semibold text-[var(--bg)] hover:opacity-90"
          >
            Go to Upload &amp; Enhance
          </button>
        </div>
      </div>
    )
  }

  const runDetection = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/urban-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_png_base64: result.output_preview_png }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(body.detail ?? `request failed (${res.status})`)
      }
      const data = await res.json()
      setOverlay({ png: data.overlay_png, count: data.n_segments })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'something went wrong')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <HeaderBanner />
      <div className="max-w-2xl rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Urban analysis</p>
          <span className="rounded-full bg-[var(--good)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--good)]">live</span>
        </div>

        {!overlay ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border-c)] bg-[var(--surface-2)] py-16">
            <p className="mb-4 max-w-sm text-center text-sm text-[var(--text-dim)]">
              Runs real zero-shot structure detection (Segment Anything) on the enhanced image. Takes 10-20 seconds.
            </p>
            <button
              onClick={runDetection}
              disabled={loading}
              className="flex items-center gap-2 rounded-[10px] bg-[var(--accent)] px-4 py-2.5 font-display text-sm font-semibold text-[var(--bg)] hover:opacity-90 disabled:opacity-60"
            >
              {loading && <Spinner />}
              {loading ? 'Detecting…' : 'Run detection'}
            </button>
            {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          </div>
        ) : (
          <>
            <img
              src={`data:image/png;base64,${overlay.png}`}
              alt="Detected structures overlay"
              className="w-full rounded-lg border border-[var(--border-soft)]"
            />
            <p className="mt-3 text-sm text-[var(--text)]">
              <span className="font-mono text-lg font-semibold text-[var(--accent)]">{overlay.count}</span> distinct
              structures/objects detected
            </p>
            <button
              onClick={runDetection}
              disabled={loading}
              className="mt-3 rounded-[8px] border border-[var(--border-c)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--text-dim)] hover:text-[var(--text)] disabled:opacity-60"
            >
              {loading ? 'Re-running…' : 'Re-run'}
            </button>
          </>
        )}

        <p className="mt-4 text-xs text-[var(--text-faint)] leading-relaxed">
          This is real zero-shot segmentation (Meta's Segment Anything Model), not a trained building classifier
          and not a claim that super-resolution finds more/better structures than bicubic upsampling would --
          that specific comparison was tested and found inconclusive (see the project's downstream-task
          validation notes).
        </p>
      </div>
    </div>
  )
}
