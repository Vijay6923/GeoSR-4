import { useState } from 'react'

interface InferResponse {
  input_preview_png: string
  output_preview_png: string
  output_geotiff: string
  input_shape: number[]
  output_shape: number[]
  input_resolution_m: number
  output_resolution_m: number
}

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<InferResponse | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null)
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
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold">GeoSR-4</h1>
        <p className="text-sm text-slate-500">10m Sentinel-2 &rarr; &lt;4m super-resolved imagery</p>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
          <label className="block text-sm font-medium text-slate-700">
            Upload a Sentinel-2 GeoTIFF (4-band R,G,B,NIR)
          </label>
          <div className="mt-3 flex items-center gap-3">
            <input
              type="file"
              accept=".tif,.tiff"
              onChange={handleFileChange}
              className="block text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-slate-700"
            />
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {loading ? 'Processing…' : 'Generate SR'}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
        </div>

        {result && (
          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm text-slate-600">
                {result.input_shape[1]}&times;{result.input_shape[2]} @ {result.input_resolution_m}m
                {'  '}&rarr;{'  '}
                {result.output_shape[1]}&times;{result.output_shape[2]} @ {result.output_resolution_m}m
              </div>
              <button
                onClick={downloadGeoTiff}
                className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-slate-50"
              >
                Download GeoTIFF
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="mb-2 text-sm font-medium text-slate-700">Original ({result.input_resolution_m}m)</p>
                <img
                  src={`data:image/png;base64,${result.input_preview_png}`}
                  alt="Original low-resolution input"
                  className="w-full rounded-md border border-slate-200"
                />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-slate-700">GeoSR-4 Output ({result.output_resolution_m}m)</p>
                <img
                  src={`data:image/png;base64,${result.output_preview_png}`}
                  alt="Super-resolved output"
                  className="w-full rounded-md border border-slate-200"
                />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
