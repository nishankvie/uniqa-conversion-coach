# EU AI Act + GDPR Compliance Spec: Insurance Conversion AI (UNIQA Coach)
> Research brief | Zero One Hackathon | 2026-05-30
> Audience: Engineering team building UNIQA Conversion Coach

---

## EXECUTIVE SUMMARY

The UNIQA Conversion Coach sits in a **legal gray zone** that can be engineered into compliance with focused effort. The key findings:

1. **EU AI Act classification**: The Coach is **probably NOT high-risk** under Annex III — but only if it's framed as a sales UX optimization tool, NOT a risk assessment or pricing engine. The product recommendation function (Optimal vs. Start) needs careful scoping. Article 6(3) self-assessment documentation is required.

2. **GDPR Article 22**: The persona routing decision (advisor handoff for Peter, online-only for Franz) **likely qualifies as profiling** under Art. 4(4) and may trigger Art. 22 if routing restricts or differentially enables access to the purchase path. Requires consent OR legal basis + right to object.

3. **Local/ONNX inference**: Dramatically improves privacy posture but does NOT eliminate legal basis requirements. UNIQA remains the data controller even when inference runs in the browser.

4. **localStorage**: Legally valid for form persistence IF consent is obtained (ePrivacy Directive applies). The "data never leaves device" argument is correct for data minimization but not for consent exemption.

5. **Austrian law**: FMA/VAG's Insurance Distribution Directive implementation adds independent obligations — the Coach's tariff recommendations trigger IDD needs analysis requirements even in a digital-only funnel.

6. **30-day TTL with explicit consent**: Legally sufficient if consent specifically names the duration and purpose. Session-scoped (browser-close) would be defensible without consent; 30-day requires it.

---

## PART 1: EU AI ACT CLASSIFICATION

### 1.1 Applicable Texts

| Source | Reference | Status as of 2026 |
|--------|-----------|-------------------|
| EU AI Act | Regulation (EU) 2024/1689 | In force Aug 1, 2024. Annex III rules apply **Aug 2, 2026** |
| Article 6 | High-risk classification criteria | Applies from Aug 2026 |
| Annex III | High-risk use case list | Applies from Aug 2026 |
| Article 50 | Real-time AI transparency | Applies from **Aug 2, 2025** |

> **⚠️ Timeline note**: For this hackathon prototype, the Annex III high-risk rules don't technically apply until August 2026. **BUT** Article 50 (transparency when AI interacts with people in real-time) applies NOW. Build for Art. 50 compliance immediately; design for Annex III compliance to avoid rework.

---

### 1.2 Annex III High-Risk Classification Analysis

**Annex III, Section 5 (essential private/public services)** is the relevant category:

> **5(b)** — AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score *(excludes fraud detection)*
>
> **5(c)** — AI systems intended to be used for **risk assessment and pricing in relation to natural persons in the case of life and health insurance**

#### Is the UNIQA Coach a "risk assessment and pricing" system?

**Arguments FOR high-risk classification (5(c)):**
- The system operates within an insurance sales funnel for health insurance (Privatarzt)
- It recommends specific tariffs (Start vs. Optimal) based on behavioral profiling
- It routes users toward different service channels based on automated persona classification
- If the Coach uses health-related behavioral signals (answers to health questions) to adapt its recommendations, this edges toward risk assessment

**Arguments AGAINST high-risk classification (5(c)):**
- The prices are pre-determined flat tariffs, NOT individually calculated premiums
- The Coach does NOT perform actuarial risk assessment — it performs dropout prediction + UX optimization
- The tariff recommendation is a sales/marketing intervention, not an underwriting decision
- The actual underwriting (health questions → price delta) is handled by UNIQA's existing pricing engine, which is separate from the Coach

**Recommended classification: NOT high-risk, with Article 6(3) documentation**

Under Article 6(3) of the EU AI Act, a provider can self-assess that an Annex III-listed system is NOT high-risk if it does not pose a significant risk of harm to health, safety, or fundamental rights. This requires:
- Written assessment documenting why the system falls outside the high-risk scope
- Registration in the EU database (Article 60) — for the hackathon prototype, note this in REPORT.md

**Concrete scoping decision to make this defensible:**

```
HIGH-RISK (Annex III 5(c)) — KEEP SEPARATE FROM COACH:
✗ Any signal from health questions (Step 6) feeding back into Coach recommendations
✗ Any price personalization beyond the flat Start/Optimal tariffs
✗ Any denial or restriction of insurance access based on Coach outputs

NOT HIGH-RISK — THE COACH SCOPE:
✓ Behavioral dropout prediction (dwell time, hover, navigation patterns)
✓ Persona classification from UX signals (not health status signals)
✓ UX intervention selection (which widget to show)
✓ Channel routing (online vs. advisor) based on behavioral preference signals
✓ Pre-determined message templates (not individualized pricing language)
```

**Implementation guard**: The Coach should explicitly NOT receive Step 6 (health questions) outputs as features. This is a clear architectural boundary that keeps it out of health risk assessment territory.

