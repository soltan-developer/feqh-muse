# -*- coding: utf-8 -*-
"""Unified engine v3 (Test 7) — trust boundary + dependency analysis.

Changes vs v2 (each traced to the Test 7 audit):
- Evidence admission goes through FactStore.admit_record ONLY: source
  authenticity + quote existence + citation LICENSE (the quote must
  license the claimed fact/value). Unlicensed claims are preserved as
  inert claims, never established facts.
- Scope provenance derives from the WINNING evidence only.
- Fawr is staged: the subject (delay) is established first; excuse facts
  are irrelevant — and cannot stop the case — when no delay occurred.
- The core no longer inherits silent defaults: unknown optional facts are
  resolved by DEPENDENCY ANALYSIS (enumerate completions; a verdict is
  returned only if every completion agrees; otherwise the pivotal
  unknowns are named and the case stops as UNDETERMINED_PIVOTAL).
- ABLATE_GATE (default False) remains the documented seam for the X13
  sabotage-sensitivity test."""
import itertools, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine2_1
from factstore import FactStore

D = pathlib.Path(__file__).parent
V4 = {r["rule_id"]: r for r in json.loads((D / "rules_v4.json").read_text(encoding="utf-8"))["nodes"]}
T3 = {r["rule_id"]: r for r in json.loads((D / "rules_t3.json").read_text(encoding="utf-8"))["nodes"]}
ABLATE_GATE = False

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

# ---------- sulh ----------
def run_sulh(records, rules=None):
    rules = rules or V4
    log, store = [], FactStore()
    for rec in records:
        if ABLATE_GATE:
            if rec.get("source_id"):
                store.entries.setdefault(rec["fact"], []).append({"value": rec["value"], "origin": "stated_premise", "ref": rec.get("source_id"), "resolution": False, "meta": rec})
                log.append(f"ADMITTED (gate ablated) {rec.get('fact')}")
            continue
        status, origin = store.admit_record(rec)
        log.append(f"{status} {rec.get('fact')} = {rec.get('value')!r} (src={rec.get('source_id')})")
    live = [e for e in store.all_entries("itlaq_scope") if e["origin"] != "unverified_hypothesis"]
    scope_val, scope_status, winners = None, "unknown", []
    if live:
        vals = {json.dumps(e["value"], sort_keys=True) for e in live}
        if len(vals) == 1:
            scope_val, scope_status, winners = live[0]["value"], "established", live
        else:
            best = min((e["meta"] or {}).get("tier", 3) for e in live)
            top = [e for e in live if (e["meta"] or {}).get("tier", 3) == best]
            if len({json.dumps(e["value"], sort_keys=True) for e in top}) == 1:
                scope_val, scope_status = top[0]["value"], "established"
                winners = [e for e in top if e["value"] == scope_val]
            else:
                scope_status = "conflict"
    if scope_status == "established":
        store.derive("insiraf_limited_customary", scope_val == "limited", "scope-resolution")
        store.derive("scope_all_maratib", scope_val == "all", "scope-resolution")
        kinds = {(e["meta"] or {}).get("kind") for e in winners}
        store.derive("scope_provenance", "tasrih" if kinds == {"tasrih"} else "qarain", "scope-resolution")
    elif scope_status == "conflict":
        store.derive("insiraf_limited_customary", "CONFLICT", "scope-resolution")
        store.derive("scope_all_maratib", "CONFLICT", "scope-resolution")
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
            "rule_status": st, "admission_log": log, "claims_preserved": len(store.claims),
            "probative_validation": "UNVERIFIED (engine verifies source, quote, and citation license only)",
            "trace": trace}

# ---------- fawr (staged) ----------
def _fawr_stop(unknowns, trace):
    return {"module": "fawr_audit_v4", "verdict": "STOP", "stop_id": "STOP-T6-INSUFFICIENT-FACTS", "unknown_facts": unknowns, "trace": trace}

