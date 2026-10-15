# -*- coding: utf-8 -*-
"""Engine 2 — defeasible rules with the contract's two admission gates.
Gate 1: scientific grade A/B. Gate 2: six operational fields + per-component backing.
The grounding (mustanad) is an explicit scenario fact; the engine never asserts it."""
import json, pathlib

RULES = json.loads((pathlib.Path(__file__).parent/"rules.json").read_text(encoding="utf-8"))
SIX = ["scope", "activation", "defeaters", "exceptions", "conflict_priority", "backing"]

def validate(rule, layer):
    problems = []
    if rule.get("grade") not in ("A", "B"):
        problems.append(f"gate1: grade={rule.get('grade')} (core requires A/B)")
    for f in SIX:
        v = rule.get(f)
        if v is None or v == {} or v == "":
            problems.append(f"gate2: missing '{f}'")
    if rule.get("scope") and not rule["scope"]:
        problems.append("gate2: empty scope")
    if rule.get("backing"):
        for b in rule["backing"]:
            if not all(b.get(k) for k in ("component", "quote", "source", "page")):
                problems.append("gate2: incomplete backing component")
    return problems

def check(cond, facts):
    f, val = cond["fact"], facts.get(cond["fact"])
    if "eq" in cond: return val == cond["eq"]
    if "contains" in cond: return isinstance(val, (list, set)) and cond["contains"] in val
    return False

def run_scenario(facts):
    state = dict(facts); trace = []; asserted_by = {}
    state.setdefault("ground_active", [])
    rules = {r["rule_id"]: r for r in RULES["core"]}
    # pass 1: conditions
    for rid in ["COND-GHABN"]:
        r = rules[rid]
        if all(check(c, state) for c in r["activation"]) and not any(check(d, state) for d in r["defeaters"]):
            state[r["effect"]["assert"]] = True; asserted_by[r["effect"]["assert"]] = rid
            trace.append(f"{rid} FIRED -> {r['effect']['assert']} (backing: " +
                         ", ".join(f"p.{b['page']}" for b in r["backing"]) + ")")
        else:
            trace.append(f"{rid} not fired (conditions/defeaters)")
    if not state.get("conditions_met"):
        return state, trace, asserted_by
    # pass 2: evidence effects
    for rid in ["LD-NAFY", "IJ-KHIYAR", "EXT-LD"]:
        r = rules[rid]
        scope_ok = facts.get("txn") in r["scope"].get("txn_in", [facts.get("txn")])
        blocked = any(check(d, state) for d in r["defeaters"])
        if scope_ok and all(check(c, state) for c in r["activation"]) and not blocked:
            state[r["effect"]["assert"]] = True; asserted_by[r["effect"]["assert"]] = rid
            trace.append(f"{rid} FIRED -> {r['effect']['assert']} (txn={facts.get('txn')}, backing p." +
                         ", p.".join(str(b["page"]) for b in r["backing"]) + ")")
        else:
            why = "out of scope" if not scope_ok else ("defeated" if blocked else "activation unmet")
            trace.append(f"{rid} silent ({why})")
    state["khiyar_asserted"] = bool(state.get("khiyar_mashhur") or state.get("khiyar_extended"))
    state["__no_khiyar__"] = not state["khiyar_asserted"]
    # pass 3: fawr (independent of grounding variables by construction)
    r = rules["FAWR"]
    if all(check(c, state) for c in r["activation"]):
        state["fawr"] = True; asserted_by["fawr"] = "FAWR"
        trace.append("FAWR FIRED -> fawr (derivation: asalat fasad al-faskh, p.212; references no grounding fact)")
    # pass 4: fallback
    r = rules["FALLBACK-LUZUM"]
    if state["__no_khiyar__"]:
        state["luzum"] = True; asserted_by["luzum"] = "FALLBACK-LUZUM"
        trace.append("FALLBACK-LUZUM FIRED -> luzum (no khiyar-establishing ground covers this txn)")
    # slot guard audit
    guard = rules["SLOT-GUARD"]["effect"]["constraint"]
    for slot in ("khiyar_mashhur",):
        if state.get(slot) and asserted_by.get(slot) not in guard["khiyar_mashhur_requires"] + ["EXT-LD"]:
            trace.append(f"SLOT-GUARD VIOLATION: {slot} asserted without valid provenance")
    trace.append("slots: nafy_luzum=%s khiyar_mashhur=%s khiyar_extended=%s luzum=%s fawr=%s" % (
        bool(state.get("nafy_luzum")), bool(state.get("khiyar_mashhur")),
        bool(state.get("khiyar_extended")), bool(state.get("luzum")), bool(state.get("fawr"))))
    return state, trace, asserted_by
