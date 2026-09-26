import heroImage from '../assets/hero-satellite.jpg'

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
          className="pointer-events-none absolute -top-16 -right-16 h-[380px] w-[380px] overflow-hidden rounded-full border border-[var(--border-c)] opacity-90 sm:h-[440px] sm:w-[440px]"
          style={{ boxShadow: '0 0 60px rgba(255,122,69,0.12)' }}
        >
          <img src={heroImage} alt="" className="animate-float h-full w-full object-cover" />
          <div
            className="absolute inset-0"
            style={{ background: 'radial-gradient(circle, transparent 55%, var(--surface) 92%)' }}
          />
        </div>
        <p className="pointer-events-none absolute top-3 right-3 text-[10px] text-[var(--text-faint)] sm:top-4 sm:right-4">
          Earth-observation satellite (artist rendering) &middot; NASA/JPL
        </p>
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
