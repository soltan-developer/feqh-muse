# -*- coding: utf-8 -*-
"""Unified engine (Test 5) — one entry point, shared semantics.

Architecture (declared, not hidden):
- Evidence layer: every fact enters ONLY as an evidence record
  {fact, value, source_id, quote, tier, kind}. Records without a source_id
  are REJECTED by the validation layer (a bare verified=true flag is not
  evidence). Per-fact resolution yields one of: established value /
  UNKNOWN / CONFLICT (both sides preserved; a higher evidence tier wins,
  a same-tier clash stays CONFLICT). Tier policy is this engine's declared
  design policy for the audit tests: 1=tasrih/text of agreement,
  2=expert 'urf determination, 3=witness/party claim.
- Rule evaluation is three-state (+conflict): FIRED / BLOCKED_FALSE /
  BLOCKED_UNKNOWN / BLOCKED_CONFLICT. Stops are per-path, never global,
  unless the stopped path is the only one to the verdict.
- Modules: ghabn core = engine2_1.run21 imported unchanged (hash in the
  manifest); sulh audit = rules_v4 evaluated here; test-3 module =
  engine3.run_case imported for non-sulh cases, with the sulh case (E)
  SUPERSEDED by the gated v4 path (supersession recorded in the trace).
"""
import json, pathlib, sys
sys.path.insert(0, "/home/hatch/workspace/ansari-engine/engine2")
import engine2_1
import engine3

D = pathlib.Path(__file__).parent
V4 = {r["rule_id"]: r for r in json.loads((D / "rules_v4.json").read_text(encoding="utf-8"))["nodes"]}

# ---------- evidence layer ----------
def validate_evidence(records, log):
    valid = []
    for rec in records:
        if not rec.get("source_id"):
            log.append(f"REJECTED evidence for fact '{rec.get('fact')}': no source_id "
                       f"(a bare claim/flag is not evidence) -> contributes nothing")
            continue
        valid.append(rec)
    return valid

def resolve_fact(records, fact, log):
    """Return (value, status, winners) with status in
    established / unknown / conflict."""
    rs = [r for r in records if r["fact"] == fact]
    if not rs:
        return None, "unknown", []
    by_val = {}
    for r in rs:
        by_val.setdefault(json.dumps(r["value"], ensure_ascii=False, sort_keys=True), []).append(r)
    if len(by_val) == 1:
        v = rs[0]["value"]
        log.append(f"fact {fact}: established = {v} (evidence: {[r['source_id'] for r in rs]})")
        return v, "established", rs
    best_tier = min(r["tier"] for r in rs)
    top = [r for r in rs if r["tier"] == best_tier]
    top_vals = {json.dumps(r["value"], ensure_ascii=False, sort_keys=True) for r in top}
    if len(top_vals) == 1:
        v = top[0]["value"]
        log.append(f"fact {fact}: CONFLICT resolved by tier — tier {best_tier} record(s) win -> {v} "
                   f"(losing evidence preserved: {[r['source_id'] for r in rs if r['tier'] != best_tier]})")
        return v, "established", top
    log.append(f"fact {fact}: CONFLICT at tier {best_tier} — both sides preserved, no valid murajjih: "
               f"{[(r['source_id'], r['value']) for r in top]}")
    return None, "conflict", top

# ---------- three-state rule evaluation ----------
def eval_rule(rule, facts, trace):
    rid = rule["rule_id"]; status = "FIRED"
    for cond in rule["conditions"]:
        fact, expect = cond["fact"], cond["expect"]
        val = facts.get(fact)
        if val == "CONFLICT":
            if status == "FIRED": status = "BLOCKED_CONFLICT"
            trace.append(f"  [{rid}] {fact}: CONFLICT (unresolved evidence)")
        elif val is None:
            if status == "FIRED": status = "BLOCKED_UNKNOWN"
            trace.append(f"  [{rid}] {fact}: UNKNOWN")
        elif val == expect:
            trace.append(f"  [{rid}] {fact}: verified = {val}")
        else:
            status = "BLOCKED_FALSE"
            trace.append(f"  [{rid}] {fact}: NEGATED (={val})")
    trace.append(f"  [{rid}] => {status}")
    return status

