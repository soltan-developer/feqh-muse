# -*- coding: utf-8 -*-
"""Unified engine v2 (Test 6) — one input contract for every module.

Changes vs v1 (each traced to an audit finding):
- Evidence admission now verifies against the source REGISTRY: the quote
  must actually occur in the registered source (factstore.verify_record).
  A source_id alone admits nothing. Probative standing (level 3) is
  reported as UNVERIFIED — the engine machine-checks levels 1-2 only.
- Every module takes a FactStore (origins: stated_premise /
  verified_evidence / derived / unverified_hypothesis). Raw dicts are
  refused by contract. A hypothesis never satisfies a condition.
- UNKNOWN is a stop everywhere: run_fawr and run_core halt with named
  stop ids instead of defaulting on missing facts.
- The test-3 module is FACT-DRIVEN (rules_t3.json): no case_id exists in
  its signature or body; verdicts compose from rules over facts alone.
- ABLATE_GATE (default False) exists ONLY as the documented seam for the
  real X13 test and the mutation battery."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine2_1
from factstore import FactStore, verify_record

D = pathlib.Path(__file__).parent
V4 = {r["rule_id"]: r for r in json.loads((D / "rules_v4.json").read_text(encoding="utf-8"))["nodes"]}
T3 = {r["rule_id"]: r for r in json.loads((D / "rules_t3.json").read_text(encoding="utf-8"))["nodes"]}
ABLATE_GATE = False

def _admit(status):
    return status == "QUOTE_VERIFIED"

# ---------- evaluation over a FactStore ----------
def eval_rule(rule, store, trace):
    rid = rule["rule_id"]; status = "FIRED"
    for cond in rule["conditions"]:
        fact, expect = cond["fact"], cond["expect"]
        val, origin = store.effective(fact)
        if isinstance(val, str) and val == "CONFLICT":
            if status == "FIRED": status = "BLOCKED_CONFLICT"
            trace.append(f"  [{rid}] {fact}: CONFLICT")
        elif val is None:
            if status == "FIRED": status = "BLOCKED_UNKNOWN"
            trace.append(f"  [{rid}] {fact}: UNKNOWN" + (" (hypothesis not admissible)" if origin == "unverified_hypothesis" else ""))
        elif val == expect:
            trace.append(f"  [{rid}] {fact}: verified = {val} (origin {origin})")
        else:
            status = "BLOCKED_FALSE"
            trace.append(f"  [{rid}] {fact}: NEGATED (={val})")
    trace.append(f"  [{rid}] => {status}")
    return status

# ---------- sulh module: records in, registry-verified ----------
def run_sulh(records, rules=None):
    rules = rules or V4
    log, admitted, hyp = [], [], []
    for rec in records:
        status, origin = verify_record(rec)
        if ABLATE_GATE:
            admitted.append((rec, "stated_premise")) if rec.get("source_id") else None
            continue
        if not _admit(status):
            log.append(f"REJECTED {rec.get('fact')}: {status} (source_id={rec.get('source_id')!r})")
            continue
        if rec.get("downgraded") == "hypothesis":
            hyp.append(rec)
            log.append(f"HYPOTHESIS-ONLY {rec.get('fact')}: downgraded by extractor guard — cannot establish")
            continue
        admitted.append((rec, origin))
        log.append(f"ADMITTED {rec.get('fact')} = {rec.get('value')} [{status}, origin={origin}, src={rec.get('source_id')}]")
    # resolve itlaq_scope over admitted records (tier policy as declared in test 5)
    scope_recs = [r for r, o in admitted if r["fact"] == "itlaq_scope"]
    store = FactStore()
    for r, o in admitted:
        if r["fact"] == "sulh_present":
            store.assert_fact("sulh_present", r["value"], o, r.get("source_id"))
    scope_val, scope_status = None, "unknown"
    if scope_recs:
        vals = {json.dumps(r["value"], sort_keys=True) for r in scope_recs}
        if len(vals) == 1:
            scope_val, scope_status = scope_recs[0]["value"], "established"
        else:
            best = min(r["tier"] for r in scope_recs)
            top = [r for r in scope_recs if r["tier"] == best]
            if len({json.dumps(r["value"], sort_keys=True) for r in top}) == 1:
                scope_val, scope_status = top[0]["value"], "established"
            else:
                scope_status = "conflict"
    if scope_status == "established":
        store.derive("insiraf_limited_customary", scope_val == "limited", "scope-resolution")
        store.derive("scope_all_maratib", scope_val == "all", "scope-resolution")
        kinds = {r["kind"] for r in scope_recs}
        store.derive("scope_provenance", "tasrih" if "tasrih" in kinds else "qarain", "scope-resolution")
    elif scope_status == "conflict":
        store.assert_fact("insiraf_limited_customary", "CONFLICT", "derived", "scope-resolution")
        store.assert_fact("scope_all_maratib", "CONFLICT", "derived", "scope-resolution")
    trace = list(log)
    st = {rid: eval_rule(rules[rid], store, trace) for rid in ("SULH-ITLAQ", "SULH-UMUM")}
    verdict, stop = None, None
    if st["SULH-ITLAQ"] == "FIRED":
        verdict = "SIHHA_MUTAZALZILA_AQWA"
    elif st["SULH-UMUM"] == "FIRED":
        prov, _ = store.effective("scope_provenance")
        verdict = "SIHHA_LAZIM" if prov == "tasrih" else "SIHHA_LAZIM_CONDITIONAL_ON_QARAIN_TASRIH_EQUATION"
    elif "BLOCKED_CONFLICT" in st.values():
        verdict, stop = "STOP", "STOP-T5-EVIDENCE-CONFLICT"
    elif "BLOCKED_UNKNOWN" in st.values():
        verdict, stop = "STOP", "STOP-T4-CONDITION-UNKNOWN"
    else:
        verdict, stop = "STOP", "STOP-T4-ITLAQ-NO-INSIRAF"
    return {"module": "sulh_audit_v4", "verdict": verdict, "stop_id": stop,
            "scope": {"value": scope_val, "status": scope_status},
            "rule_status": st, "admission_log": log,
            "probative_validation": "UNVERIFIED (engine verifies claim-id and quote-in-source only)",
            "trace": trace}

# ---------- fawr module: FactStore only, UNKNOWN = stop ----------
FAWR_REQUIRED = ("delay_beyond_urf", "jahl_khiyar_during_delay", "jahl_fawriyya_during_delay", "mani_during_delay")
def run_fawr(store):
    if not isinstance(store, FactStore):
        raise TypeError("contract: run_fawr accepts a FactStore only")
    trace = []
    unknowns = [f for f in FAWR_REQUIRED if store.effective(f)[0] is None]
    if unknowns:
        return {"module": "fawr_audit_v4", "verdict": "STOP", "stop_id": "STOP-T6-INSUFFICIENT-FACTS", "unknown_facts": unknowns, "trace": trace}
    st = {rid: eval_rule(V4[rid], store, trace) for rid in ("FAWR-DELAY", "EXC-JAHL-KHIYAR", "EXC-MANI", "OPEN-JAHL-FAWRIYYA")}
    if st["EXC-JAHL-KHIYAR"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_JAHL_KHIYAR"
    elif st["EXC-MANI"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_MANI"
    elif st["OPEN-JAHL-FAWRIYYA"] == "FIRED": verdict = "CONTESTED_EXCUSE_JAHL_FAWRIYYA"
    elif st["FAWR-DELAY"] == "FIRED": verdict = "SUQUT_LATE_FASKH_INEFFECTIVE"
    else: verdict = "NO_DELAY_ISSUE"
    return {"module": "fawr_audit_v4", "verdict": verdict, "stop_id": None, "rule_status": st, "trace": trace}

# ---------- core module: FactStore only, routing facts must be known ----------
CORE_REQUIRED = ("txn", "ground_active", "extension_ground", "jahl", "fahish", "iqdam_alim")
def run_core(store):
    if not isinstance(store, FactStore):
        raise TypeError("contract: run_core accepts a FactStore only")
    unknowns = [f for f in CORE_REQUIRED if store.effective(f)[0] is None]
    if unknowns:
        return {"verdict": "STOP", "stop_id": "STOP-T6-CORE-FACTS-UNKNOWN", "unknown_facts": unknowns}
    return engine2_1.run21(store.plain())

# ---------- test-3 module: fact-driven, NO case id ----------
def run_t3(store):
    if not isinstance(store, FactStore):
        raise TypeError("contract: run_t3 accepts a FactStore only")
    b, _ = store.effective("belief_martaba"); a, _ = store.effective("actual_martaba")
    if b is not None and a is not None:
        store.derive("martaba_mismatch", b != a, "T3-DERIVE-MISMATCH")
    trace = []
    st = {rid: eval_rule(T3[rid], store, trace) for rid in T3}
    act, _ = store.effective("act")
    if act == "sulh":
        return {"module": "t3_fact_driven", "verdict": "ROUTE_TO_SULH_MODULE", "rule_status": st, "trace": trace}
    if st["T3-FASKH-PRE-DALIL"] == "BLOCKED_UNKNOWN":
        verdict, stop = "STOP", "STOP-T3-A"
    elif st["T3-ISQAT-MISTAKE"] == "FIRED":
        verdict, stop = "CONTESTED_OPEN_T3C", None
        if st["T3-ISQAT-PRE"] == "FIRED":
            trace.append("  composition: pre-zuhur validity (mana 2) established, but the mistaken-martaba node stays open -> overall CONTESTED")
    elif st["T3-ISQAT-UMUM"] == "FIRED":
        verdict, stop = "SUQUT_VALID", None
        if st["T3-ISQAT-PRE"] == "FIRED":
            trace.append("  composition: umum wording + pre-zuhur timing; validity rests on mana 2 (thubut haqq)")
    elif st["T3-PRICE-AT-AQD"] == "FIRED":
        verdict, stop = "KHIYAR_PERSISTS_PRICE_AT_AQD", None
    elif st["T3-BASE"] == "FIRED":
        verdict, stop = "KHIYAR_ESTABLISHED_SULTANA_FROM_ILM", None
    else:
        verdict, stop = "STOP", "STOP-T6-NO-RULE-FIRED"
    return {"module": "t3_fact_driven", "verdict": verdict, "stop_id": stop, "rule_status": st, "trace": trace}

# ---------- generic logic evaluator (unchanged semantics from v1) ----------
def eval_logic(rules, facts):
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
    top = {c: [r for r in rs if r["priority"] == best] for c, rs in by_conc.items() if any(r["priority"] == best for r in rs)}
    if len(top) == 1:
        c = next(iter(top))
        trace.append(f"  CONFLICT resolved by pre-declared priority {best}: {c} wins")
        return {"verdict": c, "via": [r["id"] for r in top[c]], "conflict_resolved_by": "priority", "trace": trace, "fired": [r["id"] for r in fired]}
    trace.append("  CONFLICT at equal priority — no valid murajjih: STOP")
    return {"verdict": "CONFLICTED_STOP", "trace": trace, "fired": [r["id"] for r in fired]}
