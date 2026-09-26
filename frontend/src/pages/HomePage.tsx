interface UseCase {
  label: string
  status: 'live' | 'planned'
}

const USE_CASES: UseCase[] = [
  { label: 'Image super-resolution', status: 'live' },
  { label: 'Uncertainty estimation', status: 'live' },
  { label: 'Urban analysis', status: 'live' },
  { label: 'Crop monitoring', status: 'live' },
  { label: 'Disaster assessment', status: 'planned' },
  { label: 'Change detection', status: 'live' },
]

export default function HomePage({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="relative overflow-hidden rounded-[18px] border border-[var(--border-c)] bg-[var(--surface)] px-8 py-14 sm:px-12">
        <div
          className="pointer-events-none absolute -top-24 -right-24 h-[420px] w-[420px] rounded-full opacity-70"
          style={{ background: 'radial-gradient(circle at 35% 35%, #1a3a52 0%, #0d1f2e 45%, transparent 70%)' }}
        />
        <div
          className="pointer-events-none absolute -top-24 -right-24 h-[420px] w-[420px] rounded-full"
          style={{
            background:
              'repeating-conic-gradient(rgba(34,211,238,0.06) 0deg 2deg, transparent 2deg 8deg)',
            maskImage: 'radial-gradient(circle, black 60%, transparent 72%)',
          }}
        />
        <div className="relative max-w-xl">
          <h1 className="font-display text-4xl leading-tight font-semibold text-[var(--text)]">
            Turn medium-resolution satellite imagery into high-detail insight
          </h1>
          <p className="mt-4 text-sm text-[var(--text-dim)]">
            Deep-learning super resolution for Sentinel-2 imagery -- 10m &rarr; &lt;4m, with spectral consistency
            and per-pixel uncertainty, not interpolation.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <span className="rounded-md border border-[var(--border-c)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-dim)]">
              10m Sentinel-2 &rarr; ~2.5m output
            </span>
            <span className="rounded-md border border-[var(--border-c)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-dim)]">
              Spectrally consistent
            </span>
            <span className="rounded-md border border-[var(--border-c)] bg-[var(--surface-2)] px-3 py-1.5 text-xs text-[var(--text-dim)]">
              Uncertainty aware
            </span>
          </div>
          <button
            onClick={onGetStarted}
            className="mt-7 rounded-[10px] bg-[var(--accent)] px-5 py-3 font-display text-sm font-semibold text-[var(--bg)] shadow-[0_0_22px_rgba(255,122,69,0.3)] hover:opacity-90"
          >
            Upload a scene &rarr;
          </button>
        </div>
      </div>

      <div className="rounded-[16px] border border-[var(--border-c)] bg-[var(--surface)] p-6">
        <p className="mb-4 font-mono text-[10.5px] tracking-[0.08em] text-[var(--text-faint)] uppercase">
          Use cases
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {USE_CASES.map((u) => (
            <div key={u.label} className="flex items-center justify-between rounded-[10px] border border-[var(--border-soft)] bg-[var(--surface-2)] px-4 py-3">
              <span className="text-sm text-[var(--text)]">{u.label}</span>
              {u.status === 'live' ? (
                <span className="rounded-full bg-[var(--good)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--good)]">live</span>
              ) : (
                <span className="rounded-full bg-[var(--warn)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--warn)]">planned</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