---

### 1.3 Articles 13, 14, 15 — Practical Requirements If High-Risk Applies

These apply only if the system IS classified as high-risk. Document them now; design for them regardless (good practice + prepares for potential regulatory evolution).

#### Article 13 — Transparency Requirements in Practice

The high-risk AI system must be supplied with instructions/documentation covering:

| Requirement | What it means for the Coach | Hackathon minimum |
|-------------|----------------------------|-------------------|
| Provider identity | UNIQA's legal entity name + contact | In REPORT.md + UI disclosure |
| Intended purpose | "Conversion rate optimization in insurance sales funnel" | Document in system spec |
| Performance characteristics | Persona classifier accuracy, abandonment predictor AUC-ROC | Evaluation metrics required |
| Known limitations | "System trained on synthetic data; may not generalize to all demographics" | Documented in model card |
| Level of accuracy declared | Specific number (e.g., AUC-ROC 0.79 on Step 4) | Log in evaluation output |
| Human oversight info | How operators can review/disable the system | Admin interface needed |
| Logging capabilities | Inputs/outputs logged, how long | Specify TTL |

For the **real-time interaction** (when the coach shows a widget to the user), **Article 50** (already in force) requires:
- Users must be informed they are interacting with an AI system
- This must be done "in a clear and distinguishable manner"
- Exemption: if the AI's role is obvious from context — but a subtle tooltip/widget does NOT qualify as "obvious"

> **UI requirement**: The Coach must display something like: *"Personalized tips powered by AI"* or a small ⓘ icon that explains "This suggestion is generated by an automated system based on your behavior." This is NOT optional under Art. 50 (applies Aug 2025).

#### Article 14 — Human Oversight Requirements in Practice

High-risk AI systems must enable natural persons to:
- **Understand** the system's output (interpretable decisions)
- **Detect anomalies** / malfunctions in the AI's behavior
- **Override or interrupt** the system at any point

**Practical implementation:**
```
Minimum viable compliance:
1. Admin dashboard showing: which persona was classified, which interventions fired, user outcome
2. Kill switch: ability to disable Coach for all users (feature flag)
3. Audit log: every classification + intervention stored with timestamp
4. Bias monitoring: flag if one segment is systematically receiving disadvantageous routing

Nice-to-have (for real deployment):
5. Per-session override: UNIQA agent can override Coach decision during live session
6. A/B kill-switch: disable RL policy, fall back to rule-based
7. Regular review cadence documented (e.g., weekly human review of sample outputs)
```

#### Article 15 — Accuracy, Robustness, Cybersecurity

**Accuracy obligations:**
- Must declare the metric(s) and thresholds
- For abandonment predictor: declare AUC-ROC and confidence interval
- Must maintain accuracy throughout lifecycle (retraining schedule)

**Robustness obligations:**
- Must function correctly under reasonably foreseeable misuse
- For the Coach: test what happens if behavioral signals are manipulated (e.g., bot traffic)
- Fallback: if classifier is below confidence threshold → show no intervention (do nothing rather than misclassify)

**Cybersecurity obligations:**
- The model itself (ONNX file if deployed client-side) must be tamper-resistant
- Adversarial inputs (deliberate hover manipulation) should not cause harmful outputs

---

## PART 2: GDPR ANALYSIS

### 2.1 Article 22 — Automated Decision-Making

**Relevant GDPR provisions:**
- **Art. 4(4)**: Profiling — automated processing of personal data to evaluate personal aspects
- **Art. 22(1)**: Right not to be subject to solely automated decisions with legal or "similarly significant" effects
- **Art. 22(3)**: If Art. 22 applies: right to human intervention, right to express point of view, right to contest decision
- **Recital 71**: "significantly affects" includes: automatic refusal of online credit applications, e-recruiting decisions WITHOUT human intervention

#### Does the Coach constitute Art. 22 automated decision-making?

**Definite profiling (Art. 4(4)):**
The behavioral analysis + persona classification IS profiling under Art. 4(4). No question. Requires:
- Disclosure in privacy notice
- Right to object (Art. 21)

**Article 22(1) — "significantly similar effects" analysis:**

| Coach Action | Art. 22 triggered? | Reasoning |
|-------------|-------------------|-----------|
| Showing a price reframe tooltip | ❌ No | Informational only; user retains full agency |
| Showing "upgrade path" message | ❌ No | Informational only |
| Routing Peter to advisor callback | ⚠️ **Possibly yes** | Differentially routes user to a non-online purchase path; could be argued to restrict online purchase rights |
| Blocking online purchase (hypothetical) | ✅ Yes | Would clearly trigger Art. 22 |
| Showing/hiding certain tariff options | ✅ Yes | Restriction of choice = significant effect |

**EDPB guidance (Opinion 3/2019 on Article 22)**: The EDPB interprets "significantly similar effects" broadly, including: "access to or denial of information or services." If the Coach's advisor routing causes some users to not complete online purchase (and instead get an advisor callback that may or may not convert), this IS a significantly similar effect on their insurance purchase process.

