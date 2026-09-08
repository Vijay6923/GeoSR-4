interface Metrics {
  psnr: number
  ssim: number
  sam: number
  ergas: number
}

const METRIC_INFO: { key: keyof Metrics; label: string; direction: string; format: (v: number) => string }[] = [
  { key: 'psnr', label: 'PSNR', direction: 'higher is better', format: (v) => `${v.toFixed(2)} dB` },
  { key: 'ssim', label: 'SSIM', direction: 'higher is better', format: (v) => v.toFixed(3) },
  { key: 'sam', label: 'SAM', direction: 'lower is better', format: (v) => `${v.toFixed(2)}°` },
  { key: 'ergas', label: 'ERGAS', direction: 'lower is better', format: (v) => v.toFixed(2) },
]

export default function MetricsPanel({ metrics }: { metrics: Metrics }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {METRIC_INFO.map(({ key, label, direction, format }) => (
        <div key={key} className="rounded-md border border-slate-200 bg-white p-3 text-center">
          <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">{label}</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{format(metrics[key])}</p>
          <p className="mt-0.5 text-[11px] text-slate-400">{direction}</p>
        </div>
      ))}
    </div>
  )
}
