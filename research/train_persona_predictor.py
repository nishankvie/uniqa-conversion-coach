"""
Train + persist the persona predictor (the empirical realization of PIPELINE_PLAN
§7 `p_identify`). Saves two models:
  - state_model    : full generated state (state vars + delta + decision + feeling)
  - actions_model  : observable activity log ONLY (event families + timing + decision)

Artifacts -> models/persona_predictor/
  {state,actions}_model.joblib  + meta.json (CV metrics, feature names, step curves)

The actions_model is the one the Coach can actually run in prod (it sees only the
activity log). Reuses feature logic from the two probe scripts.
"""
import json, collections, numpy as np, joblib, pathlib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

PATH = "datasets/persona_v2/sft_steps.jsonl"
OUT = pathlib.Path("models/persona_predictor"); OUT.mkdir(parents=True, exist_ok=True)
STEP_ORDER = ["S1_COVERAGE_TYPE","S2_INSURED_PERSONS","S3_PERSONAL_INFO","S4_TARIFF_SELECT","S6_PERSONAL_DATA"]
PERSONAS = ["judith","franz","peter"]
STATE_KEYS = ["attention","satisfaction","effort_left","grasp","effort_vs_reward"]
FEELINGS = ["engaged","too_much_effort","dissatisfied","unanswered_question","coverage_mismatch","goal_achieved","cant_grasp","distracted"]
FAMILIES = ["select","edit","field_focus","field_blur","hover","dropdown","nav_next","nav_back","submit","idle","tab","tariff_click","abandon","other"]

def bucket(t):
    t=(t or "").lower()
    if any(k in t for k in("hover","mouseover","mouseenter","tooltip")) or ("price" in t and "reveal" in t):return "hover"
    if t in ("select","select_card","select_tariff","select_option","selection","selected"):return "select"
    if "tariff" in t or "premium" in t or("price" in t and "click" in t):return "tariff_click"
    if "field_focus" in t or t=="focus":return "field_focus"
    if "field_blur" in t:return "field_blur"
    if any(k in t for k in("field_edit","field_fill","type","keystroke","input","filter_type","typing","typed")):return "edit"
    if "dropdown" in t or "drop_down" in t:return "dropdown"
    if "nav_next" in t or t=="navigation":return "nav_next"
    if "nav_back" in t:return "nav_back"
    if "submit" in t:return "submit"
    if "pause" in t or "idle" in t:return "idle"
    if "tab_" in t:return "tab"
    if "abandon" in t or "abort" in t:return "abandon"
    return "other"

state_rows, action_rows, ys, stp = [], [], [], []
for line in open(PATH):
    r=json.loads(line)
    try:o=json.loads(r["output"])
    except Exception:continue
    st=o.get("state",{})
    try:out_state=[float(st[k]) for k in STATE_KEYS]
    except Exception:continue
    d=json.loads(r["input_messages"][-1]["content"]); rs=d.get("your_running_state",{})
    in_state=[float(rs.get(k,np.nan)) for k in STATE_KEYS]
    delta=[a-b for a,b in zip(out_state,in_state)]
    dec=1.0 if o.get("decision")=="leave" else 0.0
    feel=o.get("feeling"); fv=[1.0 if feel==f else 0.0 for f in FEELINGS]
    evs=[e for e in o.get("events",[]) if isinstance(e,dict)]
    fam=collections.Counter(bucket(e.get("type")) for e in evs)
    famvec=[float(fam.get(f,0)) for f in FAMILIES]
    ts=[e.get("t") for e in evs if isinstance(e.get("t"),(int,float))]
    dwell=float(max(ts)) if ts else 0.0
    inter=float(np.mean(np.diff(sorted(ts)))) if len(ts)>=2 else 0.0
    ntg=float(len({e.get("target") for e in evs if e.get("target") is not None}))
    state_rows.append(out_state+delta+[dec,float(len(evs))]+fv)
    action_rows.append(famvec+[float(len(evs)),dwell,ntg,inter,dec])
    ys.append(PERSONAS.index(r["persona"])); stp.append(r["step"])

y=np.array(ys); steps=np.array(stp)
state_names=["out_"+k for k in STATE_KEYS]+["d_"+k for k in STATE_KEYS]+["decision_leave","n_events"]+["feel_"+f for f in FEELINGS]
action_names=FAMILIES+["n_events","dwell","n_targets","inter_event_dt","decision_leave"]

def build(rows,names,tag):
    X=np.nan_to_num(np.array(rows,dtype=float))
    pipe=make_pipeline(StandardScaler(),RandomForestClassifier(n_estimators=400,random_state=0,n_jobs=-1))
    skf=StratifiedKFold(5,shuffle=True,random_state=0)
    proba=cross_val_predict(pipe,X,y,cv=skf,method="predict_proba",n_jobs=-1)
    pred=proba.argmax(1)
    per_step={s:float((pred[steps==s]==y[steps==s]).mean()) for s in STEP_ORDER}
    pipe.fit(X,y)  # final model on all data
    joblib.dump({"pipeline":pipe,"feature_names":names,"personas":PERSONAS,
                 "step_order":STEP_ORDER},OUT/f"{tag}_model.joblib")
    return {"cv_accuracy":float((pred==y).mean()),"cv_mean_conf":float(proba.max(1).mean()),
            "per_step_acc":per_step,"n_features":X.shape[1],"feature_names":names}

meta={"dataset":PATH,"n_rows":len(y),"chance":1/3,
      "state_model":build(state_rows,state_names,"state"),
      "actions_model":build(action_rows,action_names,"actions")}
json.dump(meta,open(OUT/"meta.json","w"),indent=2)
print(f"saved -> {OUT}/")
print(f"  state_model   CV acc {meta['state_model']['cv_accuracy']:.3f}")
print(f"  actions_model CV acc {meta['actions_model']['cv_accuracy']:.3f}")
print("  files:", [p.name for p in sorted(OUT.iterdir())])
