"""
Investigation: can we classify persona (judith/franz/peter) from its GENERATED
state-step records, and at which funnel stage does classification confidence
become 'good enough'?

Uses ONLY generated outputs (no persona prompt leakage):
  - output state vars: attention, satisfaction, effort_left, grasp, effort_vs_reward
  - delta from incoming running_state -> output state
  - decision (continue/leave)
  - feeling (categorical)
  - n_events, leave_rate

Two views:
  A) Per-step classifier (independent samples). Accuracy + mean top-class
     confidence broken down by funnel step S1..S6.
  B) Cumulative trajectory: simulate "if we'd seen state for steps S1..Sk for one
     persona instance, how confident", by averaging per-step posteriors up to k.
"""
import json, collections, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

PATH = "datasets/persona_v2/sft_steps.jsonl"
STATE_KEYS = ["attention", "satisfaction", "effort_left", "grasp", "effort_vs_reward"]
FEELINGS = ["engaged","too_much_effort","dissatisfied","unanswered_question",
            "coverage_mismatch","goal_achieved","cant_grasp","distracted"]
STEP_ORDER = ["S1_COVERAGE_TYPE","S2_INSURED_PERSONS","S3_PERSONAL_INFO",
              "S4_TARIFF_SELECT","S6_PERSONAL_DATA"]
PERSONAS = ["judith","franz","peter"]

def get_in_state(inp_user):
    d = json.loads(inp_user)
    rs = d.get("your_running_state", {})
    return [float(rs.get(k, np.nan)) for k in STATE_KEYS]

rows = []
for line in open(PATH):
    r = json.loads(line)
    try:
        o = json.loads(r["output"])
    except Exception:
        continue
    st = o.get("state", {})
    out_state = []
    ok = True
    for k in STATE_KEYS:
        try: out_state.append(float(st[k]))
        except Exception: ok = False; break
    if not ok: continue
    user_msg = r["input_messages"][-1]["content"]
    in_state = get_in_state(user_msg)
    decision = 1.0 if o.get("decision") == "leave" else 0.0
    feeling = o.get("feeling")
    feel_vec = [1.0 if feeling == f else 0.0 for f in FEELINGS]
    delta = [a - b for a, b in zip(out_state, in_state)]
    n_events = float(len(o.get("events", [])))
    feats = out_state + delta + [decision, n_events, float(r.get("leave_rate", 0.0))] + feel_vec
    rows.append({
        "persona": r["persona"],
        "step": r["step"],
        "X": feats,
    })

X = np.array([r["X"] for r in rows], dtype=float)
X = np.nan_to_num(X, nan=0.0)
y = np.array([PERSONAS.index(r["persona"]) for r in rows])
steps = np.array([r["step"] for r in rows])
print(f"loaded {len(rows)} step-records, {X.shape[1]} features")

feat_names = (["out_"+k for k in STATE_KEYS] + ["d_"+k for k in STATE_KEYS]
              + ["decision_leave","n_events","leave_rate"] + ["feel_"+f for f in FEELINGS])

clf = make_pipeline(StandardScaler(),
                    RandomForestClassifier(n_estimators=400, random_state=0, n_jobs=-1))

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
proba = cross_val_predict(clf, X, y, cv=skf, method="predict_proba", n_jobs=-1)
pred = proba.argmax(1)
acc = (pred == y).mean()
print(f"\n=== OVERALL (5-fold CV, RF) ===")
print(f"accuracy = {acc:.3f}  (chance = 0.333)")

# top-class confidence
topconf = proba.max(1)
print(f"mean top-class confidence = {topconf.mean():.3f}")

print("\n=== PER-STEP breakdown ===")
print(f"{'step':22s} {'n':>5s} {'acc':>6s} {'conf':>6s}  per-persona-recall")
step_acc = {}
for s in STEP_ORDER:
    m = steps == s
    if m.sum() == 0: continue
    a = (pred[m] == y[m]).mean()
    c = topconf[m].mean()
    rec = []
    for pi, pn in enumerate(PERSONAS):
        mm = m & (y == pi)
        rec.append(f"{pn[0].upper()}={(pred[mm]==y[mm]).mean():.2f}")
    step_acc[s] = a
    print(f"{s:22s} {m.sum():5d} {a:6.3f} {c:6.3f}  {' '.join(rec)}")

