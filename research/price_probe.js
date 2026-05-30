// Codified UNIQA pricing experiment — run repeatedly to re-verify the price model.
// The /products + /premiums endpoints are NOT captcha-gated (only /calculate is), so we
// sweep them directly with controlled inputs. Run via the live Chrome session:
//
//   CDP="$HOME/.pi/agent/skills/chrome-cdp/scripts/cdp.mjs"
//   T=$(node "$CDP" list | grep -i uniqa | awk '{print $1}')
//   node "$CDP" eval "$T" "$(cat research/price_probe.js)" > research/findings/pricing_dataset.json
//
// Requires a tab open on uniqa.at/rechner/krankenversicherung (same-origin creds).
// NOTE: cdp.mjs Runtime.evaluate TIMEOUT=15s caps ~13 fetches/eval. This combined script
// (~23 calls) can exceed it — run the age sweep and the factor block as two separate evals
// if it times out, or trim `ages`. Canonical result: research/findings/pricing_dataset.json.
// Findings (see pricing_recon.md): online premium = f(age, tariff) ONLY — SV, gender,
// health/BMI/smoker, addons have NO effect; no online price-jump after health questions.
(async () => {
  const BASE = "https://api.ovtapp.com/api/health-insurance-calculator-ms/v1";
  const H = { "content-type": "application/json" };
  const bd = (age) => (2026 - age) + "-06-15";
  const post = async (path, body) => {
    const r = await fetch(BASE + path, { method: "POST", credentials: "include", headers: H, body: JSON.stringify(body) });
    return { status: r.status, json: r.status === 200 ? await r.json() : await r.text() };
  };
  const products = (age, sv = "1") => post("/products", { productCategory: "PRIVATE_DOCTOR", birthDate: bd(age), insuranceProviderId: sv });
  const premiums = (b) => post("/premiums", Object.assign({ productCategory: "PRIVATE_DOCTOR", maxCoverageId: 12, selectedAddons: [] }, b));

  const ages = [18, 21, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75];
  // parallel fan-out (sequential is too slow for one CDP eval)
  const prodRes = await Promise.all(ages.map(a => products(a)));
  const curve = prodRes.map((d, i) => Array.isArray(d.json)
    ? Object.assign({ age: ages[i] }, Object.fromEntries(d.json.map(p => [p.productName.replace("Privatarzt ", ""), p.premium])))
    : { age: ages[i], err: d.status });
  // factor isolation: each should show NO effect
  const factor = {};
  const svs = ["1", "2", "3", "4", "6", "11"];
  const svRes = await Promise.all(svs.map(sv => products(45, sv)));
  factor.sv_age45_optimal = Object.fromEntries(svs.map((sv, i) => [sv, Array.isArray(svRes[i].json) ? svRes[i].json.find(p => /Optimal/.test(p.productName)).premium : svRes[i].status]));
  const [m, f] = await Promise.all([premiums({ birthDate: bd(30), insuranceProviderId: "1", gender: "male" }), premiums({ birthDate: bd(30), insuranceProviderId: "1", gender: "female" })]);
  factor.gender_age30_optimal = { male: m.json.totalMonthlyPremium, female: f.json.totalMonthlyPremium };
  const [cl, sk] = await Promise.all([
    premiums({ birthDate: bd(40), insuranceProviderId: "1" }),
    premiums({ birthDate: bd(40), insuranceProviderId: "1", heightCm: 180, weightKg: 120, smoker: true, healthQuestions: [{ id: 1, answer: true }] })]);
  factor.health_age40_optimal = { clean: cl.json.totalMonthlyPremium, with_obesity_smoker_condition: sk.json.totalMonthlyPremium, jump: +((sk.json.totalMonthlyPremium) - (cl.json.totalMonthlyPremium)).toFixed(2) };

  return JSON.stringify({ captured: new Date().toISOString(), curve_by_age: curve, factor_isolation: factor }, null, 1);
})()
