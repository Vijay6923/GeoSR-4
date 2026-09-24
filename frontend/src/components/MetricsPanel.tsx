interface Metrics {
  psnr: number
  ssim: number
  sam: number
  ergas: number
}

const METRIC_INFO: { key: keyof Metrics; label: string; full: string; direction: string; format: (v: number) => string }[] = [
  { key: 'psnr', label: 'PSNR', full: 'Peak Signal-to-Noise Ratio', direction: 'higher is better', format: (v) => `${v.toFixed(2)} dB` },
  { key: 'ssim', label: 'SSIM', full: 'Structural Similarity', direction: 'higher is better', format: (v) => v.toFixed(3) },
  { key: 'sam', label: 'SAM', full: 'Spectral Angle Mapper', direction: 'lower is better', format: (v) => `${v.toFixed(2)}°` },
  { key: 'ergas', label: 'ERGAS', full: 'Relative Global Error', direction: 'lower is better', format: (v) => v.toFixed(2) },
]

export default function MetricsPanel({ metrics }: { metrics: Metrics }) {
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <p className="font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">Validation metrics</p>
        <span className="rounded-full bg-[var(--good)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--good)]">
          ground truth provided
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {METRIC_INFO.map(({ key, label, full, direction, format }) => (
          <div key={key} className="rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] p-3.5">
            <p className="text-[11.5px] text-[var(--text-dim)]" title={full}>
              {label}
            </p>
            <p className="mt-0.5 font-mono text-[25px] text-[var(--text)] tabular-nums">{format(metrics[key])}</p>
            <p className="mt-0.5 text-[10.5px] text-[var(--text-faint)]">{direction}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