**Practical recommendation**: Design the Coach so that:
1. No purchase path is BLOCKED (Peter still gets the online funnel — the advisor callback is an ADD-ON, not a replacement)
2. The routing suggestion is clearly framed as a recommendation the user can dismiss
3. The "Franz never sees advisor handoff" rule is actually GOOD for Art. 22 compliance — you're not restricting his path

**Legal basis for profiling** (needed regardless of Art. 22):
- **Consent (Art. 6(1)(a))**: Simplest. Get consent for "personalizing your insurance experience" at the start of the funnel.
- **Legitimate interests (Art. 6(1)(f))**: Arguable for basic analytics, but risky for profiling. LIA (Legitimate Interest Assessment) required. UNIQA's interest in conversion optimization vs. user's interest in not being profiled — this is contestable.
- **Contract performance (Art. 6(1)(b))**: Cannot apply — no contract exists yet during the sales funnel.

**Recommended legal basis: Consent** — asked at funnel entry with clear explanation. This is also consistent with Austrian DSB (Data Protection Authority) expectations.

---

### 2.2 Rights Triggered by the Coach System

| Right | Trigger | What must be implemented |
|-------|---------|------------------------|
| **Art. 13 — Information** | Always (coach deployed on UNIQA website) | Privacy notice must include: "We use AI to personalize your experience, including behavioral analysis and persona-based interventions" |
| **Art. 15 — Access** | On request | Must be able to provide: what persona was assigned, what interventions were shown, what data was used |
| **Art. 17 — Erasure** | On request or consent withdrawal | Must be able to delete all stored session/behavioral data |
| **Art. 20 — Portability** | On request (if consent basis) | Provide behavioral event log in machine-readable format |
| **Art. 21 — Object to profiling** | Must provide opt-out | Easy opt-out from Coach personalization; falls back to standard funnel |
| **Art. 22(3)** | If Art. 22 applies to routing | Human review of routing decision; ability to contest |

---

## PART 3: FORM PROGRESS PERSISTENCE

### 3.1 Legal Framework

**Relevant law:**
- GDPR Art. 5(1)(b): Purpose limitation — form data collected for quote completion can't be reused for marketing
- GDPR Art. 5(1)(e): Storage limitation — keep no longer than necessary
- **ePrivacy Directive (2009/136/EC), Art. 5(3)**: Any storage of/access to information on user's terminal equipment requires consent, UNLESS strictly necessary for service explicitly requested by user
- Austrian **TKG 2021 (Telekommunikationsgesetz)** §165: Austrian implementation of ePrivacy; same consent requirement for cookies/localStorage

### 3.2 Can localStorage Satisfy GDPR?

**Short answer: Yes, if consent is obtained AND data doesn't leave the device.**

**Detailed analysis:**

```
localStorage contains personal data (name, DOB, etc.)
        ↓
ePrivacy Directive applies (Austrian TKG §165)
        ↓
UNLESS strictly necessary for user-requested service
        ↓
"Strictly necessary" = user explicitly requested to save progress?
        ↓
    If YES: no consent needed under ePrivacy (but GDPR Art. 13 notice still required)
    If NO:  consent required before writing to localStorage
```

**"Strictly necessary" test for form progress persistence:**
- ✅ User clicked "Save my progress" button → clearly requested → strictly necessary
- ❌ Auto-save on every keystroke without user knowing → NOT strictly necessary, consent required
- ⚠️ Auto-save with a banner saying "We're saving your progress" → gray area; consent is safer

**GDPR + localStorage compatibility:**
- The data controller (UNIQA) still determines the purpose of localStorage use — GDPR applies
- "Data never leaves the device" is **true for data minimization compliance** — this is a strong Art. 25 (Privacy by Design) argument
- BUT UNIQA is still the data controller; must still have legal basis and provide disclosure

**Recommendation:**
```
Storage approach:
  - Form progress (personal data): localStorage with explicit user-initiated save + consent
  - Behavioral signals (hover, dwell, navigation): sessionStorage (auto-cleared on tab close)
    OR local-only with no server transmission + no consent required if truly never transmitted
  - Persona classification result: sessionStorage only, never persisted to localStorage
  - No server-side storage of partial form data unless explicitly requested by user
```

### 3.3 Practical Storage Architecture

