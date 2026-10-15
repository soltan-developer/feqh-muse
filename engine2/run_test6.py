# -*- coding: utf-8 -*-
"""Test 6 runner — criteria frozen in TEST6_ACCEPTANCE_FA.md (SHA 4bce43e0...)."""
import json, pathlib, sys, copy
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
import engine_unified as U
import extractor
from factstore import FactStore, verify_record

D = pathlib.Path(__file__).parent
fails = []
def chk(cid, cond, detail=""):
    print(f"  {cid}: {'PASS' if cond else 'FAIL ' + detail}")
    if not cond: fails.append(cid)

def premise_store(facts, ref="premise"):
    s = FactStore()
    for k, v in facts.items():
        s.assert_fact(k, v, "stated_premise", ref)
    return s

SULH_A = {"fact": "sulh_present", "value": True, "source_id": "RAW:A:EX-SULH", "quote": "مصالحه کرده‌اند", "tier": 1, "kind": "tasrih"}

print("=== MISSION 1: forged credibility ===")
forged = {"fact": "itlaq_scope", "value": "limited", "source_id": "FAKE-001", "quote": "عبارت ساختگی", "tier": 1, "kind": "tasrih"}
out = U.run_sulh([SULH_A, forged])
print(" forged-with-id:", out["verdict"], "| log:", [l for l in out["admission_log"] if "REJECTED" in l])
chk("Y1", out["verdict"] == "STOP" and any("REJECTED_UNREGISTERED_SOURCE" in l for l in out["admission_log"]))
bad_quote = {"fact": "itlaq_scope", "value": "limited", "source_id": "RAW:B:EX-INSIRAF-WITNESS", "quote": "این عبارت در فایل ب وجود ندارد", "tier": 3, "kind": "witness"}
out = U.run_sulh([SULH_A, bad_quote])
print(" real-id-fake-quote:", out["verdict"], "| log:", [l for l in out["admission_log"] if "REJECTED" in l])
chk("Y2", out["verdict"] == "STOP" and any("REJECTED_QUOTE_NOT_IN_SOURCE" in l for l in out["admission_log"]))
st, org = verify_record({"fact": "sulh_rule_text", "value": True, "source_id": "MAKASEB-V5:p181", "quote": "ولو أطلق وكان للإطلاق منصرف", "tier": 1, "kind": "tasrih"})
st2, _ = verify_record({"fact": "sulh_rule_text", "value": True, "source_id": "MAKASEB-V5:p181", "quote": "ولو أطلق وكان للإطلاق منصرف إلى كل المراتب", "tier": 1, "kind": "tasrih"})
print(" makaseb quote:", st, org, "| altered quote:", st2)
chk("Y3", st == "QUOTE_VERIFIED" and org == "verified_evidence" and st2 == "REJECTED_QUOTE_NOT_IN_SOURCE")
chk("Y4", U.run_sulh([SULH_A])["probative_validation"].startswith("UNVERIFIED"))

print("=== MISSION 2: meaning-inversion battery ===")
battery = {}
for b in ["B1", "B2", "B3", "B4", "B5", "B6", "B7"]:
    raw = (D / f"raw_test6/{b}.txt").read_text(encoding="utf-8")
    recs, rep = extractor.extract(raw, b)
    scope = [r for r in recs if r["fact"] == "itlaq_scope"]
    battery[b] = (scope, rep)
    print(f" {b}: scope_records={[(r['value'], r.get('downgraded')) for r in scope]} report={[x['action'] + ':' + x['guard'] for x in rep]}")
chk("Y5a", len(battery["B1"][0]) == 1 and battery["B1"][0][0]["value"] == "limited" and not battery["B1"][0][0].get("downgraded"))
chk("Y5b", len(battery["B7"][0]) == 1 and battery["B7"][0][0]["value"] == "all")
chk("Y6", len(battery["B2"][0]) == 0 and any(x["action"] == "ABSTAIN" for x in battery["B2"][1]))
for b in ["B3", "B5"]:
    recs = battery[b][0]
    out = U.run_sulh([SULH_A] + recs)
    print(f" {b} via engine: {out['verdict']} {out['stop_id']}")
    chk(f"Y7-{b}", len(recs) == 1 and recs[0].get("downgraded") == "hypothesis" and out["verdict"] == "STOP")
for b in ["B4", "B6"]:
    chk(f"Y8-{b}", len(battery[b][0]) == 0 and any(x["action"] == "ABSTAIN" for x in battery[b][1]))

