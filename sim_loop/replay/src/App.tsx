import { useEffect, useMemo, useRef, useState } from 'react'
import type { Session, Summary } from './types'
import CoachWidget, { patternPosition } from './coachWidgets'

const SCREENS: Record<string, string> = {
  S1_COVERAGE_TYPE: 'S1 · Where do you want coverage?',
  S2_INSURED_PERSONS: 'S2 · Who is insured?',
  S3_PERSONAL_INFO: 'S3 · Your details (date of birth + insurance)',
  S4_TARIFF_SELECT: 'S4 · Choose your tariff (first price wall)',
  S5_ADDON_SELECT: 'S5 · Optional add-ons',
  S6_PERSONAL_DATA: 'S6 · Personal + health questions',
  S7_HEALTH_QUESTIONS: 'S7 · Health questions (final price)',
  S8_REVIEW_PURCHASE: 'S8 · Review & confirm (purchase)',
  S7_PURCHASE: 'S7 · Final price & purchase',
}
const ORDER = ['S1_COVERAGE_TYPE', 'S2_INSURED_PERSONS', 'S3_PERSONAL_INFO', 'S4_TARIFF_SELECT',
  'S5_ADDON_SELECT', 'S6_PERSONAL_DATA', 'S7_HEALTH_QUESTIONS', 'S8_REVIEW_PURCHASE']

async function loadJsonl<T>(url: string): Promise<T[]> {
  const text = await (await fetch(url)).text()
  return text.trim().split('\n').filter(Boolean).map((l) => JSON.parse(l) as T)
}

function Bar({ label, v }: { label: string; v?: number }) {
  return (
    <div className="bar"><label>{label}</label>
      <div className="track"><div className="fill" style={{ width: `${Math.round((v ?? 0) * 100)}%` }} /></div>
    </div>
  )
}