def run_fawr(store):
    if not isinstance(store, FactStore):
        raise TypeError("contract: run_fawr accepts a FactStore only")
    trace = []
    delay, _ = store.effective("delay_beyond_urf")
    if delay is None or delay == "CONFLICT":
        return _fawr_stop(["delay_beyond_urf"], trace)
    if delay is False:
        return {"module": "fawr_audit_v4", "verdict": "NO_DELAY_ISSUE", "stop_id": None, "trace": trace}
    unknowns = [f for f in ("jahl_khiyar_during_delay", "jahl_fawriyya_during_delay", "mani_during_delay") if store.effective(f)[0] is None or store.effective(f)[0] == "CONFLICT"]
    if unknowns:
        return _fawr_stop(unknowns, trace)
    st = {rid: eval_rule(V4[rid], store, trace) for rid in ("FAWR-DELAY", "EXC-JAHL-KHIYAR", "EXC-MANI", "OPEN-JAHL-FAWRIYYA")}
    if st["EXC-JAHL-KHIYAR"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_JAHL_KHIYAR"
    elif st["EXC-MANI"] == "FIRED": verdict = "KHIYAR_PERSISTS_EXCUSED_MANI"
    elif st["OPEN-JAHL-FAWRIYYA"] == "FIRED": verdict = "CONTESTED_EXCUSE_JAHL_FAWRIYYA"
    elif st["FAWR-DELAY"] == "FIRED": verdict = "SUQUT_LATE_FASKH_INEFFECTIVE"
    else: verdict = "NO_DELAY_ISSUE"
    return {"module": "fawr_audit_v4", "verdict": verdict, "stop_id": None, "rule_status": st, "trace": trace}

# ---------- core (dependency analysis over unknown optionals) ----------
CORE_REQUIRED = ("txn", "ground_active", "extension_ground", "jahl", "fahish", "iqdam_alim")
OPTIONAL_DOMAINS = {"badhl": ["none", "tendered_gharama"], "alienation": ["none", "before_ilm", "after_ilm"],
                    "maghbun_refusal": [False, True], "ghurd_ayn": ["unknown", "absent"],
                    "dalala_rida": ["none", "weak", "strong"], "musamaha_basis": [False, True]}
def run_core(store):
    if not isinstance(store, FactStore):
        raise TypeError("contract: run_core accepts a FactStore only")
    conflicts = [f for f in CORE_REQUIRED if store.effective(f)[0] == "CONFLICT"]
    if conflicts:
        return {"verdict": "STOP", "stop_id": "STOP-T8-CORE-FACTS-CONFLICT", "conflict_facts": conflicts}
    unknowns = [f for f in CORE_REQUIRED if store.effective(f)[0] is None]
    if unknowns:
        return {"verdict": "STOP", "stop_id": "STOP-T6-CORE-FACTS-UNKNOWN", "unknown_facts": unknowns}
    base = store.plain()
    unsupported = [f for f in OPTIONAL_DOMAINS if f in base and base[f] not in OPTIONAL_DOMAINS[f]]
    if unsupported:
        return {"verdict": "STOP", "stop_id": "STOP-T8-UNSUPPORTED-FACT-DOMAIN", "facts": unsupported}
    # An entry is not an established fact: hypotheses and conflicting
    # evidence must be enumerated as unknowns, never defaulted to "none".
    unresolved_conflicts = [f for f in OPTIONAL_DOMAINS if store.effective(f)[0] == "CONFLICT"]
    absent = [f for f in OPTIONAL_DOMAINS if store.effective(f)[0] is None or f in unresolved_conflicts]
    if not absent:
        return engine2_1.run21(base)
    results, slot_sets = {}, {}
    for combo in itertools.product(*[OPTIONAL_DOMAINS[f] for f in absent]):
        facts = dict(base); facts.update(dict(zip(absent, combo)))
        out = engine2_1.run21(facts)
        results[combo] = out["verdict"]
        slot_sets[combo] = json.dumps(out["slots"], sort_keys=True, default=str)
    verdicts = set(results.values())
    if len(verdicts) == 1:
        rep = next(iter(results))
        facts = dict(base); facts.update(dict(zip(absent, rep)))
        out = engine2_1.run21(facts)
        out["dependency"] = {"completions_checked": len(results),
                             "verdict_invariant_unknowns": absent,
                             "irrelevant_unknowns": absent,
                             "conflicting_unknowns": unresolved_conflicts,
                             "slot_variance_across_completions": len(set(slot_sets.values())) > 1}
        return out
    pivotal, slot_pivotal = [], []
    for i, f in enumerate(absent):
        groups, sgroups = {}, {}
        for combo, v in results.items():
            key = combo[:i] + combo[i + 1:]
            groups.setdefault(key, set()).add(v)
            sgroups.setdefault(key, set()).add(slot_sets[combo])
        if any(len(s) > 1 for s in groups.values()):
            pivotal.append(f)
        elif any(len(s) > 1 for s in sgroups.values()):
            slot_pivotal.append(f)
    return {"verdict": "UNDETERMINED_PIVOTAL", "stop_id": "STOP-T7-PIVOTAL-UNKNOWN",
            "pivotal_facts": pivotal, "slot_pivotal_facts": slot_pivotal,
            "conflicting_unknowns": unresolved_conflicts,
            "nonpivotal_unknowns": [f for f in absent if f not in pivotal and f not in slot_pivotal],
            "completions_checked": len(results)}

# ---------- test-3 module (fact-driven, unchanged semantics) ----------
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

# ---------- generic logic evaluator ----------
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
