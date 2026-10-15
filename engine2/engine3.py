# -*- coding: utf-8 -*-
"""Engine 3 — test-3 evaluator: huduth/isqat/sulh/ziyada nodes (rules_v3.json)
executed over the ghabn core (rules_v2 via engine2_1). Deterministic; every
verdict cites the nodes that fired and the stops that engaged."""
import json, pathlib, sys
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
from engine2_1 import run21

D = pathlib.Path(__file__).parent
V3 = {n["id"]: n for n in json.loads((D / "rules_v3.json").read_text(encoding="utf-8"))["nodes"]}

def base_facts(**kw):
    f = {"txn": "bay", "price": 20, "value_at_aqd": 2, "jahl": True, "fahish": True,
         "iqdam_alim": False, "ground_active": ["ijma", "la_darar"], "extension_ground": "la_darar",
         "badhl": "none", "alienation": "none", "musamaha_basis": False, "zuhur_day": 5}
    f.update(kw); return f

def out(case_id, facts, fired, not_fired, conditions, verdict, state, stops, delta, evidence):
    return {"case": case_id, "inputs": facts, "rules_fired": fired, "rules_not_fired": not_fired,
            "conditions": conditions, "verdict": verdict, "state": state, "stops": stops,
            "graph_delta_vs_base": delta, "evidence": evidence}

def run_case(case_id, f):
    ev = {n: f"{V3[n]['backing'][0]['source']} p.{V3[n]['backing'][0]['page']}" for n in V3}
    if case_id == "BASE":
        core = run21(f)
        return out(case_id, f, ["COND-GHABN", "IJ-KHIYAR", "FAWR", "HUDUTH-2MANA"], ["ISQAT-*", "SULH-*", "ZIYADA-QIMA"],
                   {"haqq (mana-2)": "exists from 'aqd (p.177)", "sultana fi'liyya (mana-1)": "from zuhur/'ilm day 5",
                    "zuhur role": "kashif for the haqq; shart for the sultana"},
                   "Khiyar established (ijma' route, bay'); haqq predates 'ilm; exercise (faskh) available from day 5, fawr clock from 'ilm",
                   "ثابت (مشروط به فور)", [], "— (reference case)",
                   {"HUDUTH-2MANA": ev["HUDUTH-2MANA"], "IJ-KHIYAR": "Makaseb v5 p.165", "FAWR": "Makaseb v5 p.212"})
    if case_id == "A":
        return out(case_id, f, ["HUDUTH-2MANA"], ["TAS-BAD", "(no per-athar assignment for faskh in text)"],
                   {"real ghabn at 'aqd": True, "zuhur before faskh": False,
                    "sabab believed by Zayd": "imagined, non-existent", "faskh insha' issued": "day 2"},
                   "Branches: mana-1 (sultana) -> faskh ineffective (no sultana before zuhur); mana-2 (haqq) -> insha' attached to an existing right. Ansari poses this exact case as the thamara of the two wujuh (p.179) and assigns no per-athar dalil to faskh in the searched scope. Contrast: had he known of the ghabn on day 2, zuhur would have occurred and faskh would be straightforwardly valid.",
                   "نامعین", ["STOP-T3-A"], "faskh-attempt node added pre-zuhur; HUDUTH fork engaged",
                   {"STOP-T3-A": ev["STOP-T3-A"], "HUDUTH-2MANA": ev["HUDUTH-2MANA"]})
    if case_id in ("B", "C", "D"):
        fired = ["HUDUTH-2MANA", "ISQAT-QABL-ZUHUR"]
        cond = {"timing": "day 2, before zuhur", "iwad": "none",
                "wording_scope": f["wording_scope"], "belief_martaba": f.get("belief_martaba"), "actual_martaba": 18}
        if f["wording_scope"] in ("all_maratib", "all_maratib_explicit_even_more"):
            fired.append("ISQAT-MARATIB-UMUM")
            return out(case_id, f, fired, ["OPEN-T3-C"],
                       cond, "Isqat valid, khiyar extinguished: qabl-zuhur isqat attaches to mana-2 (al-zahir jawazuh), and the insha' quantified over any martaba, so the tayb-nafs objection never engages (p.180: la ishkal).",
                       "منتفی (اسقاط صحیح)", [], "ISQAT-QABL-ZUHUR + ISQAT-MARATIB-UMUM activated", {"ISQAT-QABL-ZUHUR": ev["ISQAT-QABL-ZUHUR"], "ISQAT-MARATIB-UMUM": ev["ISQAT-MARATIB-UMUM"]})
        return out(case_id, f, fired, ["ISQAT-MARATIB-UMUM"],
                   cond, "Two wujuh (p.180): (1) no suqut — 'adam tayb al-nafs bi-hadha al-miqdar (qadhf analogy); (2) suqut — khiyar is ONE right from mutlaq al-tafawut, no multiplicity by maratib (analogy fails: qadhf/shatm are two rights). Ansari states no explicit tarjih for bila-'iwad isqat; wajh-2's unity premise is his own and is reused at p.181, but that reuse is inside the sulh discussion and does not by itself settle this case.",
                   "متعارض/نامعین", ["OPEN-T3-C"], "ISQAT-MARATIB-UMUM NOT activated (wording unqualified) -> OPEN-T3-C engaged",
                   {"OPEN-T3-C": ev["OPEN-T3-C"]})
    if case_id in ("E", "F"):
        cond = {"timing": "before 'ilm of amount", "iwad": 1, "belief_martaba": "4-5 (customary)",
                "actual_martaba": 18, "wording": f["wording_scope"]}
        if f["wording_scope"] == "umum_al_maratib_explicit":
            return out(case_id, f, ["SULH-UMUM"], ["SULH-ITLAQ"],
                       cond, "Sulh valid and binding, no ishkal: tasrih bi-'umum al-maratib (p.181).", "صحیح و لازم", [],
                       "SULH-UMUM activated instead of SULH-ITLAQ", {"SULH-UMUM": ev["SULH-UMUM"]})
        return out(case_id, f, ["SULH-ITLAQ"], ["SULH-UMUM"],
                   cond, "Three wujuh (p.181): butlan / sihha+luzum / sihha mutazalzila (ghabn fi al-musalaha). Ansari: 'wa-hadha huwa al-aqwa' — aqwa = third wajh on the natural antecedent reading: the sulh is valid but shakable; Zayd holds a fresh khiyar al-ghabn in the sulh itself. Version caveat: the bracketed [fa-ta'ammal] after al-aqwa is absent in ms 'q'.",
                   "صحیح متزلزل (اقوی)", ["VERSION-NOTE-T3-E: [فتأمل] absent in 'q'"],
                   "SULH-ITLAQ activated (itlaq + customary insiraf to 4-5)", {"SULH-ITLAQ": ev["SULH-ITLAQ"]})
    if case_id == "G":
        return out(case_id, f, ["ZIYADA-QIMA", "HUDUTH-2MANA"], ["(counter-ihtimal recorded, not adopted)"],
                   {"ghabn at 'aqd (20 vs 2)": True, "value day 3": 20, "rise before zuhur/'ilm": True,
                    "milk qabd-contingent": False},
                   "Khiyar persists: the criterion is value AT 'aqd; the increase accrued in Zayd's own ownership and the transaction occurred upon ghabn (p.167). Recorded counter-ihtimal (not adopted): no khiyar because tadarak occurred before radd — qiyas to the cured 'ayb (Tadhkira). The harder sub-case (rise before qabd where milk is qabd-contingent) is left 'ashkal' by Ansari and is not triggered here.",
                   "ثابت", [], "ZIYADA-QIMA activated; subject-of-ghabn vs tadarak-of-darar split engaged",
                   {"ZIYADA-QIMA": ev["ZIYADA-QIMA"]})
    raise ValueError(case_id)