export default function App() {
  const [off, setOff] = useState<Session[]>([])
  const [on, setOn] = useState<Session[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [arm, setArm] = useState<'off' | 'on'>('on')
  const [idx, setIdx] = useState(0)
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    ;(async () => {
      setOff(await loadJsonl<Session>('/sessions_coach_off.jsonl'))
      setOn(await loadJsonl<Session>('/sessions_coach_on.jsonl'))
      setSummary(await (await fetch('/summary.json')).json())
    })().catch((e) => console.error(e))
  }, [])

  const sessions = arm === 'on' ? on : off
  const session = sessions[idx]
  const nSteps = session?.steps.length ?? 0
  useEffect(() => setStep(0), [arm, idx])
  useEffect(() => {
    if (!playing) return
    timer.current = window.setInterval(() => {
      setStep((s) => { if (s >= nSteps - 1) { setPlaying(false); return s } return s + 1 })
    }, 1300)
    return () => window.clearInterval(timer.current)
  }, [playing, nSteps])
  const cur = useMemo(() => Math.min(step, Math.max(0, nSteps - 1)), [step, nSteps])

  if (!session || !summary) return <div className="wrap">loading…</div>
  const st = session.steps[cur]
  const po = st.persona_output ?? {}
  const cd = st.coach_decision ?? {}
  const cmd = cd.command
  const acted = !!cd._acted && !!cmd
  const last = cur === nSteps - 1
  const belief = cd.persona_belief

  return (
    <>
      <header>
        <h1>UNIQA Conversion Coach — Simulation Replay</h1>
        <p>The coach is a json-rendered overlay layer ON TOP of the immutable funnel · 32 effectors · turn-by-turn</p>
      </header>

      <div className="wrap">
        <div className="ab">
          {(['off', 'on'] as const).map((k) => {
            const d = summary.arms[k]
            return (
              <div className="abcard" key={k}>
                <h3>Coach {k.toUpperCase()}</h3>
                <div className="big">{Math.round(d.convert_rate * 100)}%</div>
                <small>{d.convert} convert · {d.advisor} advisor · {d.abandon} abandon — of {d.n}<br />
                  {d.coach_interventions} coach interventions</small>
              </div>
            )
          })}
        </div>

        <div className="controls">
          <div className="seg">
            {(['off', 'on'] as const).map((k) => (
              <button key={k} className={arm === k ? 'on' : ''} onClick={() => { setArm(k); setIdx(0) }}>Coach {k.toUpperCase()}</button>
            ))}
          </div>
          <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
            {sessions.map((s, i) => <option key={i} value={i}>#{i + 1} · {s.persona} → {s.outcome}</option>)}
          </select>
          <button onClick={() => setStep((s) => Math.max(0, s - 1))}>‹ Prev</button>
          <button className="primary" onClick={() => setStep((s) => Math.min(nSteps - 1, s + 1))}>Next step ›</button>
          <button onClick={() => setPlaying((p) => !p)}>{playing ? '⏸ Pause' : '▶ Play'}</button>
        </div>

        <div className="stage">
          <div className="stepper">
            {ORDER.map((code) => {
              const reached = session.steps.findIndex((x) => x.step === code)
              let cls = 's'; if (code === st.step) cls += ' cur'; else if (reached > -1 && reached < cur) cls += ' done'
              return <div key={code} className={cls}>{code.split('_')[0]}</div>
            })}
          </div>

          {/* the immutable funnel form, with the coach overlay layered on top */}
          <div className="stagebody">
            <div className="funnelform">
              <div className="ff-head">{SCREENS[st.step] ?? st.step}</div>
              <div className="ff-fields">
                <div className="ff-row" /><div className="ff-row" /><div className="ff-row short" />
                <button className="ff-next" disabled>Weiter ›</button>
              </div>
              <div className="ff-tag">the funnel · immutable</div>
            </div>

            {acted ? (
              <div className={`cw-overlay ${patternPosition(cmd!.fe_pattern || 'card')}`}>
                <CoachWidget c={cmd!} />
              </div>
            ) : (
              <div className="coach-watching">✨ coach watching · NO_ACTION</div>
            )}
          </div>

          {last && (
            <div className="outcome"><span className={`badge ${session.outcome}`}>{session.outcome.replace(/_/g, ' ').toUpperCase()}</span></div>
          )}
        </div>

        {/* mind + coach reasoning */}
        <div className="grid">
          <div className="panel">
            <h4>The customer's mind ({session.persona})</h4>
            <div className="thought">“{po.events?.[0]?.thought || po.reason || '…'}”</div>
            {po.feeling && <span className={`chip ${po.feeling}`}>{po.feeling}</span>}
            <div className="bars">
              <Bar label="attention" v={po.state?.attention} />
              <Bar label="satisfaction" v={po.state?.satisfaction} />
              <Bar label="effort left" v={po.state?.effort_left} />
            </div>
            <div className="assess">decision: <b>{po.decision || '?'}</b></div>
          </div>
          <div className="panel">
            <h4>Coach reasoning</h4>
            {belief && (
              <div className="belief">
                {Object.entries(belief).map(([p, v]) => (
                  <span key={p} className="belief-pill">{p} {(v as number).toFixed(2)}</span>
                ))}
                {typeof cd.intervention_temperature === 'number' && <span className="belief-pill temp">temp {cd.intervention_temperature.toFixed(2)}</span>}
              </div>
            )}
            <div className="assess">{cd.reasoning || '—'}</div>
            {po.intervention_assessment && (
              <div className="assess react">reaction: <b>{po.intervention_assessment.reaction}</b>
                {po.intervention_assessment.effect ? ` — ${po.intervention_assessment.effect}` : ''}</div>
            )}
          </div>
        </div>

        <div className="foot">Data: <code>sim_loop/out/sessions_coach_&#123;off,on&#125;.jsonl</code> · the coach overlay is json-rendered from the effector spec, distinct from the funnel form.</div>
      </div>
    </>
  )
}
