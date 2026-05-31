export interface PersonaEvent {
  step: string
  type: string
  target: string | null
  value: unknown
  t: number
  thought?: string
}

export interface PersonaState {
  attention?: number
  satisfaction?: number
  effort_left?: number
  grasp?: number
  effort_vs_reward?: number
}

export interface InterventionAssessment {
  reaction?: string
  engaged?: boolean
  effect?: string
}

export interface PersonaOutput {
  events?: PersonaEvent[]
  decision?: 'continue' | 'leave' | string
  reason?: string
  state?: PersonaState
  feeling?: string
  intent?: string
  intervention_assessment?: InterventionAssessment
}

export interface CoachCommand {
  effector: string
  category?: string | null
  fe_pattern?: string
  surface?: string
  target?: string | null
  title?: string
  message?: string
  cta?: string
}

export interface CoachDecision {
  reasoning?: string
  command?: CoachCommand
  value_estimate?: number
  persona_belief?: Record<string, number>
  detected_pains?: string[]
  intervention_temperature?: number
  _acted?: boolean
}

export interface SessionStep {
  step: string
  shown_coach?: unknown
  persona_output: PersonaOutput
  coach_decision?: CoachDecision
}

export interface Session {
  persona: string
  arm: 'off' | 'on' | string
  session_instance?: Record<string, unknown>
  outcome: string
  n_steps: number
  coach_interventions: number
  steps: SessionStep[]
}

export interface ArmSummary {
  n: number
  convert: number
  convert_rate: number
  advisor: number
  abandon: number
  coach_interventions: number
}

export interface Summary {
  arms: { off: ArmSummary; on: ArmSummary }
  persona_mix?: Record<string, number>
}