```
╔══════════════════════════════════════════════════════════════╗
║  BROWSER (user's device)                                      ║
║                                                               ║
║  sessionStorage (cleared on tab close — no consent needed)   ║
║  ├── behavioral_events: [{step, event, dwell_ms, t}...]       ║
║  ├── persona_estimate: {judith: 0.2, franz: 0.7, peter: 0.1} ║
║  └── session_id: "anonymous-uuid" (no PII)                    ║
║                                                               ║
║  localStorage (persisted — ePrivacy consent required)         ║
║  ├── ONLY if user explicitly clicked "Save my progress"       ║
║  ├── form_progress: {step: 4, name: "Max", dob: "1990-01-15"} ║
║  ├── consent_timestamp: "2026-05-30T14:22:00Z"               ║
║  ├── consent_version: "v1.2"                                  ║
║  └── ttl_expires: "2026-06-29T14:22:00Z" (30 days)           ║
║                                                               ║
║  ONNX Model (static asset, loaded once)                       ║
║  └── abandonment_predictor.onnx (no personal data inside)     ║
╚══════════════════════════════════════════════════════════════╝
                              │
                    Only sends to server:
                    - Quote request (when user submits)
                    - Aggregate anonymized analytics (no PII)
                    - Nothing during Coach operation
```

### 3.4 Retention Policy

| Data type | Recommended TTL | Legal basis | Notes |
|-----------|----------------|-------------|-------|
| sessionStorage (behavioral signals) | Browser session (auto) | Strictly necessary / legitimate interests | No PII if anonymous session IDs used |
| localStorage form progress | 30 days with consent | Consent | Must expire and auto-delete; must be deletable by user |
| Server-side partial quote | 7 days maximum | Consent | Only if user explicitly requests email reminder |
| Completed purchase data | Per insurance contract duration | Contract performance | Out of scope for Coach |
| Audit logs (intervention decisions) | 1-3 years | Regulatory obligation / legitimate interests | Required for AI Act compliance; UNIQA decides |

**Is 30-day TTL with explicit consent legally sufficient?**

**YES**, provided:
1. The consent specifically states "We will save your progress for up to 30 days so you can complete your application later"
2. User can delete at any time (e.g., a "Clear my saved progress" button)
3. Data automatically deleted at TTL without further action required from user
4. UNIQA doesn't use the partial form data for re-marketing (purpose limitation)
5. DSR (Data Subject Request) responses include this data

---

## PART 4: LOCAL MODEL INFERENCE (ONNX/WASM)

### 4.1 What Changes Under GDPR When Inference Is On-Device

| Factor | Server-side inference | Client-side ONNX/WASM |
|--------|----------------------|----------------------|
| Personal data transmitted | YES (behavioral signals sent to server) | NO (signals processed locally) |
| GDPR data minimization | Poor (server receives all signals) | Excellent (data stays on device) |
| Data controller | UNIQA | UNIQA (unchanged) |
| Legal basis requirement | YES | YES (unchanged) |
| Art. 25 (Privacy by Design) | Partial | Strong compliance |
| Third-party processor needed | YES (if cloud inference) | NO (browser is not a processor) |
| DPA (Data Processing Agreement) | Required with cloud vendor | Not required for browser execution |
| DPIA (Art. 35) likelihood | Higher | Lower (reduced risk profile) |
| Model file as "personal data" | If model trained on personal data, possibly | Same question applies |

**Key insight: UNIQA is still the data controller for client-side inference**

