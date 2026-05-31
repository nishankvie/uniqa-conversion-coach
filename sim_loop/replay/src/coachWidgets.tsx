// coachWidgets.tsx — a lightweight JSON-RENDER registry for COACH effectors.
// The coach emits a typed spec {effector, category, fe_pattern, surface, title, message, cta}.
// We map fe_pattern -> a React overlay component, drawn in the coach's OWN visual language
// (elevated, accent, "✨ Coach" tag) — deliberately distinct from the plain funnel form,
// and positioned as an overlay ON TOP of it.
import type { CoachCommand } from './types'

type Cat = 'price' | 'inform' | 'reassure' | 'engage' | 'convert_aid' | 'capture' | 'handoff'

export const CATEGORY_META: Record<string, { color: string; icon: string; label: string }> = {
  price:       { color: '#0046A0', icon: '€',  label: 'price' },
  inform:      { color: '#2563EB', icon: 'i',  label: 'inform' },
  reassure:    { color: '#1FA971', icon: '✓',  label: 'reassure' },
  engage:      { color: '#7C3AED', icon: '✦',  label: 'engage' },
  convert_aid: { color: '#0891B2', icon: '→',  label: 'convert' },
  capture:     { color: '#F0A028', icon: '✉',  label: 'capture' },
  handoff:     { color: '#E2001A', icon: '☎',  label: 'handoff' },
}

// which corner/edge of the funnel stage each pattern occupies
export function patternPosition(fe: string): string {
  switch (fe) {
    case 'banner': case 'progress_ribbon': return 'pos-top'
    case 'toast': return 'pos-toast'
    case 'bottom_sheet': case 'sticky_bar': return 'pos-bottom'
    case 'price_chip': case 'chip': return 'pos-inline'
    default: return 'pos-center' // card, popover, inline_expand
  }
}

function Tag({ cat, fe }: { cat?: string | null; fe: string }) {
  const m = CATEGORY_META[cat || ''] || { color: '#5C6479', icon: '✦', label: cat || '' }
  return (
    <span className="cw-tag" style={{ background: m.color }}>
      <span className="cw-tag-icon">{m.icon}</span>✨ Coach · {fe}
    </span>
  )
}

function Body({ c }: { c: CoachCommand }) {
  return (
    <>
      {c.title && <div className="cw-title">{c.title}</div>}
      {c.message && <div className="cw-body">{c.message}</div>}
      <div className="cw-actions">
        {c.cta && <button className="cw-cta">{c.cta}</button>}
        <button className="cw-x" title="dismiss">×</button>
      </div>
    </>
  )
}

/** The json-render entry point: one effector spec -> one styled overlay widget. */
export default function CoachWidget({ c }: { c: CoachCommand }) {
  const cat = CATEGORY_META[c.category || ''] || CATEGORY_META.inform
  const accent = { ['--cw' as any]: cat.color }
  const fe = c.fe_pattern || 'card'

  switch (fe) {
    case 'banner':
      return <div className={`cw cw-banner`} style={accent}><Tag cat={c.category} fe={fe} /><Body c={c} /></div>
    case 'progress_ribbon':
      return (
        <div className="cw cw-ribbon" style={accent}>
          <Tag cat={c.category} fe={fe} />
          <div className="cw-dots"><i className="on" /><i className="on" /><i /><i /></div>
          <Body c={c} />
        </div>
      )
    case 'toast':
      return <div className="cw cw-toast" style={accent}><Tag cat={c.category} fe={fe} /><Body c={c} /></div>
    case 'bottom_sheet':
      return (
        <div className="cw cw-sheet" style={accent}>
          <div className="cw-handle" />
          <Tag cat={c.category} fe={fe} /><Body c={c} />
        </div>
      )
    case 'sticky_bar':
      return <div className="cw cw-sticky" style={accent}><Tag cat={c.category} fe={fe} /><Body c={c} /></div>
    case 'price_chip':
      return (
        <div className="cw cw-chip cw-price" style={accent}>
          <Tag cat={c.category} fe={fe} />
          <div className="cw-chip-val">{c.title || c.message}</div>
        </div>
      )
    case 'chip':
      return <div className="cw cw-chip" style={accent}><Tag cat={c.category} fe={fe} /><div className="cw-chip-val">{c.title || c.message}</div></div>
    case 'inline_expand':
      return (
        <div className="cw cw-expand" style={accent}>
          <Tag cat={c.category} fe={fe} />
          <div className="cw-title">▾ {c.title || 'What differs'}</div>
          <div className="cw-body">{c.message}</div>
        </div>
      )
    case 'popover':
      return <div className="cw cw-popover" style={accent}><span className="cw-arrow" /><Tag cat={c.category} fe={fe} /><Body c={c} /></div>
    case 'card':
    default:
      return <div className="cw cw-card" style={accent}><Tag cat={c.category} fe={fe} /><Body c={c} /></div>
  }
}