print("\n=== CONFUSION (overall, rows=true persona) ===")
cm = collections.Counter()
for t, p in zip(y, pred): cm[(PERSONAS[t], PERSONAS[p])] += 1
print(f"{'true\\pred':10s}" + "".join(f"{p:>9s}" for p in PERSONAS))
for t in PERSONAS:
    print(f"{t:10s}" + "".join(f"{cm[(t,p)]:9d}" for p in PERSONAS))

# Feature importance from a single fit
clf.fit(X, y)
imp = clf.named_steps["randomforestclassifier"].feature_importances_
order = np.argsort(imp)[::-1]
print("\n=== TOP 12 FEATURES ===")
for i in order[:12]:
    print(f"  {feat_names[i]:24s} {imp[i]:.3f}")

# === B) Cumulative confidence: average posterior over steps S1..Sk ===
# Simulate per-persona: how does confidence in TRUE persona grow as we accumulate
# evidence from more steps. (mean over samples of that persona at each step)
print("\n=== CUMULATIVE confidence in TRUE persona (avg posterior, steps S1..Sk) ===")
print(f"{'thru step':22s} " + " ".join(f"{p:>8s}" for p in PERSONAS) + f"{'  mean':>8s}")
for ki in range(len(STEP_ORDER)):
    upto = set(STEP_ORDER[:ki+1])
    line = f"{STEP_ORDER[ki]:22s} "
    means = []
    for pi, pn in enumerate(PERSONAS):
        m = np.isin(steps, list(upto)) & (y == pi)
        # posterior assigned to the TRUE persona for those samples
        v = proba[m, pi].mean()
        means.append(v)
        line += f"{v:8.3f} "
    line += f"{np.mean(means):8.3f}"
    print(line)

print("\nNote: per-step samples are independent (state-covering), so 'thru Sk' = pooled")
print("evidence quality available by that stage, not a single live trajectory.")

# === C) Sequential accumulation: simulate watching ONE persona across S1..Sk ===
# Per-step samples are independent, so a live trajectory's evidence = product of
# per-step posteriors. Monte-Carlo: draw one sample per step from the same persona,
# accumulate log-posteriors, measure P(true) and accuracy after k steps.
rng = np.random.default_rng(0)
# index pools by (persona, step) using out-of-fold posteriors (no leakage)
pool = {(pi, s): np.where((y == pi) & (steps == s))[0] for pi in range(3) for s in STEP_ORDER}
log_prior = np.log(np.ones(3) / 3)
N_TRAJ = 4000
acc_at_k = np.zeros(len(STEP_ORDER))
conf_at_k = np.zeros(len(STEP_ORDER))
for _ in range(N_TRAJ):
    true = rng.integers(3)
    logp = log_prior.copy()
    for ki, s in enumerate(STEP_ORDER):
        idxs = pool[(true, s)]
        j = idxs[rng.integers(len(idxs))]
        p = np.clip(proba[j], 1e-6, 1.0)
        logp = logp + np.log(p)          # accumulate evidence
        post = np.exp(logp - logp.max()); post /= post.sum()
        acc_at_k[ki] += (post.argmax() == true)
        conf_at_k[ki] += post[true]
acc_at_k /= N_TRAJ; conf_at_k /= N_TRAJ
print("\n=== SEQUENTIAL (accumulate evidence over a live trajectory) ===")
print(f"{'after step':22s} {'cum_acc':>8s} {'cum_conf(true)':>15s}")
for ki, s in enumerate(STEP_ORDER):
    flag = "  <-- >=90% conf" if conf_at_k[ki] >= 0.90 else ("  <-- >=80%" if conf_at_k[ki] >= 0.80 else "")
    print(f"thru {s:17s} {acc_at_k[ki]:8.3f} {conf_at_k[ki]:15.3f}{flag}")
