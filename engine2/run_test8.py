# -*- coding: utf-8 -*-
"""Trust and unknown-state release gate (Test 8).

This suite is deliberately about software safety, NOT proof of fiqh validity.
Run from repository root: python3 engine2/run_test8.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extractor
import engine_unified as U
from factstore import FactStore, verify_record

checks = 0
def check(name, condition, detail=""):
    global checks
    checks += 1
    print(f"{'PASS' if condition else 'FAIL'} {name}: {detail}")
    if not condition:
        raise AssertionError(name + " " + detail)

def store(facts):
    s = FactStore()
    for name, value in facts.items():
        s.assert_fact(name, value, "stated_premise", "T8:case")
    return s

SULH = {"fact": "sulh_present", "value": True,
        "source_id": "RAW:A:EX-SULH", "quote": "مصالحه کرده‌اند",
        "tier": 1, "kind": "tasrih"}

# 1. A real, negated quote must not be re-licensed merely by asserting a rule ID.
neg = {"fact": "itlaq_scope", "value": "limited",
       "source_id": "RAW:B2:EX-INSIRAF-WITNESS",
       "quote": "یک شاهد معتبر نشان نمی‌دهد عرف این معامله، اطلاق را فقط ناظر به غبن متعارف",
       "extractor_rule": "EX-INSIRAF-WITNESS", "tier": 1, "kind": "tasrih"}
s = FactStore()
check("T8-01 actual quote", verify_record(neg)[0] == "QUOTE_VERIFIED")
status, _ = s.admit_record(neg)
check("T8-02 semantic guard cannot be bypassed",
      status == "ATTRIBUTED_UNLICENSED" and s.effective("itlaq_scope")[0] is None)
check("T8-03 guarded path stops", U.run_sulh([SULH, neg])["verdict"] == "STOP")

# 2. Canonical evidence ranking must come from the approved extractor/license.
raw_b = (HERE / "raw_test5/B.txt").read_text(encoding="utf-8")
recs, _ = extractor.extract(raw_b, "B")
item = next(r for r in recs if r["extractor_rule"] == "EX-INSIRAF-WITNESS")
spoof = dict(item, tier=1, kind="tasrih")
s = FactStore()
check("T8-04 extracted record admitted", s.admit_record(spoof)[0] == "ADMITTED_LICENSED")
meta = s.entry("itlaq_scope")["meta"]
check("T8-05 forged tier/kind canonicalized",
      meta["tier"] == 3 and meta["kind"] == "witness")
check("T8-06 legitimate extraction remains usable",
      U.run_sulh([SULH, spoof])["verdict"] == "SIHHA_MUTAZALZILA_AQWA")

manual = {"fact": "itlaq_scope", "value": "all", "source_id": "T4:E3",
          "quote": '"scope_all_maratib": true', "tier": 1, "kind": "tasrih"}
s = FactStore()
check("T8-07 registered manual premise admitted", s.admit_record(manual)[0] == "ADMITTED_LICENSED")
check("T8-08 manual witness cannot impersonate tasrih",
      s.entry("itlaq_scope")["meta"]["tier"] == 3
      and s.entry("itlaq_scope")["meta"]["kind"] == "witness")
check("T8-09 manual witness verdict stays conditional",
      U.run_sulh([SULH, manual])["verdict"] == "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION")

# 3. Only EFFECTIVE facts are known; a stored hypothesis or conflict isn't proof.
base = {"txn": "sulh", "ground_active": ["la_darar"], "extension_ground": "la_darar",
        "jahl": True, "fahish": True, "iqdam_alim": False,
        "alienation": "none", "maghbun_refusal": False,
        "ghurd_ayn": "absent", "dalala_rida": "none", "musamaha_basis": False}
s = store(base)
s.assert_fact("badhl", "tendered_gharama", "unverified_hypothesis", "T8:hyp")
r = U.run_core(s)
check("T8-10 optional hypothesis is enumerated, not defaulted",
      r["verdict"] == "UNDETERMINED_PIVOTAL" and "badhl" in r["pivotal_facts"])

s = store(base)
s.assert_fact("badhl", "none", "stated_premise", "T8:one")
s.assert_fact("badhl", "tendered_gharama", "stated_premise", "T8:two")
r = U.run_core(s)
check("T8-11 conflicting optional evidence is never silently dropped",
      r["verdict"] == "UNDETERMINED_PIVOTAL"
      and "badhl" in r["conflicting_unknowns"]
      and "badhl" in r["pivotal_facts"])

s = store(base)
s.assert_fact("txn", "bay", "stated_premise", "T8:conflict")
r = U.run_core(s)
check("T8-12 conflicting required fact stops",
      r["stop_id"] == "STOP-T8-CORE-FACTS-CONFLICT"
      and "txn" in r["conflict_facts"])

s = store({"delay_beyond_urf": True})
s.assert_fact("delay_beyond_urf", False, "stated_premise", "T8:conflict")
r = U.run_fawr(s)
check("T8-13 conflict in fawr subject stops",
      r["verdict"] == "STOP" and r["stop_id"] == "STOP-T6-INSUFFICIENT-FACTS")

s = store({"delay_beyond_urf": True,
           "jahl_khiyar_during_delay": False, "jahl_fawriyya_during_delay": False,
           "mani_during_delay": False})
s.assert_fact("mani_during_delay", True, "stated_premise", "T8:conflict")
check("T8-14 conflicting excuse stops",
      U.run_fawr(s)["verdict"] == "STOP")

# 4. Cannot mint trusted derivations via the premise API.
s = FactStore()
for origin in ("verified_evidence", "derived"):
    try:
        s.assert_fact("x", True, origin, "T8:forgery")
    except ValueError:
        pass
    else:
        raise AssertionError("T8-15: assert_fact minted origin " + origin)
check("T8-15 trust boundary accepts only explicit premises/hypotheses", True)

# 5. An irrelevant unknown should not stop a known conclusion.
s = store({"txn": "sulh", "ground_active": ["ijma"], "extension_ground": "ijma",
           "jahl": True, "fahish": True, "iqdam_alim": False,
           "musamaha_basis": False})
r = U.run_core(s)
check("T8-16 irrelevant unknowns permit invariant verdict",
      r["verdict"] == "LUZUM" and "badhl" in r["dependency"]["verdict_invariant_unknowns"])

print(f"TEST 8 RELEASE GATE: PASS ({checks} assertions)")
