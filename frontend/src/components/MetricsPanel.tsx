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
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-700">Accuracy vs. ground truth</h3>
        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">measured, not estimated</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {METRIC_INFO.map(({ key, label, full, direction, format }) => (
          <div key={key} className="group relative rounded-lg border border-slate-200 bg-white p-4 text-center transition-shadow hover:shadow-sm">
            <p className="text-xs font-semibold tracking-wide text-slate-400 uppercase" title={full}>
              {label}
            </p>
            <p className="mt-1.5 text-2xl font-semibold text-slate-900 tabular-nums">{format(metrics[key])}</p>
            <p className="mt-1 text-[11px] text-slate-400">{direction}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
