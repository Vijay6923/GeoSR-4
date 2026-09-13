import { useState } from 'react'
import Dropzone from './components/Dropzone'
import BeforeAfterSlider from './components/BeforeAfterSlider'
import MetricsPanel from './components/MetricsPanel'

interface InferResponse {
  input_preview_png: string
  output_preview_png: string
  uncertainty_preview_png: string
  output_geotiff: string
  input_shape: number[]
  output_shape: number[]
  input_resolution_m: number
  output_resolution_m: number
  metrics: { psnr: number; ssim: number; sam: number; ergas: number } | null
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [hrFile, setHrFile] = useState<File | null>(null)
  const [showRefUpload, setShowRefUpload] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<InferResponse | null>(null)

  const handleFileSelect = (f: File | null) => {
    setFile(f)
    setResult(null)
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)
    if (hrFile) formData.append('hr_reference', hrFile)

    try {
      const res = await fetch('/api/infer', { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(body.detail ?? `request failed (${res.status})`)
      }
      const data: InferResponse = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'something went wrong')
    } finally {
      setLoading(false)
    }
  }

  const downloadGeoTiff = () => {
    if (!result) return
    const bytes = atob(result.output_geotiff)
    const arr = new Uint8Array(bytes.length)
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
    const blob = new Blob([arr], { type: 'image/tiff' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'geosr4_output.tif'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="relative overflow-hidden bg-slate-900">
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-6 py-10">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-400/30">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                <line x1="2" y1="12" x2="22" y2="12" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-white">GeoSR-4</h1>
          </div>
          <p className="mt-3 max-w-xl text-sm text-slate-400">
            Deep-learning super resolution for satellite imagery. Upload 10m Sentinel-2 imagery and reconstruct
            &lt;4m detail with a trained model, not interpolation.
          </p>
          <div className="mt-5 flex items-center gap-2 text-xs font-medium text-slate-500">
            <span className="rounded-md bg-white/5 px-2.5 py-1 ring-1 ring-white/10">10m Sentinel-2</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
            <span className="rounded-md bg-emerald-500/10 px-2.5 py-1 text-emerald-400 ring-1 ring-emerald-400/20">2.5m GeoSR-4</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <Dropzone file={file} onFileSelect={handleFileSelect} label="Sentinel-2 GeoTIFF (4-band R,G,B,NIR)" />

          {!showRefUpload ? (
            <button
              onClick={() => setShowRefUpload(true)}
              className="mt-3 flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700"
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
                onFileSelect={setHrFile}
                label="Ground-truth reference (optional)"
                hint="PSNR/SSIM/SAM/ERGAS need something to compare against -- without one we won't show numbers we can't back up."
                compact
              />
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || loading}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
          >
            {loading && <Spinner />}
            {loading ? 'Reconstructing…' : 'Generate SR'}
          </button>

          {error && (
            <div className="mt-3 flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
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
          <div className="mt-8">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <span className="tabular-nums">
                  {result.input_shape[1]}&times;{result.input_shape[2]}
                </span>
                <span className="text-slate-400">@ {result.input_resolution_m}m</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="text-slate-300">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
                <span className="tabular-nums">
                  {result.output_shape[1]}&times;{result.output_shape[2]}
                </span>
                <span className="text-slate-400">@ {result.output_resolution_m}m</span>
              </div>
              <button
                onClick={downloadGeoTiff}
                className="flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download GeoTIFF
              </button>
            </div>

            <BeforeAfterSlider
              beforeSrc={`data:image/png;base64,${result.input_preview_png}`}
              afterSrc={`data:image/png;base64,${result.output_preview_png}`}
              beforeLabel={`Original (${result.input_resolution_m}m)`}
              afterLabel={`GeoSR-4 Output (${result.output_resolution_m}m)`}
            />
            <p className="mt-2 text-center text-xs text-slate-400">Drag the handle to compare</p>

            <div className="mt-7">
              {result.metrics ? (
                <MetricsPanel metrics={result.metrics} />
              ) : (
                <p className="text-center text-sm text-slate-400">
                  No ground-truth reference provided -- accuracy metrics unavailable for this image.
                </p>
              )}
            </div>

            <div className="mt-7">
              <div className="mb-3 flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-700">Model confidence</h3>
                <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                  where the model is unsure
                </span>
              </div>
              <img
                src={`data:image/png;base64,${result.uncertainty_preview_png}`}
                alt="Per-pixel uncertainty heatmap"
                className="w-full rounded-lg border border-slate-200"
              />
              <p className="mt-2 text-center text-xs text-slate-400">
                Brighter = lower confidence. Reconstructed detail is an inference, not a direct observation --
                sharp edges (roads, building outlines) are typically where the model is least certain.
              </p>
            </div>
          </div>
        )}
      </main>

      <footer className="mx-auto max-w-5xl px-6 py-8 text-center text-xs text-slate-400">
        GeoSR-4 -- SIH 2026 (26142). Model: SwinIR, trained on real Sentinel-2/NAIP pairs.
      </footer>
    </div>
  )
}

export default App