The fact that inference runs in the user's browser doesn't change UNIQA's controller status. UNIQA:
- Wrote the JavaScript that runs the inference
- Trained the model (on UNIQA's data)
- Determines the purposes (conversion optimization)
- Receives the commercial benefit

**What actually changes:**
1. No need for a DPA with a cloud inference vendor (Anthropic, AWS, etc.)
2. Reduced DPIA requirements — risk profile is lower
3. Stronger Art. 25 compliance argument
4. If inference results (persona classification, p_abandon) are NOT transmitted to server → no personal data is processed server-side during the Coach's operation → huge privacy win

**Recommended architecture:**
```javascript
// All inference happens in browser
const session = await InferenceSession.create('/models/coach_v1.onnx');
const behavioralFeatures = extractFeatures(windowEvents); // local only
const output = await session.run({input: behavioralFeatures}); // local only
const personaClass = argmax(output.logits); // local only
const intervention = selectIntervention(personaClass, currentStep); // local only
showWidget(intervention); // local DOM manipulation

// Only this goes to server (or not even this, if purely frontend):
// - The final quote request when user completes purchase
// - Optional: anonymized/aggregated analytics (no individual persona data)
```

**ONNX model itself — does it contain personal data?**

If the model was trained on UNIQA's real customer data (clickstream, purchase history), then the trained model weights may be a "derived" form of personal data. Under GDPR, this is contested — most data protection authorities have not issued clear guidance. Practical mitigation:
- Train on synthetic data (as planned in the UNIQA_ANALYSIS.md) → no personal data in model weights
- If trained on real data: k-anonymity + differential privacy during training
- Document training data in model card

### 4.2 Privacy by Design Implementation (Art. 25)

For the ONNX/WASM approach to fully satisfy Art. 25:

```
Requirement                     Implementation
──────────────────────────────  ──────────────────────────────────────
Data minimization               Only behavioral features (no PII) as model input
Purpose limitation              Model outputs used only for Coach decisions, not stored
Storage limitation              sessionStorage only; auto-clear on tab close
Integrity + confidentiality     ONNX file served over HTTPS; no model tampering
Default privacy                 Coach disabled by default; activated only after consent
```

---

## PART 5: AUSTRIAN SPECIFICS

### 5.1 DSG (Datenschutzgesetz 2018)

Austria's DSG implements GDPR with minor national additions:

**Relevant provisions for the Coach:**

| DSG Section | Content | Impact on Coach |
|-------------|---------|-----------------|
| §1 DSG | Constitutional fundamental right to data protection | Higher bar for overriding privacy in LIA assessments |
| §4 DSG | Consent requirements (ages of consent) | Minor persons → no online insurance application |
| §24 DSG | Right to complain to DSB | Must have clear DSB complaint channel in privacy notice |
| §1 Abs. 2 DSG | State interference in data rights requires proportionality | Relevant if government audits UNIQA's AI |

**DSB (Datenschutzbehörde) precedent:**
- The DSB ruled in 2022 that Google Analytics 4's data transfers were unlawful (following Schrems II)
- The DSB has been active on Art. 22 cases involving credit scoring and insurance
- Any automated profiling in insurance should be notifiable to DSB if it involves special categories of data (health data from Step 6)

> **Critical**: Step 6 health question answers are **special category data under GDPR Art. 9**. If the Coach receives ANY health question data as features, it processes special category data, requiring EXPLICIT consent under Art. 9(2)(a) — not just regular consent.

**Architecture guard**: Coach MUST NOT receive Step 6 (health questions) data. This is both an Art. 9 compliance measure AND the measure that keeps the system out of Annex III high-risk territory.

---

### 5.2 VAG (Versicherungsaufsichtsgesetz 2016) and IDD Compliance

The Insurance Distribution Directive (IDD, Directive 2016/97/EU) was implemented in Austria through the VAG 2016 amendments and the Gewerbeordnung for brokers.

**Relevant VAG provisions for the digital Coach:**

| VAG/IDD Reference | Requirement | Coach Implication |
|-------------------|-------------|-------------------|
| VAG §131 + IDD Art. 17 | Act in customer's best interest | Coach must not steer toward Optimal if Start meets user's needs |
| VAG §132 + IDD Art. 20 | Demands and needs analysis before sale | The "persona" approach should document how it assesses user needs |
| VAG §133 + IDD Art. 20(3) | Provide standardized IPID before purchase | IPID must be accessible at Step 4; Coach can link to it |
| IDD Art. 24 | Cross-selling: ancillary products must be available separately | Add-ons (Fit Feeling etc.) must be clearly separable |
| IDD Art. 20(4) | Online sales: standardized info must cover customer's needs | The Coach's tariff recommendation must be traceable to expressed needs |

**FMA regulatory expectations:**

The Austrian FMA has issued:
- **FMA Aufsichtsmitteilung 2021**: Guidance on digital insurance distribution under IDD
- **FMA Rundschreiben on algorithmic systems**: Following EIOPA guidance
- FMA enforces the principle that **any recommendation of a specific product requires documented suitability justification**

**For the Coach's tariff recommendation (Start vs. Optimal):**

Under IDD, if the Coach recommends Optimal over Start, this constitutes a "product recommendation" and triggers the demands-and-needs analysis. Required documentation:
```
When Coach recommends Optimal:
- Record: what user needs were identified (e.g., no physiotherapy coverage in Start)
- Record: why Optimal meets those needs better than Start
- This can be simplified to: "User has [X] characteristic → Optimal covers [Y] which Start does not"
- The 3-year upgrade path must be disclosed at this point
```

This means the Coach's recommendation logic must be **auditable and need-justified**, not just "Optimal converts better." The actual conversion optimization goal must be wrapped in a needs-justification framework.

---

### 5.3 EIOPA Guidance on AI in Insurance

EIOPA (European Insurance and Occupational Pensions Authority) has issued key guidance relevant to the Coach:

**EIOPA Supervisory Statement on Big Data Analytics in Motor and Health Insurance (2019, updated 2021):**

Key principles applicable to the Coach:
1. **Governance**: AI systems in insurance must have clear accountability chains (who is responsible for Coach outputs?)
2. **Fairness and Non-Discrimination**: AI must not use proxies for protected characteristics (age, gender, health status) in pricing or sales
3. **Explainability**: Insurers must be able to explain AI-driven decisions to supervisors and customers
4. **Accuracy and Reliability**: Model performance must be monitored and documented

**EIOPA's red lines for insurance AI:**
- AI cannot use data that creates discriminatory outcomes based on protected characteristics (Art. 21 EU Charter)
- Behavioral profiling for insurance sales must not use proxies that correlate with health status, disability, or ethnicity
- Loss of explainability = supervisory concern

**Specific risk for the Coach:**
The persona classification could inadvertently correlate with protected characteristics:
- "Service Affine" (Peter, 43% hospitalization rate) → profiling people with higher health needs as requiring advisor routing could be disability discrimination if the routing is less favorable
- Mitigation: ensure advisor routing is presented as equivalent-quality service, not lesser service

---

## PART 6: RIGHT TO EXPLANATION

### 6.1 Sources of the Explanation Right

| Legal Source | Scope | Strength |
|-------------|-------|----------|
| GDPR Art. 22(3) | Right to meaningful information about logic in automated decisions | Binding; but only "meaningful information about the logic" — not full explanation |
| GDPR Art. 13(2)(f) + Art. 14(2)(g) | "Meaningful information about the logic" in privacy notice | Binding; in privacy notice |
| EU AI Act Art. 50 | Inform users when interacting with AI in real-time | Binding from Aug 2025 |
| EU AI Act Art. 86 (Recital discussion) | Right to explanation for affected persons from high-risk systems | Applies only if high-risk classified |
| GDPR Recital 71 | Right to explanation is an "at minimum" expectation for Art. 22 | Soft guidance |

### 6.2 What Must Be Disclosed in Insurance AI Context

**In the privacy notice (Art. 13 GDPR):**
```
"UNIQA uses an automated system to personalize your experience in our health 
insurance calculator. This system analyzes your interaction patterns (such as 
time spent on pages, navigation choices, and scroll behavior) to provide 
relevant information at the right moment. It does not analyze your health 
information, financial situation, or personal circumstances.

The system classifies your behavior into general categories to predict whether 
you might benefit from additional information (e.g., price breakdowns, coverage 
comparisons). No legally binding decisions about your insurance application are 
made by this system.

You can opt out of this personalization at any time by [clicking here/turning 
off personalization in settings]. This will not affect your ability to purchase 
insurance."
```

**In the UI when the Coach is active:**
- Small disclosure notice: *"ⓘ Personalized suggestion powered by AI — based on your current session behavior"*
- No personal name required in the disclosure
- Link to privacy notice

**On request (Art. 22(3) if applicable):**
- User can request: "What behavioral data was used for this suggestion?"
- Response must cover: which signals triggered the intervention, what category was assigned
- Does NOT need to reveal full model architecture or weights

---

## PART 7: PRACTICAL COMPLIANCE CHECKLIST

### 7.1 Form Progress Persistence

```
✅ REQUIRED (legal minimum):
□ Obtain explicit consent before writing personal data to localStorage
  - Consent UI: modal/banner before first auto-save
  - Consent text: "Save your progress for 30 days? We'll store your partial application locally."
  - Consent = affirmative action (not pre-checked box)
  
□ Behavioral signals in sessionStorage ONLY (auto-cleared on tab close)
  - Never persist persona classification or p_abandon scores
  - Never transmit behavioral signals to server during Coach operation
  
□ Auto-TTL enforcement in client code
  - Check TTL on page load: if expired, delete and don't restore
  - Show user: "Your saved progress expired. Start fresh."
  
□ User-initiated deletion
  - "Clear my saved progress" button on the form page
  - Must delete ALL related localStorage keys

✅ REQUIRED (Art. 13 GDPR notice):
□ Privacy notice updated to mention form progress persistence
□ Retention period (30 days) explicitly stated
□ User right to delete explicitly mentioned

⭐ BEST PRACTICE (beyond legal minimum):
□ Progress persistence opt-in is off by default
□ Offer shorter retention options (7 days, session only)
□ Display remaining TTL: "Your progress saved for X more days"
□ Quote ID for server-side persistence (user can request deletion by quote ID)
```

### 7.2 Local Model Approach (On-Device Inference)

```
✅ REQUIRED:
□ ONNX model served over HTTPS (integrity + confidentiality)
□ Model NOT trained on special category data (health, medical records)
□ Privacy notice mentions AI personalization (even if client-side)
□ No individual inference results transmitted to server
□ Art. 50 disclosure: user informed AI is active

✅ REQUIRED for training data:
□ If trained on real UNIQA clickstream data → privacy notice must cover this use
□ Preferred: train on synthetic data only → cleaner consent story
□ Model card documenting: training data source, known biases, performance metrics

⭐ BEST PRACTICE:
□ Model weights available for audit by regulators (not publicly, but on request)
□ Version-control the ONNX model with release notes
□ Serve ONNX model with SRI (Subresource Integrity) hash
□ Differential privacy during training if real user data is used
□ Periodic bias audit: test model performance across age groups, genders
```

### 7.3 Disclosure Requirements (UI When AI Coaching Is Active)

```
✅ REQUIRED (Art. 50 EU AI Act — in force now):
□ Visible indicator that AI personalization is active
□ Minimum: small text + icon "AI-powered suggestions"
□ Must be in primary language of the interface (German for UNIQA.at)
□ Must appear BEFORE the first intervention (not after)

✅ REQUIRED (GDPR Art. 13):
□ Privacy notice linked from the AI disclosure indicator
□ Privacy notice explains behavioral profiling
□ Opt-out accessible from disclosure UI

Sample UI implementation:
┌─────────────────────────────────────────────────────┐
│  🤖 Personalisierte Hinweise  ⓘ Datenschutz   [✕]  │
│     Basierend auf Ihrem Verhalten in dieser Sitzung  │
└─────────────────────────────────────────────────────┘

The [✕] dismisses and opts out. The ⓘ opens privacy info.

✅ IDD Requirement (for tariff recommendations):
□ When Coach recommends Optimal over Start:
  - Show why: "Based on your profile, Optimal covers [specific need] that Start does not"
  - Show that Start is still available
  - Link to IPID for both tariffs
  - State that recommendation is automated

⚠️ What NOT to do:
□ Don't hide that AI is making the recommendation
□ Don't imply the recommendation is from a human advisor
□ Don't make advisor routing feel like a punishment or restriction
□ Don't use health data as Coach input signals
```

### 7.4 Consent Flow Design

```
FUNNEL ENTRY
│
├── Standard cookie consent (existing UNIQA requirement)
│   └── Strictly necessary cookies: granted without consent
│
└── Coach personalization consent (NEW — add to consent flow)
    │
    ├── Trigger: Before first behavioral data collection
    │   (i.e., at page load or first interaction)
    │
    ├── UI: Non-blocking banner (not modal — don't block funnel)
    │   "Darf UNIQA Ihr Verhalten in dieser Sitzung analysieren,
    │    um personalisierte Tipps anzuzeigen? [Ja] [Nein]"
    │
    ├── If YES:
    │   ├── Start behavioral tracking (sessionStorage)
    │   ├── Enable Coach interventions
    │   ├── Show AI disclosure banner when first intervention fires
    │   └── Offer "Save my progress" (30 days, separate consent)
    │
    └── If NO:
        ├── Standard funnel without Coach (no behavioral tracking)
        ├── No sessionStorage behavioral data written
        └── Basic form functionality still available

SAVE PROGRESS CONSENT (separate, user-initiated)
│
├── Trigger: User clicks "Fortschritt speichern" button
│
└── Consent dialog:
    "Ihre bisherigen Angaben werden für 30 Tage lokal auf Ihrem
     Gerät gespeichert, damit Sie später weitermachen können.
     Diese Daten verlassen Ihr Gerät nicht.
     [Speichern] [Nein danke]"

DATA DELETION FLOW
│
├── In-funnel: "Gespeicherte Daten löschen" button on form
├── Privacy notice: Link to data deletion request
└── On TTL expiry: Auto-delete + inform user on next visit
```

---

## PART 8: ARCHITECTURE RECOMMENDATIONS SUMMARY

### 8.1 Recommended Technical Architecture (Privacy-Compliant)

```
BROWSER                                    UNIQA SERVER
┌───────────────────────────────────┐      ┌──────────────────────┐
│                                   │      │                      │
│  sessionStorage (cleared on close)│      │  Insurance platform  │
│  ├── behavioral_events (no PII)   │      │  ├── Health Q engine │
│  ├── session_uuid (random)        │      │  ├── Pricing engine  │
│  └── consent_state                │      │  └── Quote storage   │
│                                   │      │                      │
│  localStorage (consent required)  │      │  Analytics (aggregate│
│  └── partial_quote (30-day TTL)   │      │  only, no persona)   │
│                                   │      │                      │
│  ONNX Runtime (wasm)              │      │  Audit log           │
│  ├── Input: behavioral features   │      │  ├── Coach version   │
│  ├── Inference: local only        │      │  ├── Intervention    │
│  └── Output: used only for UI     │      │  │   types shown     │
│                                   │      │  └── Outcomes (agg.) │
│  Coach logic (JS)                 │      │                      │
│  ├── Disclosure UI                │──────▶  Quote request       │
│  ├── Intervention selection       │      │  (personal data)     │
│  └── Widget renderer              │      │                      │
└───────────────────────────────────┘      └──────────────────────┘

WHAT CROSSES THE WIRE:
→ Only: quote form data (when user submits), not behavioral signals
← Only: ONNX model file (static asset), funnel HTML/JS, product prices
```

### 8.2 Legal Basis Summary

| Processing Activity | Legal Basis | Notes |
|--------------------|-------------|-------|
| Behavioral tracking (sessionStorage) | **Legitimate interests** (Art. 6(1)(f)) | Must pass LIA; sessionStorage self-clears |
| AI persona classification | **Consent** (Art. 6(1)(a)) | Cleaner than LI; ask at funnel entry |
| Form progress persistence (localStorage) | **Consent** (Art. 6(1)(a)) | ePrivacy consent required |
| Quote completion (personal data) | **Contract performance** (Art. 6(1)(b)) | Pre-contractual steps |
| Audit logging | **Legitimate interests** (Art. 6(1)(f)) | Regulatory compliance purpose |
| Health Q answers (Step 6) | **Explicit consent** (Art. 9(2)(a)) | Special category data — NEVER in Coach |

---

## PART 9: GAPS AND UNCERTAINTY FLAGS

### 9.1 Areas of Genuine Legal Uncertainty

1. **Art. 22 threshold for routing decisions**: There is no Austrian or EU case law specifically on conversion funnel advisor routing as Art. 22. The EDPB's broad interpretation suggests it applies; the narrow textual reading suggests it doesn't. **Recommended**: treat as Art. 22 applies; design accordingly.

2. **IDD "needs analysis" digitization**: How formal does the automated needs analysis need to be for a €38-68/month online tariff? FMA has not issued specific guidance on AI-driven needs analysis. **Recommended**: document the Coach's decision logic with explicit needs-mapping; keep it reviewable by FMA.

3. **EU AI Act Art. 6(3) self-assessment threshold**: The rule for when you can self-exempt from high-risk classification is vague. The European Commission hasn't yet published detailed guidance. **Recommended**: make the architectural decision (no health data in Coach) and document it explicitly; register in EU AI Act database when that goes live (Aug 2026).

4. **ePrivacy Directive reform**: The ePrivacy Regulation was supposed to replace the Directive but is still blocked. Austria's TKG 2021 applies current Directive rules. The "strictly necessary" exemption for localStorage auto-save is untested by Austrian courts. **Recommended**: get explicit consent; don't rely on "strictly necessary."

5. **Model weights as personal data**: No definitive EDPB guidance. **Recommended**: train on synthetic data to eliminate this uncertainty entirely.

### 9.2 What This Research Cannot Confirm

- **FMA-specific guidance on conversion AI**: No published FMA guidance specific to AI conversion tools in insurance funnels found. The VAG + IDD framework applies by analogy.
- **DSB enforcement priorities**: The Austrian DSB's specific focus on insurance AI is not documented in public sources. The Schrems II enforcement against Google Analytics gives some signal about DSB's willingness to act.
- **Exact Art. 50 UI requirements**: The EU AI Act implementing acts (delegated acts) covering exact UI disclosure formats are not yet published. The text says "clear and distinguishable manner" — design for visibility.

---

## APPENDIX A: LEGAL CITATIONS QUICK REFERENCE

| Reference | Full Name | URL |
|-----------|-----------|-----|
| EU AI Act | Regulation (EU) 2024/1689 | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689 |
| GDPR | Regulation (EU) 2016/679 | https://eur-lex.europa.eu/eli/reg/2016/679/oj |
| IDD | Directive (EU) 2016/97 | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32016L0097 |
| ePrivacy Dir. | Directive 2009/136/EC | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0136 |
| Austrian TKG 2021 | Telekommunikationsgesetz 2021 | https://www.ris.bka.gv.at/ |
| Austrian DSG | Datenschutzgesetz 2018 | https://www.ris.bka.gv.at/ |
| Austrian VAG | Versicherungsaufsichtsgesetz 2016 | https://www.ris.bka.gv.at/ |
| EIOPA BigData | EIOPA-BoS-18/026 (2019) | https://www.eiopa.europa.eu/ |
| EDPB Art 22 | Opinion 3/2019 | https://edpb.europa.eu/ |

---

## APPENDIX B: HACKATHON-SPECIFIC IMPLEMENTATION PRIORITIES

Given the Sunday 10:00 deadline, here's the minimum viable compliance implementation:

```
MUST HAVE (for defensible demo):
✅ Art. 50 disclosure: "AI-powered personalization" notice in UI
✅ Consent banner before behavioral tracking starts
✅ sessionStorage for behavioral signals (not localStorage)
✅ No health question data in Coach features
✅ Explicit "I'm Franz so never show advisor" guard in code (documents safe design intent)
✅ Privacy notice stub covering: profiling, AI use, data rights

SHOULD HAVE (for complete demo):
☐ localStorage with TTL for form progress (with consent dialog)
☐ Opt-out mechanism (button that clears consent + disables Coach)
☐ IPID links at tariff recommendation step
☐ Needs-justification log when recommending Optimal

NICE TO HAVE (for legal thoroughness, less demo-critical):
☐ DPIA document (Data Protection Impact Assessment)
☐ EU AI Act Art. 6(3) self-assessment document
☐ LIA (Legitimate Interest Assessment) for session analytics
☐ Bias audit across age/gender groups

REPORT.MD COMPLIANCE SECTION SHOULD INCLUDE:
- "The Coach does not process health questionnaire data"
- "Classification uses UX behavioral signals only (session-scoped)"
- "The system is designed for Art. 6(3) non-high-risk self-assessment"
- "Art. 50 transparency disclosure implemented in UI"
- "GDPR Art. 22 risk addressed through: routing as recommendation only, no path blocking"
```

---

*Research compiled by: zero-one.researcher agent | Based on: EU AI Act 2024/1689, GDPR 2016/679, IDD 2016/97, Austrian DSG 2018, Austrian TKG 2021, Austrian VAG 2016, EIOPA guidance EIOPA-BoS-18/026, EDPB Opinion 3/2019 on Art. 22, EDPB Guidelines 8/2020 on targeting social media users | Date: 2026-05-30*
