# -*- coding: utf-8 -*-
"""Retest runner for engine 2.1 — criteria frozen in RETEST_ACCEPTANCE_V21_FA.md
(SHA-256 recorded in RETEST_ACCEPTANCE_V21.sha256 BEFORE this run)."""
import sys
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
from engine2_1 import RULES, validate, run21

fails = []
def chk(cid, cond, detail=""):
    print(f"  {cid}: {'PASS' if cond else 'FAIL ' + detail}")
    if not cond: fails.append(cid)

print("=== GATES (two-axis) ===")
for r in RULES["core"]:
    p = validate(r)
    print(f"  {r['rule_id']} [attr={r.get('attribution')} x force={r.get('force')}]: {'ADMITTED' if not p else 'REJECTED ' + str(p)}")
    if p: fails.append("GATE-" + r["rule_id"])
for r in RULES["hypothesis"]:
    p = validate(r)
    print(f"  {r['rule_id']} (hypothesis): {'kept out of core (' + '; '.join(p[:1]) + ')' if p else 'ADMITTED?!'}")
    if not p: fails.append("GATE-HYP-" + r["rule_id"])

BASE = {"jahl": True, "fahish": True, "iqdam_alim": False}
def S(txn, grounds, ext, **kw):
    d = dict(BASE); d.update({"txn": txn, "ground_active": grounds, "extension_ground": ext}); d.update(kw); return d

print("\n=== REGRESSION G (Probe 1 slot semantics) ===")
reg = [
 ("G1", S("sulh", ["ijma", "la_darar"], "la_darar"), {"khiyar_extended": True, "nafy_luzum": True, "luzum": False, "fawr": True}),
 ("G2", S("sulh", ["ijma"], "ijma"), {"khiyar_extended": False, "khiyar_mashhur": False, "luzum": True}),
 ("G3", S("bay", ["la_darar"], "la_darar"), {"nafy_luzum": True, "khiyar_mashhur": False, "luzum": True}),
 ("G4a", S("bay", ["ijma", "la_darar"], "la_darar"), {"khiyar_mashhur": True, "fawr": True}),
 ("G4b", S("bay", ["ijma", "la_darar"], "ijma"), {"khiyar_mashhur": True, "fawr": True}),
]
for cid, facts, expect in reg:
    out = run21(facts)
    got = {k: out["slots"][k] for k in expect}
    chk(cid, got == expect, f"expected {expect} got {got} verdict={out['verdict']}")

print("\n=== RETEST R (Zayd case + counterfactuals, GRAPH_V2) ===")
ZAYD = dict(badhl="tendered_gharama", maghbun_refusal=True, ghurd_ayn="unknown", alienation="before_ilm")
# R1 base: sulh mu'awadi + badhl + refusal + alienation before 'ilm
o = run21(S("sulh", ["ijma", "la_darar"], "la_darar", **ZAYD))
print(" R1 verdict:", o["verdict"], "| open:", o["open_nodes"], "| sub:", o["sub"])
chk("R1", o["verdict"] == "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE" and "GHURD-AYN" in o["open_nodes"] and "R1-TENDER" in o["open_nodes"] and o["sub"]["tasarruf"] == "persists" and o["sub"]["execution"] == "badal")
# R2 bay' analogue
o = run21(S("bay", ["ijma", "la_darar"], "la_darar", **ZAYD))
print(" R2 verdict:", o["verdict"], "| open:", o["open_nodes"])
chk("R2", o["verdict"] == "UNDETERMINED_IJMA_BADHL_SCOPE" and "IJ-SCOPE-BADHL" in o["open_nodes"])
# R3 counterfactual A: ijma-only ground, sulh
o = run21(S("sulh", ["ijma"], "ijma", **ZAYD))
print(" R3 verdict:", o["verdict"], "| moot:", o["moot"])
chk("R3", o["verdict"] == "LUZUM" and any("badhl" in m for m in o["moot"]))
# R4 counterfactual B: 'ayn present
o = run21(S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="none")))
print(" R4 verdict:", o["verdict"], "| sub:", o["sub"])
chk("R4", o["verdict"] == "FASKH_NOT_ESTABLISHED_ON_LD_ROUTE" and o["sub"]["execution"] == "ayn")
# R5 counterfactual C: musamaha basis
o = run21(S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, musamaha_basis=True)))
print(" R5 verdict:", o["verdict"])
chk("R5", o["verdict"] == "STOP_DIRECTIONAL_NON_INCLUSION")
# R6 counterfactual D: alienation after 'ilm, strong dalala
o = run21(S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="strong")))
print(" R6 verdict:", o["verdict"], "| sub:", o["sub"])
chk("R6", o["verdict"] == "SUQUT_VIA_TASARRUF_CONDITIONAL" and o["sub"]["tasarruf"] == "suqut_conditional")
# R7 control: after 'ilm, weak dalala
o = run21(S("sulh", ["ijma", "la_darar"], "la_darar", **dict(ZAYD, alienation="after_ilm", dalala_rida="weak")))
print(" R7 verdict:", o["verdict"], "| sub:", o["sub"])
chk("R7", o["sub"]["tasarruf"] == "persists_asalat_baqa" and o["verdict"] != "SUQUT_VIA_TASARRUF_CONDITIONAL")

print("\nRETEST OVERALL:", "PASS — all frozen criteria met" if not fails else f"FAIL: {fails}")
