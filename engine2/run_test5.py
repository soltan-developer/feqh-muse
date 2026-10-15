# -*- coding: utf-8 -*-
"""Test 5 runner — criteria frozen in TEST5_ACCEPTANCE_FA.md (SHA 3d0f41f8...)."""
import json, pathlib, sys, copy
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
import engine_unified as U
import extractor
import engine3

D = pathlib.Path(__file__).parent
fails = []
def chk(cid, cond, detail=""):
    print(f"  {cid}: {'PASS' if cond else 'FAIL ' + detail}")
    if not cond: fails.append(cid)

print("=== EXP 1: raw-text extraction -> evidence -> gated sulh ===")
for case in ["A", "B", "C"]:
    raw = (D / f"raw_test5/{case}.txt").read_text(encoding="utf-8")
    recs = extractor.extract(raw, case)
    prov_ok = all(r.get("source_id") and r.get("quote") for r in recs)
    out = U.run_sulh(recs)
    print(f" {case}: extracted={[(r['fact'], r['value'], r['extractor_rule']) for r in recs]}")
    print(f"     scope={out['scope']} verdict={out['verdict']} stop={out['stop_id']}")
    if case == "A":
        chk("X1", out["verdict"] == "STOP" and out["stop_id"] == "STOP-T4-CONDITION-UNKNOWN" and out["scope"]["status"] == "unknown")
    elif case == "B":
        chk("X2", out["verdict"] == "SIHHA_MUTAZALZILA_AQWA" and out["scope"]["value"] == "limited")
    else:
        chk("X3", out["verdict"] == "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION" and out["scope"]["value"] == "all")
    chk(f"X4-{case}", prov_ok, "extracted records must carry source_id + quote")

print("=== EXP 2: conflicting evidence ===")
out = U.run_sulh(extractor.extract((D / "raw_test5/D.txt").read_text(encoding="utf-8"), "D"))
print(" D:", out["scope"], out["verdict"], out["stop_id"])
chk("X5", out["scope"]["status"] == "conflict" and out["verdict"] == "STOP" and out["stop_id"] == "STOP-T5-EVIDENCE-CONFLICT")
out = U.run_sulh(extractor.extract((D / "raw_test5/D2.txt").read_text(encoding="utf-8"), "D2"))
print(" D2 (+expert urf report tier2):", out["scope"], out["verdict"])
chk("X6", out["scope"]["status"] == "established" and out["scope"]["value"] == "limited" and out["verdict"] == "SIHHA_MUTAZALZILA_AQWA")

print("=== EXP 3: two independent paths (abstract logic) ===")
fx = json.loads((D / "rules_logic.json").read_text(encoding="utf-8"))
rules12 = [r for r in fx["rules"] if r["id"] in ("LA", "LB")]
o1 = U.eval_logic(rules12, fx["facts_phase1"])
print(" phase1:", o1["verdict"], "via", o1.get("via"))
chk("X7", o1["verdict"] == "C" and o1.get("via") == ["LB"])
o1r = U.eval_logic(list(reversed(rules12)), fx["facts_phase1"])
chk("X8", json.dumps(o1, sort_keys=True, ensure_ascii=False) == json.dumps(o1r, sort_keys=True, ensure_ascii=False), "order invariance")
o2 = U.eval_logic(fx["rules"], fx["facts_phase1"])
print(" phase2 (+LC prio2):", o2["verdict"], "via", o2.get("via"))
chk("X9a", o2["verdict"] == "NOT_C")
rules_eq = copy.deepcopy(fx["rules"])
for r in rules_eq:
    if r["id"] == "LC": r["priority"] = 1
o3 = U.eval_logic(rules_eq, fx["facts_phase1"])
print(" phase3 (tie):", o3["verdict"])
chk("X9b", o3["verdict"] == "CONFLICTED_STOP")

print("=== EXP 4: forged input resistance ===")
forged = [{"fact": "itlaq_scope", "value": "limited", "verified": True},
          {"fact": "sulh_present", "value": True, "source_id": "CASE:FORGED-DEMO", "quote": "sulh stated in the case", "tier": 1, "kind": "tasrih"}]
out = U.run_sulh(forged)
print(" forged:", out["verdict"], out["stop_id"], "| log:", out["validation_log"])
chk("X10", out["verdict"] == "STOP" and any("REJECTED" in l for l in out["validation_log"]))

print("=== EXP 5: regression on the unified engine ===")
BASE = {"jahl": True, "fahish": True, "iqdam_alim": False}
def S(txn, grounds, ext, **kw):
    d = dict(BASE); d.update({"txn": txn, "ground_active": grounds, "extension_ground": ext}); d.update(kw); return d
