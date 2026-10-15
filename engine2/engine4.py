# -*- coding: utf-8 -*-
"""Engine 4 — THREE-STATE condition audit engine (Test 4).

Every rule condition is evaluated against facts whose values may be
True / False / None(unknown):
  FIRED           - all conditions verified True/False as expected
  BLOCKED_FALSE   - at least one condition verified contrary (rule inapplicable)
  BLOCKED_UNKNOWN - at least one condition unknown, none contrary (rule may NOT
                    be executed; if it is on the case's critical path the
                    verdict is a STOP, never a guess)
Usage: python3 engine4.py <input.json> <output.json>
Set ABLATE_INSIRAF=True (in the separate ablated copy) to bypass the
has_urf_insiraf gate for the ablation experiment."""
import json, pathlib, sys

ABLATE_INSIRAF = False
D = pathlib.Path(__file__).parent
RULES = json.loads((D / "rules_v4.json").read_text(encoding="utf-8"))["nodes"]
RULE = {r["rule_id"]: r for r in RULES}

def eval_rule(rule, facts, trace):
    rid = rule["rule_id"]; status = "FIRED"; detail = []
    for cond in rule["conditions"]:
        fact, expect = cond["fact"], cond["expect"]
        val = facts.get(fact)
        if cond.get("gate") == "has_urf_insiraf" and ABLATE_INSIRAF:
            detail.append(f"{fact}: CHECK BYPASSED (ablation build) — treated as satisfied")
            trace.append(f"  [{rid}] gate has_urf_insiraf BYPASSED by ablation flag")
            continue
        if val is None:
            if status == "FIRED": status = "BLOCKED_UNKNOWN"
            detail.append(f"{fact}: UNKNOWN (no evidence in input)")
        elif val == expect:
            detail.append(f"{fact}: verified = {val}")
        else:
            status = "BLOCKED_FALSE"
            detail.append(f"{fact}: NEGATED (={val}, expected {expect})")
    trace.append(f"  [{rid}] {status} | " + "; ".join(detail))
    return status

def run(facts):
    trace = [f"input facts: {json.dumps(facts, ensure_ascii=False)}"]
    status = {}
    for r in RULES:
        status[r["rule_id"]] = eval_rule(r, facts, trace)
    verdict, stop = None, None
    if facts.get("case_kind") == "sulh":
        if status["SULH-ITLAQ"] == "FIRED":
            verdict = "SIHHA_MUTAZALZILA_AQWA"
        elif status["SULH-UMUM"] == "FIRED":
            verdict = "SIHHA_LAZIM"
            if facts.get("scope_provenance") == "qarain":
                trace.append("  NOTE: scope established by qara'in, not tasrih — equating the two is an engine inference (attribution C for that step)")
                verdict = "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION"
        elif "BLOCKED_UNKNOWN" in (status["SULH-ITLAQ"], status["SULH-UMUM"]):
            verdict, stop = "STOP", "STOP-T4-CONDITION-UNKNOWN"
            trace.append("  VERDICT: STOP — a condition on the critical path is UNKNOWN; the engine does not guess it")
        else:
            verdict, stop = "STOP", "STOP-T4-ITLAQ-NO-INSIRAF"
            trace.append("  VERDICT: STOP — itlaq with insiraf negated and no all-marAtib scope: this branch is not developed in the text; the engine does not invent it")
    elif facts.get("case_kind") == "fawr":
        if status["EXC-JAHL-KHIYAR"] == "FIRED":
            verdict = "KHIYAR_PERSISTS_EXCUSED_JAHL_KHIYAR"
        elif status["EXC-MANI"] == "FIRED":
            verdict = "KHIYAR_PERSISTS_EXCUSED_MANI"
        elif status["OPEN-JAHL-FAWRIYYA"] == "FIRED":
            verdict = "CONTESTED_EXCUSE_JAHL_FAWRIYYA"
        elif status["FAWR-DELAY"] == "FIRED":
            verdict = "SUQUT_LATE_FASKH_INEFFECTIVE"
        else:
            verdict = "NO_DELAY_ISSUE"
    return {"case": facts.get("case"), "verdict": verdict, "stop_id": stop,
            "rule_status": status, "ablated_build": ABLATE_INSIRAF, "trace": trace}

if __name__ == "__main__":
    facts = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = run(facts)
    pathlib.Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {result['case']}: {result['verdict']} (stop={result['stop_id']}, ablated={result['ablated_build']})")
    for line in result["trace"]:
        print(line)
