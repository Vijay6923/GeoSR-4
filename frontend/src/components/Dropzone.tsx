import { useRef, useState } from 'react'

interface DropzoneProps {
  file: File | null
  onFileSelect: (file: File | null) => void
  label: string
  hint?: string
  compact?: boolean
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Dropzone({ file, onFileSelect, label, hint, compact }: DropzoneProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const pickFile = (fileList: FileList | null) => {
    const f = fileList?.[0]
    if (f) onFileSelect(f)
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700">{label}</label>
      {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          pickFile(e.dataTransfer.files)
        }}
        className={`mt-2 flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed px-4 transition-colors ${compact ? 'py-2.5' : 'py-5'} ${
          dragOver
            ? 'border-emerald-400 bg-emerald-50'
            : file
              ? 'border-slate-300 bg-slate-50'
              : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".tif,.tiff"
          onChange={(e) => pickFile(e.target.files)}
          className="hidden"
        />

        <div className={`flex ${compact ? 'h-8 w-8' : 'h-10 w-10'} shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500`}>
          <svg width={compact ? 16 : 18} height={compact ? 16 : 18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <div className="min-w-0 flex-1">
          {file ? (
            <>
              <p className="truncate text-sm font-medium text-slate-800">{file.name}</p>
              <p className="text-xs text-slate-400">{formatBytes(file.size)}</p>
            </>
          ) : (
            <p className="text-sm text-slate-500">
              <span className="font-medium text-slate-700">Click to browse</span> or drag a GeoTIFF here
            </p>
          )}
        </div>

        {file && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onFileSelect(null)
              if (inputRef.current) inputRef.current.value = ''
            }}
            className="shrink-0 rounded-full p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
            aria-label="Remove file"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>
    </div>
  )
}
