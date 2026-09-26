import { useState } from 'react'
import type { ReactNode } from 'react'

export type Page =
  | 'home'
  | 'upload'
  | 'compare'
  | 'analysis-tools'
  | 'model-insights'
  | 'uncertainty'
  | 'downloads'
  | 'app-urban'
  | 'app-crop'
  | 'app-disaster'
  | 'app-change'

interface NavItemDef {
  page: Page
  label: string
  icon: ReactNode
  disabled?: boolean
}

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  )
}

const MAIN_ITEMS: NavItemDef[] = [
  { page: 'home', label: 'Home', icon: <Icon><path d="M3 12l9-9 9 9" /><path d="M5 10v10h14V10" /></Icon> },
  { page: 'upload', label: 'Upload & Enhance', icon: <Icon><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></Icon> },
  { page: 'compare', label: 'Compare View', icon: <Icon><rect x="3" y="4" width="8" height="16" rx="1" /><rect x="13" y="4" width="8" height="16" rx="1" /></Icon> },
  { page: 'analysis-tools', label: 'Analysis Tools', icon: <Icon><line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" /><line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /></Icon> },
]

const APPLICATIONS: NavItemDef[] = [
  { page: 'app-urban', label: 'Urban Analysis', icon: <Icon><path d="M3 21h18" /><path d="M6 21V8l6-4 6 4v13" /><path d="M10 21v-6h4v6" /></Icon> },
  { page: 'app-crop', label: 'Crop Monitoring', icon: <Icon><path d="M12 22V12" /><path d="M12 12C12 7 8 6 5 6c0 5 2 8 7 6z" /><path d="M12 12c0-5 4-6 7-6 0 5-2 8-7 6z" /></Icon> },
  { page: 'app-change', label: 'Change Detection', icon: <Icon><path d="M17 3l4 4-4 4" /><path d="M3 11V9a4 4 0 0 1 4-4h14" /><path d="M7 21l-4-4 4-4" /><path d="M21 13v2a4 4 0 0 1-4 4H3" /></Icon> },
]

const TAIL_ITEMS: NavItemDef[] = [
  { page: 'model-insights', label: 'Model Insights', icon: <Icon><circle cx="12" cy="12" r="9" /><path d="M12 8v4l3 2" /></Icon> },
  { page: 'uncertainty', label: 'Uncertainty Map', icon: <Icon><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></Icon> },
  { page: 'downloads', label: 'Downloads', icon: <Icon><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></Icon> },
]

function NavRow({ item, active, onSelect, indent }: { item: NavItemDef; active: boolean; onSelect: (p: Page) => void; indent?: boolean }) {
  if (item.disabled) {
    return (
      <div
        className={`flex w-full cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-faint)] opacity-50 ${indent ? 'pl-9' : ''}`}
        aria-disabled="true"
      >
        <span>{item.icon}</span>
        <span className="flex-1">{item.label}</span>
        <span className="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[9px] font-medium">Soon</span>
      </div>
    )
  }

  return (
    <button
      onClick={() => onSelect(item.page)}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${indent ? 'pl-9' : ''} ${
        active ? 'bg-[var(--accent)] text-[var(--bg)] font-medium' : 'text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
      }`}
    >
      <span className={active ? 'text-[var(--bg)]' : 'text-[var(--text-faint)]'}>{item.icon}</span>
      {item.label}
    </button>
  )
}

export default function Sidebar({ page, onSelect }: { page: Page; onSelect: (p: Page) => void }) {
  const [appsOpen, setAppsOpen] = useState(true)

  return (
    <aside className="flex h-screen w-[248px] shrink-0 flex-col border-r border-[var(--border-c)] bg-[var(--surface)]">
      <div className="flex items-center gap-2.5 border-b border-[var(--border-c)] px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-[8px] border border-[rgba(255,122,69,0.35)] bg-[var(--accent-soft)]">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="9" />
            <ellipse cx="12" cy="12" rx="4" ry="9" transform="rotate(35 12 12)" />
          </svg>
        </div>
        <span className="font-display text-[17px] font-bold text-[var(--text)]">GeoSR&#8209;4</span>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {MAIN_ITEMS.map((item) => (
          <NavRow key={item.page} item={item} active={page === item.page} onSelect={onSelect} />
        ))}

        <button
          onClick={() => setAppsOpen((v) => !v)}
          className="mt-0.5 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-[var(--text-dim)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
        >
          <Icon><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></Icon>
          <span className="flex-1">Applications</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${appsOpen ? 'rotate-90' : ''}`}>
            <path d="M9 18l6-6-6-6" />
          </svg>
        </button>
        {appsOpen && (
          <div className="space-y-0.5">
            {APPLICATIONS.map((item) => (
              <NavRow key={item.page} item={item} active={page === item.page} onSelect={onSelect} indent />
            ))}
          </div>
        )}

        <div className="my-3 h-px bg-[var(--border-c)]" />

        {TAIL_ITEMS.map((item) => (
          <NavRow key={item.page} item={item} active={page === item.page} onSelect={onSelect} />
        ))}
      </nav>

      <div className="border-t border-[var(--border-c)] px-5 py-4 text-[11px] text-[var(--text-faint)]">
        SIH 26142 &middot; NTRO
      </div>
    </aside>
  )
}
