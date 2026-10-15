# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
from engine2 import RULES, validate, run_scenario

print("=== GATE CHECK: core rules ===")
ok = True
for r in RULES["core"]:
    p = validate(r, "core")
    print(f"  {r['rule_id']}: {'ADMITTED' if not p else 'REJECTED ' + str(p)}")
    ok &= not p
print("=== GATE CHECK: hypothesis-layer rules trying to enter core ===")
for r in RULES["hypothesis"]:
    p = validate(r, "core")
    print(f"  {r['rule_id']}: {'ADMITTED?!' if not p else 'kept in hypothesis layer (' + '; '.join(p[:2]) + ')'}")

BASE = {"jahl": True, "fahish": True, "iqdam_alim": False}
def S(txn, grounds, ext):
    d = dict(BASE); d.update({"txn": txn, "ground_active": grounds, "extension_ground": ext}); return d

scen = [
 ("S1 historical — sulh, grounds={ijma,la_darar}, extension=la_darar",
  S("sulh", ["ijma", "la_darar"], "la_darar"),
  {"khiyar_extended": True, "nafy_luzum": True, "luzum": False, "fawr": True}),
 ("S2 counterfactual — sulh, grounds={ijma} only (law istanada ila al-ijma'at)",
  S("sulh", ["ijma"], "ijma"),
  {"khiyar_extended": False, "khiyar_mashhur": False, "luzum": True}),
 ("S3 slot separation — bay', la_darar ONLY (no ijma)",
  S("bay", ["la_darar"], "la_darar"),
  {"nafy_luzum": True, "khiyar_mashhur": False, "luzum": True}),
 ("S4a bay', extension=la_darar", S("bay", ["ijma", "la_darar"], "la_darar"),
  {"khiyar_mashhur": True, "fawr": True}),
 ("S4b bay', extension=ijma (fork variable flipped)", S("bay", ["ijma", "la_darar"], "ijma"),
  {"khiyar_mashhur": True, "fawr": True}),
]
print("\n=== PROBE 1 — MACHINE RUN ===")
allpass = True
for name, facts, expect in scen:
    state, trace, _ = run_scenario(facts)
    res = {k: bool(state.get(k)) for k in expect}
    passed = res == expect
    allpass &= passed
    print(f"\n[{name}] -> {'PASS' if passed else 'FAIL expected ' + str(expect) + ' got ' + str(res)}")
    for t in trace: print("   " + t)
print("\nPROBE 1 OVERALL:", "PASS" if allpass and ok else "CHECK FAILURES ABOVE")
