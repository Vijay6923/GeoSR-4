import { useRef, useState } from 'react'

interface BeforeAfterSliderProps {
  beforeSrc: string
  afterSrc: string
  beforeLabel: string
  afterLabel: string
}

const LENS_SIZE = 170 // px
const ZOOM = 3 // magnifier zoom factor

interface LensState {
  x: number
  y: number
  showBefore: boolean
}

export default function BeforeAfterSlider({ beforeSrc, afterSrc, beforeLabel, afterLabel }: BeforeAfterSliderProps) {
  const [pos, setPos] = useState(50) // percent, 0 = all "after", 100 = all "before"
  const [lens, setLens] = useState<LensState | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const updateLens = (clientX: number, clientY: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = Math.min(Math.max(clientX - rect.left, 0), rect.width)
    const y = Math.min(Math.max(clientY - rect.top, 0), rect.height)
    setLens({ x, y, showBefore: (x / rect.width) * 100 < pos })
  }

  let lensStyle: React.CSSProperties | undefined
  if (lens && containerRef.current) {
    const rect = containerRef.current.getBoundingClientRect()
    const bgW = rect.width * ZOOM
    const bgH = rect.height * ZOOM
    lensStyle = {
      left: lens.x - LENS_SIZE / 2,
      top: lens.y - LENS_SIZE / 2,
      width: LENS_SIZE,
      height: LENS_SIZE,
      backgroundImage: `url(${lens.showBefore ? beforeSrc : afterSrc})`,
      backgroundSize: `${bgW}px ${bgH}px`,
      backgroundPosition: `${-(lens.x * ZOOM - LENS_SIZE / 2)}px ${-(lens.y * ZOOM - LENS_SIZE / 2)}px`,
    }
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full select-none overflow-hidden rounded-lg border border-slate-200 shadow-sm"
      onMouseMove={(e) => updateLens(e.clientX, e.clientY)}
      onMouseLeave={() => setLens(null)}
      onTouchMove={(e) => {
        const t = e.touches[0]
        if (t) updateLens(t.clientX, t.clientY)
      }}
      onTouchEnd={() => setLens(null)}
    >
      {/* base layer: after (SR output), fills the whole container */}
      <img src={afterSrc} alt={afterLabel} className="block w-full" draggable={false} />

      {/* overlay layer: before (LR input), clipped to the left pos% */}
      <div className="pointer-events-none absolute inset-0" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
        <img src={beforeSrc} alt={beforeLabel} className="block w-full" draggable={false} />
      </div>

      {/* divider line + handle, purely visual */}
      <div
        className="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.4)]"
        style={{ left: `${pos}%` }}
      >
        <div className="absolute top-1/2 left-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-slate-600 shadow-lg ring-1 ring-black/5">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M8 6l-6 6 6 6M16 6l6 6-6 6" />
          </svg>
        </div>
      </div>

      {/* labels */}
      <div className="pointer-events-none absolute top-3 left-3 rounded-md bg-black/55 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm">
        {beforeLabel}
      </div>
      <div className="pointer-events-none absolute top-3 right-3 rounded-md bg-emerald-600/85 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm">
        {afterLabel}
      </div>

      {/* magnifier lens: follows the cursor, zoomed crop of whichever side (before/after) is under it */}
      {lensStyle && (
        <div
          className="pointer-events-none absolute rounded-full border-2 border-white bg-no-repeat shadow-xl ring-1 ring-black/10"
          style={lensStyle}
        />
      )}

      {/* invisible range input drives the whole thing -- native drag/touch/keyboard handling for free */}
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
        aria-label="Before/after comparison slider"
      />
    </div>
  )
}
