import type { ReactNode } from 'react'

interface ComingSoonPageProps {
  title: string
  description: string
  icon: ReactNode
  onGoToUpload: () => void
}

export default function ComingSoonPage({ title, description, icon, onGoToUpload }: ComingSoonPageProps) {
  return (
    <div className="flex min-h-[480px] flex-col items-center justify-center rounded-[16px] border border-dashed border-[var(--border-c)] bg-[var(--surface)] px-8 py-20 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-[12px] border border-[var(--border-c)] bg-[var(--surface-2)] text-[var(--text-dim)]">
        {icon}
      </div>
      <span className="mb-3 rounded-full bg-[var(--warn)]/10 px-2.5 py-1 text-[11px] font-medium text-[var(--warn)]">
        Coming soon
      </span>
      <h2 className="font-display text-xl font-semibold text-[var(--text)]">{title}</h2>
      <p className="mt-2.5 max-w-md text-sm text-[var(--text-dim)]">{description}</p>
      <p className="mt-4 max-w-md text-xs text-[var(--text-faint)]">
        This is on the roadmap but not built yet -- we don't show placeholder numbers or fake results here. The
        core super-resolution + uncertainty pipeline is real and working today.
      </p>
      <button
        onClick={onGoToUpload}
        className="mt-6 rounded-[10px] border border-[var(--border-c)] bg-[var(--surface-2)] px-4 py-2 text-sm font-medium text-[var(--text-dim)] hover:text-[var(--text)]"
      >
        Go to Upload &amp; Enhance instead
      </button>
    </div>
  )
}