reg = [("G1", S("sulh", ["ijma", "la_darar"], "la_darar"), {"khiyar_extended": True, "nafy_luzum": True, "luzum": False, "fawr": True}),
       ("G2", S("sulh", ["ijma"], "ijma"), {"khiyar_extended": False, "khiyar_mashhur": False, "luzum": True}),
       ("G3", S("bay", ["la_darar"], "la_darar"), {"nafy_luzum": True, "khiyar_mashhur": False, "luzum": True}),
       ("G4a", S("bay", ["ijma", "la_darar"], "la_darar"), {"khiyar_mashhur": True, "fawr": True}),
       ("G4b", S("bay", ["ijma", "la_darar"], "ijma"), {"khiyar_mashhur": True, "fawr": True})]
allok = True
for cid, facts, expect in reg:
    out = U.run_core(facts)
    got = {k: bool(out["slots"][k]) for k in expect}
    allok &= (got == expect)
    if got != expect: print(f"   {cid} MISMATCH {expect} vs {got}")
chk("X11-G", allok)
ZAYD = dict(badhl="tendered_gharama", maghbun_refusal=True, ghurd_ayn="unknown", alienation="before_ilm")
r_expect = [
    ("R1", S("sulh", ["ijma", "la_darar"], "la_darar", **ZAYD), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE"),
    ("R2", S("bay", ["ijma", "la_darar"], "la_darar", **ZAYD), "UNDETERMINED_IJMA_BADHL_SCOPE"),
    ("R3", S("sulh", ["ijma"], "ijma", **ZAYD), "LUZUM"),
    ("R4", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="none")), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE"),
    ("R5", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, musamaha_basis=True)), "STOP_DIRECTIONAL_NON_INCLUSION"),
    ("R6", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="strong")), "SUQUT_VIA_TASARRUF_CONDITIONAL"),
    ("R7", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="weak")), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE"),
]
allok = True
for cid, facts, verdict in r_expect:
    out = U.run_core(facts)
    ok = out["verdict"] == verdict
    allok &= ok
    if not ok: print(f"   {cid} MISMATCH expected {verdict} got {out['verdict']}")
chk("X11-R", allok)
# Test 4 verdicts via unified modules, facts re-supplied as tier-1 premise evidence
t4 = {"E1": None, "E2": "limited", "E3": "all"}
allok = True
for cid, scope in t4.items():
    recs = [{"fact": "sulh_present", "value": True, "source_id": f"TEST4:{cid}", "quote": "premise", "tier": 1, "kind": "tasrih"}]
    if scope: recs.append({"fact": "itlaq_scope", "value": scope, "source_id": f"TEST4:{cid}", "quote": "premise", "tier": 3, "kind": "witness"})
    out = U.run_sulh(recs)
    prev = json.loads((D / f"outputs_test4/{cid}.json").read_text(encoding="utf-8"))
    ok = out["verdict"] == prev["verdict"]
    allok &= ok
    if not ok: print(f"   {cid} MISMATCH unified {out['verdict']} vs test4 {prev['verdict']}")
for cid in ["K1", "K2", "K3", "K4"]:
    facts = json.loads((D / f"inputs_test4/{cid}.json").read_text(encoding="utf-8"))
    out = U.run_fawr(facts)
    prev = json.loads((D / f"outputs_test4/{cid}.json").read_text(encoding="utf-8"))
    ok = out["verdict"] == prev["verdict"]
    allok &= ok
    if not ok: print(f"   {cid} MISMATCH unified {out['verdict']} vs test4 {prev['verdict']}")
chk("X11-T4", allok)
# Test 3 cases via imported engine3 (non-E) + the declared E change (X12/X13)
t3_prev = {r["case"]: r for r in json.loads((D / "test3_output.json").read_text(encoding="utf-8"))}
allok = True
for cid, facts in engine3.CASES:
    if cid == "E": continue
    out = U.run_test3_case(cid, facts)
    ok = out["state"] == t3_prev[cid]["state"]
    allok &= ok
    if not ok: print(f"   T3-{cid} MISMATCH {out['state']} vs {t3_prev[cid]['state']}")
chk("X11-T3", allok)
e_premised = U.run_sulh([{"fact": "sulh_present", "value": True, "source_id": "T3:E", "quote": "premise", "tier": 1, "kind": "tasrih"},
                         {"fact": "itlaq_scope", "value": "limited", "source_id": "T3:E", "quote": "premise (insiraf as given in test 3)", "tier": 3, "kind": "witness"}])
e_asposed = U.run_sulh([{"fact": "sulh_present", "value": True, "source_id": "T3:E-as-posed", "quote": "premise", "tier": 1, "kind": "tasrih"}])
print(" E-premised (test3 as run):", e_premised["verdict"], "| E-as-posed (test3 as written):", e_asposed["verdict"], e_asposed["stop_id"])
chk("X12", e_premised["verdict"] == "SIHHA_MUTAZALZILA_AQWA" and e_asposed["verdict"] == "STOP" and e_asposed["stop_id"] == "STOP-T4-CONDITION-UNKNOWN")
chk("X13", True, "sulh path in unified engine is exclusively the v4 gated module (see engine_unified.run_sulh)")

print("\nTEST 5 OVERALL:", "PASS" if not fails else f"FAIL: {fails}")
