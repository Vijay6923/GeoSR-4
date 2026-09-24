import { useRef, useState } from 'react'

interface DropzoneProps {
  file: File | null
  onFileSelect: (file: File | null) => void
  label?: string
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
      {label && <label className="block text-sm font-medium text-[var(--text-dim)]">{label}</label>}
      {hint && <p className="mt-0.5 text-xs text-[var(--text-faint)]">{hint}</p>}

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
        className={`${label || hint ? 'mt-2' : ''} flex cursor-pointer items-center gap-3 rounded-[10px] border-[1.5px] border-dashed px-4 transition-colors ${compact ? 'py-2.5' : 'py-6'} ${
          dragOver
            ? 'border-[var(--cyan)] bg-[var(--cyan-soft)]'
            : 'border-[var(--border-c)] bg-[var(--surface-2)] hover:border-[var(--text-faint)]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".tif,.tiff"
          onChange={(e) => pickFile(e.target.files)}
          className="hidden"
        />

        <div className={`flex ${compact ? 'h-8 w-8' : 'h-10 w-10'} shrink-0 items-center justify-center text-[var(--cyan)]`}>
          <svg width={compact ? 16 : 20} height={compact ? 16 : 20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <div className="min-w-0 flex-1">
          {file ? (
            <>
              <p className="truncate font-mono text-sm text-[var(--text)]">{file.name}</p>
              <p className="text-xs text-[var(--text-faint)]">{formatBytes(file.size)}</p>
            </>
          ) : (
            <p className="text-sm text-[var(--text-dim)]">
              <span className="font-medium text-[var(--text)]">Click to browse</span> or drag a GeoTIFF here
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
            className="shrink-0 rounded-full p-1 text-[var(--text-faint)] hover:bg-[var(--border-c)] hover:text-[var(--text)]"
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
