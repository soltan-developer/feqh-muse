# -*- coding: utf-8 -*-
"""Engine 2.1 — implements GRAPH_V2 after the expert-review correction cycle.

Fixes vs engine2.py:
- Two-axis grading (attribution x force); core admits attribution A/B only.
- The mumtani' qualifier (p.165) is scoped to the la-darar ROUTE only; the
  ijma' route carries an OPEN sub-node for its badhl scope instead.
- Open nodes are first-class: they attach to outputs and block categorical verdicts.
- TAS-BAD (post-'ilm disposition) requires the independent dalala node (p.187).
- Stop nodes carry a direction (STOP-MUSAMAHA: leaning non-inclusion, p.205).
Slot semantics are kept identical to engine2 for Probe-1 regression comparability;
a separate verdict layer carries the corrected analysis.
"""
import json, pathlib

D = pathlib.Path(__file__).parent
RULES = json.loads((D / "rules_v2.json").read_text(encoding="utf-8"))
SIX = ["scope", "activation", "defeaters", "exceptions", "conflict_priority", "backing"]

def validate(rule):
    problems = []
    if rule.get("attribution") not in ("A", "B"):
        problems.append(f"gate1: attribution={rule.get('attribution')} (core requires A/B)")
    if not rule.get("force"):
        problems.append("gate1b: missing force axis")
    for f in SIX:
        v = rule.get(f)
        if v is None or v == "":
            problems.append(f"gate2: missing '{f}'")
    for b in rule.get("backing", []):
        if not all(b.get(k) for k in ("component", "quote", "source", "page")):
            problems.append("gate2: incomplete backing component")
    return problems

def check(cond, facts):
    val = facts.get(cond["fact"])
    if "eq" in cond: return val == cond["eq"]
    if "contains" in cond: return isinstance(val, (list, set)) and cond["contains"] in val
    return False

RULE = {r["rule_id"]: r for r in RULES["core"]}

def fires(rid, facts):
    r = RULE[rid]
    scope = r.get("scope", {})
    if "txn_in" in scope and facts.get("txn") not in scope["txn_in"]:
        return False
    return all(check(c, facts) for c in r["activation"]) and not any(check(d, facts) for d in r["defeaters"])

