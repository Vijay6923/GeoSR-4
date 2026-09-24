interface StatRow {
  label: string
  value: string
}

const ARCHITECTURE: StatRow[] = [
  { label: 'Primary model', value: 'SwinIR (transformer, window attention)' },
  { label: 'Confidence model', value: 'EDSR + heteroscedastic uncertainty head' },
  { label: 'Serving strategy', value: 'Confidence-weighted fusion of both models' },
  { label: 'Scale factor', value: '4x (10m -> 2.5m)' },
  { label: 'Training data', value: 'SEN2NAIP, real Sentinel-2 / NAIP pairs' },
]

const VALIDATION: StatRow[] = [
  { label: 'PSNR (fused, n=279)', value: '16.89 dB' },
  { label: 'SSIM (fused, n=279)', value: '0.4471' },
  { label: 'SAM (fused, n=279)', value: '11.84°' },
  { label: 'ERGAS median (fused, n=279)', value: '~8.87' },
  { label: 'Uncertainty calibration', value: 'r ≈ 0.21 (real, modest)' },
]

function StatCard({ title, rows }: { title: string; rows: StatRow[] }) {
  return (
    <div className="rounded-[14px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
      <p className="mb-4 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">{title}</p>
      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-4 border-b border-[var(--border-soft)] pb-3 last:border-0 last:pb-0">
            <span className="text-sm text-[var(--text-dim)]">{r.label}</span>
            <span className="font-mono text-sm text-[var(--text)]">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ModelInsightsPage() {
  return (
    <div className="flex flex-col gap-6">
      <p className="max-w-2xl text-sm text-[var(--text-dim)]">
        Numbers measured on the held-out validation split (tile-disjoint from training), never estimated or
        assumed. Full reasoning and history for every model decision is logged in this project's{' '}
        <code className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 font-mono text-xs text-[var(--text)]">decisions.md</code>.
      </p>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <StatCard title="Architecture" rows={ARCHITECTURE} />
        <StatCard title="Validation (real, measured)" rows={VALIDATION} />
      </div>
    </div>
  )
}
