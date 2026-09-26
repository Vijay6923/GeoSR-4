import { useState } from 'react'
import Sidebar from './components/Sidebar'
import type { Page } from './components/Sidebar'
import HomePage from './pages/HomePage'
import UploadEnhancePage from './pages/UploadEnhancePage'
import CompareViewPage from './pages/CompareViewPage'
import UncertaintyMapPage from './pages/UncertaintyMapPage'
import DownloadsPage from './pages/DownloadsPage'
import ModelInsightsPage from './pages/ModelInsightsPage'
import ComingSoonPage from './pages/ComingSoonPage'
import CropMonitoringPage from './pages/CropMonitoringPage'
import UrbanAnalysisPage from './pages/UrbanAnalysisPage'
import ChangeDetectionPage from './pages/ChangeDetectionPage'
import type { InferResponse } from './types'

const PAGE_TITLES: Record<Page, string> = {
  home: 'Home',
  upload: 'Upload & Enhance',
  compare: 'Compare View',
  'analysis-tools': 'Analysis Tools',
  'model-insights': 'Model Insights',
  uncertainty: 'Uncertainty Map',
  downloads: 'Downloads',
  'app-urban': 'Urban Analysis',
  'app-crop': 'Crop Monitoring',
  'app-disaster': 'Disaster Assessment',
  'app-change': 'Change Detection',
}

function ToolIcon({ d }: { d: string }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}

function App() {
  const [page, setPage] = useState<Page>('home')
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

  const goToUpload = () => setPage('upload')

  const renderPage = () => {
    switch (page) {
      case 'home':
        return <HomePage onGetStarted={goToUpload} />
      case 'upload':
        return (
          <UploadEnhancePage
            file={file}
            hrFile={hrFile}
            showRefUpload={showRefUpload}
            loading={loading}
            error={error}
            result={result}
            onFileSelect={handleFileSelect}
            onHrFileSelect={setHrFile}
            onShowRefUpload={() => setShowRefUpload(true)}
            onGenerate={handleUpload}
            onDownload={downloadGeoTiff}
          />
        )
      case 'compare':
        return <CompareViewPage result={result} onGoToUpload={goToUpload} />
      case 'uncertainty':
        return <UncertaintyMapPage result={result} onGoToUpload={goToUpload} />
      case 'downloads':
        return <DownloadsPage result={result} onDownload={downloadGeoTiff} onGoToUpload={goToUpload} />
      case 'model-insights':
        return <ModelInsightsPage />
      case 'analysis-tools':
        return (
          <ComingSoonPage
            title="Analysis Tools"
            description="A workspace for running downstream analysis (segmentation, classification, change detection) directly on super-resolved output."
            icon={<ToolIcon d="M4 21V14M4 10V3M12 21V12M12 8V3M20 21V16M20 12V3" />}
            onGoToUpload={goToUpload}
          />
        )
      case 'app-urban':
        return <UrbanAnalysisPage result={result} onGoToUpload={goToUpload} />
      case 'app-crop':
        return <CropMonitoringPage result={result} onGoToUpload={goToUpload} />
      case 'app-disaster':
        return (
          <ComingSoonPage
            title="Disaster Assessment"
            description="Damage mapping and affected-area estimation using before/after super-resolved comparisons."
            icon={<ToolIcon d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />}
            onGoToUpload={goToUpload}
          />
        )
      case 'app-change':
        return <ChangeDetectionPage />
    }
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Sidebar page={page} onSelect={setPage} />

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-[68px] shrink-0 items-center justify-between border-b border-[var(--border-c)] bg-[var(--surface)] px-8">
          <span className="font-display text-lg font-semibold text-[var(--text)]">{PAGE_TITLES[page]}</span>
          <div className="flex items-center gap-3">
            <span className="rounded-md border border-[var(--border-c)] bg-[var(--surface-2)] px-2.5 py-1 font-mono text-[11px] text-[var(--text-dim)]">
              SIH 26142
            </span>
            <div className="flex items-center gap-1.5 font-mono text-[11px] text-[var(--text-dim)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--good)] shadow-[0_0_6px_rgba(52,211,153,0.7)]" />
              Model online
            </div>
          </div>
        </div>

        <main className="mx-auto w-full max-w-[1240px] flex-1 px-8 py-8">{renderPage()}</main>

        <footer className="border-t border-[var(--border-c)] px-8 py-5 text-center text-xs text-[var(--text-faint)]">
          GeoSR-4 -- SIH 2026 (26142). Model: SwinIR, trained on real Sentinel-2/NAIP pairs.
        </footer>
      </div>
    </div>
  )
}

export default App