def run21(facts):
    f = {"badhl": "none", "alienation": "none", "dalala_rida": "unknown",
         "ghurd_ayn": "unknown", "musamaha_basis": False, "maghbun_refusal": False,
         "ground_active": [], "extension_ground": None, "iqdam_alim": False}
    f.update(facts)
    trace, open_nodes, moot, notes = [], [], [], []
    slots = {"nafy_luzum": False, "khiyar_mashhur": False, "khiyar_extended": False,
             "luzum": False, "fawr": False}
    sub = {"tasarruf": None, "execution": None}

    def done(verdict):
        return {"verdict": verdict, "slots": slots, "sub": sub,
                "open_nodes": open_nodes, "moot": moot, "notes": notes, "trace": trace}

    # stage 0: directional stop (musamaha basis)
    if fires("STOP-MUSAMAHA", f):
        trace.append("STOP-MUSAMAHA FIRED (p.205: khafa', bal man'a) -> directional stop, leaning non-inclusion")
        return done("STOP_DIRECTIONAL_NON_INCLUSION")
    # stage 1: subject conditions
    if not fires("COND-GHABN", f):
        trace.append("COND-GHABN not fired (jahl/fahish/iqdam)")
        return done("NO_GHABN_SUBJECT")
    f["conditions_met"] = True
    trace.append("COND-GHABN FIRED")
    # stage 2: routes
    grounds = f["ground_active"]
    ij_route = f["txn"] == "bay" and "ijma" in grounds
    ld_ground = "la_darar" in grounds
    if ld_ground:
        f["ld_route"] = True
        if fires("LD-NAFY", f):
            slots["nafy_luzum"] = True
            trace.append("LD-NAFY FIRED -> nafy_luzum (la-darar route; its CERTAIN output only)")
    if ij_route:
        slots["khiyar_mashhur"] = True
        trace.append("IJ-KHIYAR FIRED -> khiyar_mashhur (bay' only; NO mumtani' condition attached — p.165 qualifier belongs to la-darar)")
    if f["txn"] != "bay" and ld_ground and fires("EXT-LD", f):
        slots["khiyar_extended"] = True
        trace.append("EXT-LD FIRED -> khiyar_extended [attribution A x force istizhar-mashrut, p.203/205]")
    ld_reaches = ld_ground and (f["txn"] == "bay" or slots["khiyar_extended"])
    khiyar_asserted = slots["khiyar_mashhur"] or slots["khiyar_extended"]
    f["khiyar_asserted"] = khiyar_asserted
    f["__no_khiyar__"] = not khiyar_asserted
    if khiyar_asserted:
        slots["fawr"] = True
        trace.append("FAWR FIRED (invariant to grounding variable, pp.210-212)")
    if not khiyar_asserted and fires("FALLBACK-LUZUM", f):
        slots["luzum"] = True
        trace.append("FALLBACK-LUZUM FIRED -> luzum")
    # stage 3: tasarruf sub-results (independent of badhl node)
    if f["alienation"] == "before_ilm" and fires("TAS-QABL", f):
        sub["tasarruf"] = "persists"
        sub["execution"] = "badal"
        trace.append("TAS-QABL FIRED (pp.186-190): khiyar persists; execution converts to badal")
        if khiyar_asserted:
            open_nodes.append("X8-BADAL-DAY")
    elif f["alienation"] == "after_ilm":
        if fires("TAS-BAD", f):
            sub["tasarruf"] = "suqut_conditional"
            trace.append("TAS-BAD FIRED via dalala node N8b=strong (p.187): suqut, conditional in form")
        else:
            sub["tasarruf"] = "persists_asalat_baqa"
            trace.append("TAS-BAD blocked: dalala node unmet -> asalat baqa' al-khiyar (p.187)")
    if f["alienation"] == "none":
        sub["execution"] = "ayn"
    # stage 4: verdict synthesis
    if sub["tasarruf"] == "suqut_conditional":
        if f["badhl"] != "none":
            moot.append("badhl_node (suqut by tasarruf precedes it)")
        return done("SUQUT_VIA_TASARRUF_CONDITIONAL")
    if ij_route:
        if f["badhl"] != "none":
            open_nodes.append("IJ-SCOPE-BADHL")
            trace.append("IJ-KHIYAR + badhl: khiyar established, but its persistence vs badhl is the OPEN sub-node (mashhur: non-suqut; no categorical fatwa) -> UNDETERMINED")
            return done("UNDETERMINED_IJMA_BADHL_SCOPE")
        return done("FASKH_ESTABLISHED")
    if ld_reaches:
        if f["badhl"] != "none":
            trace.append("TADARAK-STR (la-darar route only): faskh conditioned on imtina'; ghabin is badhil -> faskh not yielded on this route (pp.162,164)")
            if f["ghurd_ayn"] != "absent":
                open_nodes.append("GHURD-AYN")
            if f["maghbun_refusal"] or f["badhl"] == "tendered_gharama":
                open_nodes.append("R1-TENDER")
            notes.append("force chain: EXT-LD=istizhar (non-bay') + TADARAK-STR=ihtimal-murajjah => conditional, leaning negative")
            return done("FASKH_NOT_ESTABLISHED_ON_LD_ROUTE")
        notes.append("via la-darar/tadarak structure; conditional on EXT-LD istizhar" if f["txn"] != "bay" else "via la-darar/tadarak structure (ihtimal grade)")
        return done("FASKH_ESTABLISHED_VIA_LD_CONDITIONAL")
    if slots["luzum"]:
        if f["badhl"] != "none":
            moot.append("badhl_node (no khiyar route reaches this case)")
        if f["alienation"] != "none":
            moot.append("tasarruf_nodes (no khiyar route reaches this case)")
        return done("LUZUM")
    return done("LUZUM")