print("=== MISSION 3: UNKNOWN everywhere ===")
out = U.run_fawr(FactStore())
print(" fawr empty:", out["verdict"], out["stop_id"], out.get("unknown_facts"))
chk("Y9a", out["verdict"] == "STOP" and out["stop_id"] == "STOP-T6-INSUFFICIENT-FACTS" and out["unknown_facts"] == ["delay_beyond_urf"])  # staged since test 7: only the subject fact is stage-1 relevant
partial = premise_store({"delay_beyond_urf": True, "jahl_khiyar_during_delay": False})
out = U.run_fawr(partial)
chk("Y9b", out["verdict"] == "STOP" and set(out["unknown_facts"]) == {"jahl_fawriyya_during_delay", "mani_during_delay"})
nodelay = premise_store({"delay_beyond_urf": False, "jahl_khiyar_during_delay": False, "jahl_fawriyya_during_delay": False, "mani_during_delay": False})
chk("Y9c", U.run_fawr(nodelay)["verdict"] == "NO_DELAY_ISSUE")
out = U.run_core(FactStore())
print(" core empty:", out["verdict"], out["stop_id"])
chk("Y10", out["verdict"] == "STOP" and out["stop_id"] == "STOP-T6-CORE-FACTS-UNKNOWN")

print("=== MISSION 4: case-ID independence (fact-driven t3) ===")
import inspect
sig = inspect.signature(U.run_t3)
chk("Y11a", list(sig.parameters) == ["store"], f"run_t3 signature must be (store), got {list(sig.parameters)}")
cases = {
 "BASE": ({"act": "none", "zuhur": True}, "KHIYAR_ESTABLISHED_SULTANA_FROM_ILM"),
 "A": ({"act": "faskh", "timing": "pre_zuhur"}, "STOP"),
 "B": ({"act": "isqat", "timing": "pre_zuhur", "wording_scope": "umum"}, "SUQUT_VALID"),
 "C": ({"act": "isqat", "timing": "post_zuhur", "wording_scope": "specific", "belief_martaba": 4, "actual_martaba": 18, "with_iwad": False}, "CONTESTED_OPEN_T3C"),
 "D": ({"act": "isqat", "timing": "post_zuhur", "wording_scope": "umum"}, "SUQUT_VALID"),
 "G": ({"act": "none", "zuhur": True, "price_rose_full": True, "ghabn_at_aqd": True}, "KHIYAR_PERSISTS_PRICE_AT_AQD"),
}
allok = True
for cid, (facts, expect) in cases.items():
    out = U.run_t3(premise_store(facts, f"t3-{cid}"))
    ok = out["verdict"] == expect
    allok &= ok
    print(f"  t3[{cid}] -> {out['verdict']} (stop={out['stop_id']}) {'ok' if ok else 'MISMATCH exp ' + expect}")
chk("Y11b", allok)
comp = U.run_t3(premise_store({"act": "isqat", "timing": "pre_zuhur", "wording_scope": "specific", "belief_martaba": 4, "actual_martaba": 18, "with_iwad": False}, "composite-new"))
print("  composite (pre-zuhur + mistaken martaba, never branched):", comp["verdict"])
chk("Y12", comp["verdict"] == "CONTESTED_OPEN_T3C" and comp["rule_status"]["T3-ISQAT-PRE"] == "FIRED" and comp["rule_status"]["T3-ISQAT-MISTAKE"] == "FIRED")

print("=== MISSION 5: single input contract ===")
s = premise_store({"delay_beyond_urf": True})
s.assert_fact("jahl_khiyar_during_delay", False, "unverified_hypothesis", "guess")
s.assert_fact("jahl_fawriyya_during_delay", False, "stated_premise")
s.assert_fact("mani_during_delay", False, "stated_premise")
out = U.run_fawr(s)
print(" fawr with hypothesis-as-false:", out["verdict"], out.get("unknown_facts"))
chk("Y13", out["verdict"] == "STOP" and out["unknown_facts"] == ["jahl_khiyar_during_delay"])
try:
    U.run_fawr({"delay_beyond_urf": True}); y14 = False
except TypeError:
    y14 = True
try:
    U.run_core({}); y14 = y14 and False
except TypeError:
    pass
chk("Y14", y14)

print("=== MISSION 6: REAL X13 (gate presence + sabotage sensitivity) ===")
e_posed = U.run_sulh([SULH_A])
patched = copy.deepcopy(U.V4)
patched["SULH-ITLAQ"] = {**patched["SULH-ITLAQ"], "conditions": [c for c in patched["SULH-ITLAQ"]["conditions"] if c["fact"] != "insiraf_limited_customary"]}
e_sabotaged = U.run_sulh([SULH_A], rules=patched)
print(" gate on:", e_posed["verdict"], "| gate sabotaged:", e_sabotaged["verdict"])
chk("Y15", e_posed["verdict"] == "STOP" and e_sabotaged["verdict"] == "SIHHA_MUTAZALZILA_AQWA")

print("=== REGRESSION (Y17) ===")
BASE = {"jahl": True, "fahish": True, "iqdam_alim": False}
def S(txn, grounds, ext, **kw):
    d = dict(BASE); d.update({"txn": txn, "ground_active": grounds, "extension_ground": ext}); d.update(kw); return d
reg = [("G1", S("sulh", ["ijma", "la_darar"], "la_darar"), {"khiyar_extended": True, "nafy_luzum": True, "luzum": False, "fawr": True}),
       ("G2", S("sulh", ["ijma"], "ijma"), {"khiyar_extended": False, "khiyar_mashhur": False, "luzum": True}),
       ("G3", S("bay", ["la_darar"], "la_darar"), {"nafy_luzum": True, "khiyar_mashhur": False, "luzum": True}),
       ("G4a", S("bay", ["ijma", "la_darar"], "la_darar"), {"khiyar_mashhur": True, "fawr": True}),
       ("G4b", S("bay", ["ijma", "la_darar"], "ijma"), {"khiyar_mashhur": True, "fawr": True})]
