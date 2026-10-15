# -*- coding: utf-8 -*-
"""Mutation probe: run ONE behavioral probe against an engine directory.
Usage: python3 mutation_probe.py <engine_dir> <probe>
Prints PROBE-RESULT: PASS/FAIL. A probe PASSes when the CORRECT behavior
is observed; a mutation is 'caught' when its target probe FAILs."""
import json, pathlib, sys
ENG = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ENG))
import engine_unified as U
import extractor
from factstore import FactStore

probe = sys.argv[2]
ok = False
if probe == "P-forge":
    sulh = {"fact": "sulh_present", "value": True, "source_id": "RAW:A:EX-SULH", "quote": "مصالحه کرده‌اند", "tier": 1, "kind": "tasrih"}
    forged = {"fact": "itlaq_scope", "value": "limited", "source_id": "FAKE-001", "quote": "عبارت ساختگی", "tier": 1, "kind": "tasrih"}
    ok = U.run_sulh([sulh, forged])["verdict"] == "STOP"
elif probe == "P-neg":
    raw = (ENG / "raw_test6/B2.txt").read_text(encoding="utf-8")
    recs, _ = extractor.extract(raw, "B2")
    ok = not [r for r in recs if r["fact"] == "itlaq_scope"]
elif probe == "P-fawr":
    ok = U.run_fawr(FactStore())["verdict"] == "STOP"
elif probe == "P-hyp":
    s = FactStore()
    s.assert_fact("delay_beyond_urf", True, "stated_premise")
    s.assert_fact("jahl_khiyar_during_delay", False, "unverified_hypothesis", "guess")
    s.assert_fact("jahl_fawriyya_during_delay", False, "stated_premise")
    s.assert_fact("mani_during_delay", False, "stated_premise")
    ok = U.run_fawr(s)["verdict"] == "STOP"
elif probe == "P-order":
    fx = json.loads((ENG / "rules_logic.json").read_text(encoding="utf-8"))
    rules12 = [r for r in fx["rules"] if r["id"] in ("LA", "LB")]
    o1 = U.eval_logic(rules12, fx["facts_phase1"])
    o2 = U.eval_logic(list(reversed(rules12)), fx["facts_phase1"])
    ok = o1["verdict"] == "C" and json.dumps(o1, sort_keys=True, ensure_ascii=False) == json.dumps(o2, sort_keys=True, ensure_ascii=False)
print("PROBE-RESULT:", "PASS" if ok else "FAIL")