CASES = [
    ("BASE", base_facts()),
    ("A", base_facts(faskh_attempt={"day": 2, "sabab_belief": "imagined_other_khiyar", "ilm_at_attempt": False})),
    ("B", base_facts(isqat={"day": 2}, wording_scope="all_maratib")),
    ("C", base_facts(isqat={"day": 2}, wording_scope="unqualified", belief_martaba=4)),
    ("D", base_facts(isqat={"day": 2}, wording_scope="all_maratib_explicit_even_more", belief_martaba=4)),
    ("E", base_facts(sulh={"iwad": 1}, wording_scope="itlaq_customary_insiraf", belief_martaba="4-5")),
    ("F", base_facts(sulh={"iwad": 1}, wording_scope="umum_al_maratib_explicit", belief_martaba="4-5")),
    ("G", base_facts(value_day3=20, rise_before_zuhur=True)),
]

if __name__ == "__main__":
    results = [run_case(cid, f) for cid, f in CASES]
    txt = json.dumps(results, ensure_ascii=False, indent=1)
    (D / "test3_output.json").write_text(txt, encoding="utf-8")
    for r in results:
        print(f"### {r['case']}: {r['state']} | stops={r['stops']}")
        print("  fired:", ", ".join(r["rules_fired"]))
        print("  verdict:", r["verdict"][:300])
        print()
    print("full structured output -> test3_output.json")