OPT = {"badhl": "none", "alienation": "none", "maghbun_refusal": False, "ghurd_ayn": "unknown", "dalala_rida": "none", "musamaha_basis": False}
allok = True
for cid, facts, expect in reg:
    out = U.run_core(premise_store({**OPT, **facts}, cid))
    got = {k: bool(out["slots"][k]) for k in expect}
    allok &= (got == expect)
chk("Y17-G", allok)
ZAYD = dict(badhl="tendered_gharama", maghbun_refusal=True, ghurd_ayn="unknown", alienation="before_ilm")
r_expect = [("R1", S("sulh", ["ijma", "la_darar"], "la_darar", **ZAYD), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE"),
            ("R2", S("bay", ["ijma", "la_darar"], "la_darar", **ZAYD), "UNDETERMINED_IJMA_BADHL_SCOPE"),
            ("R3", S("sulh", ["ijma"], "ijma", **ZAYD), "LUZUM"),
            ("R4", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="none")), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE"),
            ("R5", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, musamaha_basis=True)), "STOP_DIRECTIONAL_NON_INCLUSION"),
            ("R6", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="strong")), "SUQUT_VIA_TASARRUF_CONDITIONAL"),
            ("R7", S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="weak")), "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE")]
allok = True
for cid, facts, verdict in r_expect:
    out = U.run_core(premise_store({**OPT, **facts}, cid))
    allok &= (out["verdict"] == verdict)
chk("Y17-R", allok)
# Test 4 via registry-backed records / premise stores
t4e = {"E1": ([SULH_A], "STOP"), "E2": ([SULH_A, {"fact": "itlaq_scope", "value": "limited", "source_id": "T4:E2", "quote": "\"insiraf_limited_customary\": true", "tier": 3, "kind": "witness"}], "SIHHA_MUTAZALZILA_AQWA"),
       "E3": ([SULH_A, {"fact": "itlaq_scope", "value": "all", "source_id": "T4:E3", "quote": "\"scope_all_maratib\": true", "tier": 3, "kind": "witness"}], "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION")}
allok = True
for cid, (recs, expect) in t4e.items():
    out = U.run_sulh(recs)
    allok &= (out["verdict"] == expect)
    if out["verdict"] != expect: print(f"   {cid}: {out['verdict']} != {expect}")
for cid, expect in [("K1", "SUQUT_LATE_FASKH_INEFFECTIVE"), ("K2", "KHIYAR_PERSISTS_EXCUSED_JAHL_KHIYAR"), ("K3", "CONTESTED_EXCUSE_JAHL_FAWRIYYA"), ("K4", "KHIYAR_PERSISTS_EXCUSED_MANI")]:
    facts = json.loads((D / f"inputs_test4/{cid}.json").read_text(encoding="utf-8"))
    keep = {k: facts[k] for k in ("delay_beyond_urf", "jahl_khiyar_during_delay", "jahl_fawriyya_during_delay", "mani_during_delay")}
    out = U.run_fawr(premise_store(keep, cid))
    allok &= (out["verdict"] == expect)
chk("Y17-T4", allok)
# Test 5 scenarios re-based on the registry
for case, expect in [("A", "STOP"), ("B", "SIHHA_MUTAZALZILA_AQWA"), ("C", "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION"), ("D", "STOP"), ("D2", "SIHHA_MUTAZALZILA_AQWA")]:
    raw = (D / f"raw_test5/{case}.txt").read_text(encoding="utf-8")
    recs, _ = extractor.extract(raw, case)
    out = U.run_sulh(recs)
    ok = out["verdict"] == expect
    allok &= ok
    if not ok: print(f"   T5-{case}: {out['verdict']} != {expect}")
rawf = (D / "raw_test6/F.txt").read_text(encoding="utf-8")
recs, _ = extractor.extract(rawf, "F")
out = U.run_sulh(recs)
print(" T3-F (tasrih, fact-driven sulh path):", out["verdict"])
allok &= (out["verdict"] == "SIHHA_LAZIM")
chk("Y17-T5+T3F", allok)
fx = json.loads((D / "rules_logic.json").read_text(encoding="utf-8"))
rules12 = [r for r in fx["rules"] if r["id"] in ("LA", "LB")]
o1, o1r = U.eval_logic(rules12, fx["facts_phase1"]), U.eval_logic(list(reversed(rules12)), fx["facts_phase1"])
chk("Y17-LOGIC", o1["verdict"] == "C" and json.dumps(o1, sort_keys=True, ensure_ascii=False) == json.dumps(o1r, sort_keys=True, ensure_ascii=False))

print("\nTEST 6 OVERALL:", "PASS" if not fails else f"FAIL: {fails}")
sys.exit(1 if fails else 0)
