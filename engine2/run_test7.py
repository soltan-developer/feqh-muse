# -*- coding: utf-8 -*-
"""Test 7 runner — criteria frozen in TEST7_ACCEPTANCE_FA.md (SHA 2b8ab536...)."""
import json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine_unified as U
from factstore import FactStore

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

print("=== MISSION 1: citation license ===")
rec = {"fact": "itlaq_scope", "value": "all", "source_id": "RAW:A", "quote": "عبارت مصالحه مطلق است", "tier": 1, "kind": "tasrih"}
out = U.run_sulh([SULH_A, rec])
print(" forged-meaning:", out["verdict"], "| log:", out["admission_log"], "| claims preserved:", out["claims_preserved"])
chk("Z1", out["verdict"] == "STOP" and any("ATTRIBUTED_UNLICENSED" in l for l in out["admission_log"]) and out["claims_preserved"] == 1)
import extractor
raw = (D / "raw_test5/B.txt").read_text(encoding="utf-8")
recs, _ = extractor.extract(raw, "B")
out = U.run_sulh(recs)
chk("Z2", out["verdict"] == "SIHHA_MUTAZALZILA_AQWA" and any("ADMITTED_LICENSED" in l for l in out["admission_log"]))
chk("Z3", out["probative_validation"].startswith("UNVERIFIED"))

print("=== MISSION 2: dependency analysis (no hidden defaults) ===")
core_min = {"txn": "sulh", "ground_active": ["ijma", "la_darar"], "extension_ground": "la_darar", "jahl": True, "fahish": True, "iqdam_alim": False}
out = U.run_core(premise_store(core_min, "Z4"))
print(" minimal core, no badhl data:", out["verdict"], "| pivotal:", out.get("pivotal_facts"), "| completions:", out.get("completions_checked"))
chk("Z4", out["verdict"] == "UNDETERMINED_PIVOTAL" and "badhl" in out.get("pivotal_facts", []))
print("   note: maghbun_refusal is SLOT-pivotal here, not verdict-pivotal:", out.get("slot_pivotal_facts"))
out = U.run_core(premise_store({**core_min, "ground_active": ["ijma"], "extension_ground": "ijma", "musamaha_basis": False}, "Z5"))
print(" ijma-only sulh (musamaha stated False), no badhl data:", out["verdict"], "| dep:", out.get("dependency"))
chk("Z5", out["verdict"] == "LUZUM" and "badhl" in out.get("dependency", {}).get("irrelevant_unknowns", []))
out = U.run_core(premise_store({**core_min, "ground_active": ["ijma"], "extension_ground": "ijma"}, "Z5b"))
print(" same but musamaha UNKNOWN:", out["verdict"], "| pivotal:", out.get("pivotal_facts"), "| nonpivotal:", out.get("nonpivotal_unknowns"))
chk("Z5b", out["verdict"] == "UNDETERMINED_PIVOTAL" and "musamaha_basis" in out.get("pivotal_facts", []) and "badhl" in out.get("nonpivotal_unknowns", []))

print("=== MISSION 3: FactStore trust boundary ===")
s = FactStore()
try:
    s.assert_fact("x", 1, "verified_evidence", "self-declared"); z6 = False
except ValueError:
    z6 = True
st_in = premise_store({"delay_beyond_urf": True}, "case-1")
chk("Z6", z6 and st_in.effective("delay_beyond_urf")[1] == "stated_premise")

print("=== MISSION 4: winner-only provenance + multi-evidence store ===")
winner = {"fact": "itlaq_scope", "value": "all", "source_id": "RAW:C", "quote": "قرینه معتبر دیگری نشان می‌دهد اطلاق در قصد مشترک طرفین، تمام مراتب غبن را دربرمی‌گرفته است", "tier": 2, "kind": "expert_urf", "extractor_rule": "EX-SCOPEALL-QARINA"}
loser = {"fact": "itlaq_scope", "value": "limited", "source_id": "RAW:B", "quote": "یک شاهد معتبر نشان می‌دهد عرف این معامله، اطلاق را فقط ناظر به غبن متعارف می‌دانسته است", "tier": 3, "kind": "tasrih", "extractor_rule": "EX-INSIRAF-WITNESS"}
out = U.run_sulh([SULH_A, winner, loser])
print(" winner=expert_urf/all (tier2) + loser tasrih/limited (tier3):", out["verdict"], "| log:", out["admission_log"])
chk("Z7", out["verdict"] == "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION")
s = FactStore()
s.assert_fact("f", 1, "stated_premise", "one")
s.assert_fact("f", 2, "stated_premise", "two")
chk("Z8", len(s.all_entries("f")) == 2 and s.effective("f")[0] == "CONFLICT")

print("=== MISSION 5: fawr staging ===")
s = premise_store({"delay_beyond_urf": False, "jahl_khiyar_during_delay": True, "jahl_fawriyya_during_delay": False, "mani_during_delay": False}, "Z9")
chk("Z9", U.run_fawr(s)["verdict"] == "NO_DELAY_ISSUE")
s = premise_store({"delay_beyond_urf": False}, "Z10")
chk("Z10a", U.run_fawr(s)["verdict"] == "NO_DELAY_ISSUE")
s = premise_store({"delay_beyond_urf": True, "jahl_khiyar_during_delay": False, "mani_during_delay": False}, "Z10b")
out = U.run_fawr(s)
chk("Z10b", out["verdict"] == "STOP" and out["unknown_facts"] == ["jahl_fawriyya_during_delay"])

print("=== MISSION 6+REGRESSION: harness hygiene (Z11/Z12) + test 6 suite (Z15) ===")
r = subprocess.run([sys.executable, str(D / "run_test6.py")], capture_output=True, text=True)
print(" run_test6 exit code:", r.returncode, "| tail:", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
chk("Z15a", r.returncode == 0 and "TEST 6 OVERALL: PASS" in r.stdout)
r = subprocess.run([sys.executable, str(D / "run_mutations.py")], capture_output=True, text=True)
print(" run_mutations exit code:", r.returncode, "| tail:", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
chk("Z15b", r.returncode == 0 and "MUTATION BATTERY: PASS" in r.stdout)
broken = pathlib.Path("/tmp/broken_suite.py")
broken.write_text("import sys\nsys.path.insert(0, '" + str(D) + "')\nimport run_test6\n", encoding="utf-8")
# negative control: a copy of run_test6 with one expectation sabotaged must exit non-zero
src = (D / "run_test6.py").read_text(encoding="utf-8").replace('"SIHHA_MUTAZALZILA_AQWA"', '"SABOTAGED"', 1)
tmp = pathlib.Path("/tmp/run_test6_broken.py"); tmp.write_text(src, encoding="utf-8")
r = subprocess.run([sys.executable, str(tmp)], capture_output=True, text=True, cwd="/tmp")
print(" sabotaged suite exit code:", r.returncode)
chk("Z11", r.returncode != 0)

print("\nTEST 7 (missions 1-6) OVERALL:", "PASS" if not fails else f"FAIL: {fails}")
sys.exit(1 if fails else 0)
