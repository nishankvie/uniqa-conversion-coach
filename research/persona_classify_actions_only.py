"""
Investigation 2: classify persona from GENERATED ACTIONS ONLY.
No thoughts, no state variables, no feeling, no leave_rate.
Observable = the activity log the Coach actually sees:
  - decision (continue/leave)
  - event stream: type, timing (t), n_events, distinct targets
Event types are bucketed into canonical families (data is noisy).
"""
import json, collections, numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

PATH = "datasets/persona_v2/sft_steps.jsonl"
STEP_ORDER = ["S1_COVERAGE_TYPE","S2_INSURED_PERSONS","S3_PERSONAL_INFO",
              "S4_TARIFF_SELECT","S6_PERSONAL_DATA"]
PERSONAS = ["judith","franz","peter"]

# bucket noisy event types into observable action families
def bucket(t):
    t = (t or "").lower()
    if "hover" in t or "mouseover" in t or "mouseenter" in t or "tooltip" in t: return "hover"
    if "price" in t and ("reveal" in t or "hover" in t): return "hover"
    if t in ("select","select_card","select_tariff","select_option","selection","selected","select_tariff"): return "select"
    if "tariff" in t or "premium" in t or ("price" in t and "click" in t): return "tariff_click"
    if "field_focus" in t or t == "focus": return "field_focus"
    if "field_blur" in t: return "field_blur"
    if "field_edit" in t or "field_fill" in t or "type" in t or "keystroke" in t or "input" in t or "filter_type" in t or "typing" in t or "typed" in t: return "edit"
    if "dropdown" in t or "drop_down" in t: return "dropdown"
    if "nav_next" in t or t == "navigation": return "nav_next"
    if "nav_back" in t: return "nav_back"
    if "submit" in t: return "submit"
    if "pause" in t or "idle" in t: return "idle"
    if "tab_" in t: return "tab"
    if "abandon" in t or "abort" in t: return "abandon"
    return "other"

FAMILIES = ["select","edit","field_focus","field_blur","hover","dropdown",
            "nav_next","nav_back","submit","idle","tab","tariff_click","abandon","other"]

rows = []
for line in open(PATH):
    r = json.loads(line)
    try: o = json.loads(r["output"])
    except Exception: continue
    evs = o.get("events", [])
    if not isinstance(evs, list): continue
    evs = [e for e in evs if isinstance(e, dict)]
    fam = collections.Counter(bucket(e.get("type")) for e in evs)
    famvec = [float(fam.get(f, 0)) for f in FAMILIES]
    ts = [e.get("t") for e in evs if isinstance(e.get("t"), (int, float))]
    dwell = float(max(ts)) if ts else 0.0
    n_ev = float(len(evs))
    n_targets = float(len({e.get("target") for e in evs if e.get("target") is not None}))
    inter = float(np.mean(np.diff(sorted(ts)))) if len(ts) >= 2 else 0.0
    decision = 1.0 if o.get("decision") == "leave" else 0.0
    feats = famvec + [n_ev, dwell, n_targets, inter, decision]
    rows.append({"persona": r["persona"], "step": r["step"], "X": feats})

feat_names = FAMILIES + ["n_events","dwell","n_targets","inter_event_dt","decision_leave"]
X = np.nan_to_num(np.array([r["X"] for r in rows], dtype=float))
y = np.array([PERSONAS.index(r["persona"]) for r in rows])
steps = np.array([r["step"] for r in rows])
print(f"loaded {len(rows)} records, {X.shape[1]} ACTION-ONLY features")

clf = make_pipeline(StandardScaler(),
                    RandomForestClassifier(n_estimators=400, random_state=0, n_jobs=-1))
skf = StratifiedKFold(5, shuffle=True, random_state=0)
proba = cross_val_predict(clf, X, y, cv=skf, method="predict_proba", n_jobs=-1)
pred = proba.argmax(1)
print(f"\n=== OVERALL (actions only) ===")
print(f"accuracy = {(pred==y).mean():.3f}  (chance 0.333)   mean conf = {proba.max(1).mean():.3f}")

print("\n=== PER-STEP ===")
print(f"{'step':22s} {'n':>5s} {'acc':>6s}  per-persona-recall")
for s in STEP_ORDER:
    m = steps == s
    rec = " ".join(f"{p[0].upper()}={(pred[m&(y==i)]==y[m&(y==i)]).mean():.2f}"
                   for i,p in enumerate(PERSONAS))
    print(f"{s:22s} {m.sum():5d} {(pred[m]==y[m]).mean():6.3f}  {rec}")

print("\n=== CONFUSION ===")
cm = collections.Counter((PERSONAS[t],PERSONAS[p]) for t,p in zip(y,pred))
print(f"{'true/pred':10s}"+"".join(f"{p:>9s}" for p in PERSONAS))
for t in PERSONAS:
    print(f"{t:10s}"+"".join(f"{cm[(t,p)]:9d}" for p in PERSONAS))

clf.fit(X, y)
imp = clf.named_steps["randomforestclassifier"].feature_importances_
print("\n=== TOP 10 ACTION FEATURES ===")
for i in np.argsort(imp)[::-1][:10]:
    print(f"  {feat_names[i]:18s} {imp[i]:.3f}")

# sequential accumulation over a live trajectory
rng = np.random.default_rng(0)
pool = {(i,s): np.where((y==i)&(steps==s))[0] for i in range(3) for s in STEP_ORDER}
logpri = np.log(np.ones(3)/3); N=4000
acc_k=np.zeros(5); conf_k=np.zeros(5)
for _ in range(N):
    tr=rng.integers(3); lp=logpri.copy()
    for ki,s in enumerate(STEP_ORDER):
        idx=pool[(tr,s)]; j=idx[rng.integers(len(idx))]
        lp=lp+np.log(np.clip(proba[j],1e-6,1))
        po=np.exp(lp-lp.max()); po/=po.sum()
        acc_k[ki]+=po.argmax()==tr; conf_k[ki]+=po[tr]
acc_k/=N; conf_k/=N
print("\n=== SEQUENTIAL (accumulate actions over live trajectory) ===")
print(f"{'after step':22s} {'cum_acc':>8s} {'cum_conf':>9s}")
for ki,s in enumerate(STEP_ORDER):
    fl="  <-- >=80%" if conf_k[ki]>=0.80 else ""
    print(f"thru {s:17s} {acc_k[ki]:8.3f} {conf_k[ki]:9.3f}{fl}")