# ---------- sulh audit module (rules_v4, gated) ----------
def run_sulh(records, extra_facts=None):
    log = []
    valid = validate_evidence(records, log)
    scope_val, scope_status, winners = resolve_fact(valid, "itlaq_scope", log)
    sulh_val, _, _ = resolve_fact(valid, "sulh_present", log)
    facts = {"sulh_present": sulh_val if sulh_val is not None else (extra_facts or {}).get("sulh_present"),
             "scope_provenance": None}
    if scope_status == "established":
        facts["insiraf_limited_customary"] = (scope_val == "limited")
        facts["scope_all_maratib"] = (scope_val == "all")
        if scope_val == "all":
            kinds = {w["kind"] for w in winners}
            facts["scope_provenance"] = "tasrih" if "tasrih" in kinds else "qarain"
    elif scope_status == "conflict":
        facts["insiraf_limited_customary"] = "CONFLICT"
        facts["scope_all_maratib"] = "CONFLICT"
    trace = list(log)
    st = {rid: eval_rule(V4[rid], facts, trace) for rid in ("SULH-ITLAQ", "SULH-UMUM")}
    verdict, stop = None, None
    if st["SULH-ITLAQ"] == "FIRED":
        verdict = "SIHHA_MUTAZALZILA_AQWA"
    elif st["SULH-UMUM"] == "FIRED":
        verdict = "SIHHA_LAZIM" if facts.get("scope_provenance") == "tasrih" else "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION"
    elif "BLOCKED_CONFLICT" in st.values():
        verdict, stop = "STOP", "STOP-T5-EVIDENCE-CONFLICT"
    elif "BLOCKED_UNKNOWN" in st.values():
        verdict, stop = "STOP", "STOP-T4-CONDITION-UNKNOWN"
    else:
        verdict, stop = "STOP", "STOP-T4-ITLAQ-NO-INSIRAF"
    return {"module": "sulh_audit_v4", "verdict": verdict, "stop_id": stop,
            "scope": {"value": scope_val, "status": scope_status},
            "rule_status": st, "validation_log": log, "trace": trace}

# ---------- fawr audit module (rules_v4) ----------
def run_fawr(facts):
    trace = []
    st = {rid: eval_rule(V4[rid], facts, trace) for rid in ("FAWR-DELAY", "EXC-JAHL-KHIYAR", "EXC-MANI", "OPEN-JAHL-FAWRIYYA")}
    if st["EXC-JAHL-KHIYAR"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_JAHL_KHIYAR"
    elif st["EXC-MANI"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_MANI"
    elif st["OPEN-JAHL-FAWRIYYA"] == "FIRED": verdict = "CONTESTED_EXCUSE_JAHL_FAWRIYYA"
    elif st["FAWR-DELAY"] == "FIRED": verdict = "SUQUT_LATE_FASKH_INEFFECTIVE"
    else: verdict = "NO_DELAY_ISSUE"
    return {"module": "fawr_audit_v4", "verdict": verdict, "rule_status": st, "trace": trace}

# ---------- generic logic evaluator (Experiment 3) ----------
def eval_logic(rules, facts):
    """Rules: {id, conditions[{fact,expect}], conclusion, priority}.
    Deterministic regardless of rule order: outcomes resolved by
    (priority desc, conclusion) after evaluating every rule."""
    trace, fired = [], []
    for r in sorted(rules, key=lambda x: x["id"]):
        status = "FIRED"
        for c in r["conditions"]:
            v = facts.get(c["fact"])
            if v is None:
                if status == "FIRED": status = "BLOCKED_UNKNOWN"
            elif v != c["expect"]:
                status = "BLOCKED_FALSE"
        trace.append(f"  [{r['id']}] => {status} (conclusion {r['conclusion']}, priority {r['priority']})")
        if status == "FIRED":
            fired.append(r)
    by_conc = {}
    for r in fired:
        by_conc.setdefault(r["conclusion"], []).append(r)
    if not by_conc:
        return {"verdict": "NO_CONCLUSION", "trace": trace, "fired": [r["id"] for r in fired]}
    if len(by_conc) == 1:
        c = next(iter(by_conc))
        return {"verdict": c, "via": [r["id"] for r in by_conc[c]], "trace": trace, "fired": [r["id"] for r in fired]}
    best = max(r["priority"] for r in fired)
    winners = [c for c, rs in by_conc.items() if any(r["priority"] == best for r in rs)]
    top = {c: [r for r in rs if r["priority"] == best] for c, rs in by_conc.items() if any(r["priority"] == best for r in rs)}
    if len(top) == 1:
        c = next(iter(top))
        trace.append(f"  CONFLICT resolved by pre-declared priority {best}: {c} wins")
        return {"verdict": c, "via": [r["id"] for r in top[c]], "conflict_resolved_by": "priority", "trace": trace, "fired": [r["id"] for r in fired]}
    trace.append("  CONFLICT at equal priority — no valid murajjih: STOP")
    return {"verdict": "CONFLICTED_STOP", "trace": trace, "fired": [r["id"] for r in fired]}

# ---------- core + test3 passthrough (unchanged modules) ----------
def run_core(facts):
    return engine2_1.run21(facts)

def run_test3_case(case_id, facts):
    if case_id == "E":
        raise ValueError("E is superseded by the gated sulh module (X13)")
    return engine3.run_case(case_id, facts)
