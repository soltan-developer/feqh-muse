# -*- coding: utf-8 -*-
"""Read-only contract adapter from the issue-centric DB to the locked engine.

No database-sourced claims are converted into verified_evidence by fiat.
In this pilot only Ansari's unapproved development rules may be run in a
clearly-labelled safety_probe, never in historical_reconstruction mode.
"""
import argparse
import hashlib
import json
import os
import pathlib
import sys

import psycopg

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine2"))
import engine_unified as legacy
from factstore import FactStore
from phase_b.pilot import digest, file_text


def _stop(reason, **extra):
    return {"verdict": "STOP", "stop_id": reason, "historical_attribution": None,
            "ansari_consistent_extension": None, "probative_validation": "UNVERIFIED",
            **extra}


def _manifest_hash():
    return digest("".join(digest(file_text(path)) for path in (
        "engine2/rules_v4.json", "engine2/rules_t3.json", "engine2/engine2_1.py"
    )))


def baseline_core(facts):
    """The existing locked core, without database integration (regression oracle)."""
    store = FactStore()
    for k, v in facts.items():
        store.assert_fact(k, v, "stated_premise", "phase-b:development-case")
    return legacy.run_core(store)


def run(conn, issue_id, scholar_id, methodology_profile_id, scenario_id,
        run_mode="safety_probe"):
    if run_mode not in ("safety_probe", "historical_reconstruction", "hypothetical_experiment"):
        raise ValueError("Unsupported execution mode")
    # Require all four identifiers to be mutually consistent BEFORE reading facts.
    with conn.cursor() as c:
        c.execute("""
            SELECT i.id,s.id,p.id,cs.id,i.stable_key,cs.stable_key,
                   p.profile_key,p.revision,p.status,cs.test_class,cs.fact_pattern
            FROM fiqh.issues i
            JOIN fiqh.cases cs ON cs.issue_id=i.id
            JOIN fiqh.methodology_profiles p ON true
            JOIN fiqh.scholars s ON s.id=p.scholar_id
            WHERE (i.id::text=%s OR i.stable_key=%s)
              AND (s.id::text=%s OR s.stable_key=%s)
              AND (p.id::text=%s OR p.profile_key=%s)
              AND (cs.id::text=%s OR cs.stable_key=%s)
        """, (issue_id, issue_id, scholar_id, scholar_id,
              methodology_profile_id, methodology_profile_id, scenario_id, scenario_id))
        found = c.fetchall()
        if len(found) != 1:
            return _stop("STOP-IDENTITY-OR-SCOPE-MISMATCH")
        issue, scholar, profile, case, issue_key, case_key, profile_key, revision, profile_status, test_class, scenario_meta = found[0]
        c.execute("SELECT stable_key FROM fiqh.scholars WHERE id=%s", (scholar,))
        scholar_key = c.fetchone()[0]
        ids = {"issue_id": str(issue), "scholar_id": str(scholar),
               "methodology_profile_id": str(profile), "scenario_id": str(case)}
        provenance = {"profile_key": profile_key, "profile_revision": revision,
                      "scenario_key": case_key, "issue_key": issue_key}
        # Do not silently enable synthetic scholars or new subjects.
        if scholar_key != "murtada-ansari":
            return _stop("STOP-INACTIVE-SCHOLAR", identifiers=ids, provenance=provenance)
        if issue_key != "khiyar.ghabn":
            return _stop("STOP-OUT-OF-DOMAIN", identifiers=ids, provenance=provenance,
                         detail="Current locked executable engine contains no certified Udhrah rule")
        if test_class != "development" or scenario_meta.get("development_only") is not True:
            return _stop("STOP-UNLICENSED-SCENARIO", identifiers=ids,
                         provenance=provenance)
        c.execute("""
            SELECT rs.id,rs.version_key,rs.engine_sha256,rs.rule_manifest_sha256
            FROM fiqh.rule_sets rs WHERE rs.profile_id=%s
        """, (profile,))
        sets = c.fetchall()
        if len(sets) != 1:
            return _stop("STOP-RULESET-NOT-FROZEN", identifiers=ids, provenance=provenance)
        rule_set, version, engine_sha, manifest_sha = sets[0]
        if engine_sha != digest(file_text("engine2/engine_unified.py")) or manifest_sha != _manifest_hash():
            return _stop("STOP-LOCKED-ENGINE-DRIFT", identifiers=ids, provenance=provenance)
        c.execute("""
            SELECT r.rule_key,r.execution_layer,r.reviewer_status,r.scope,r.scientific_grade
            FROM fiqh.rule_set_members m
            JOIN fiqh.method_rules r ON r.id=m.rule_id
            WHERE m.rule_set_id=%s AND r.profile_id=%s ORDER BY r.rule_key
        """, (rule_set, profile))
        rules = c.fetchall()
        if not any(r[0] == "ENGINE2-CORE-LEGACY" for r in rules):
            return _stop("STOP-CORE-RULE-NOT-IN-RULESET", identifiers=ids, provenance=provenance)
        if any(r[3].get("issue_key") != issue_key for r in rules):
            return _stop("STOP-RULE-SCOPE-MISMATCH", identifiers=ids, provenance=provenance)
        if run_mode != "safety_probe":
            if profile_status != "reviewed" or any(
                r[1] != "historical" or r[2] != "approved" or r[4] not in ("A", "B")
                for r in rules
            ):
                return _stop("STOP-UNAPPROVED-METHODOLOGY", identifiers=ids,
                             provenance=provenance, run_mode=run_mode)
            # No historical execution until independent probative qualification.
            return _stop("STOP-HISTORICAL-EXECUTION-NOT-QUALIFIED", identifiers=ids,
                         provenance=provenance)
        c.execute("""
            SELECT fact_key,value,origin,evidence_status,provenance_passage_id
            FROM fiqh.case_facts WHERE case_id=%s ORDER BY fact_key,id
        """, (case,))
        rows = c.fetchall()
        c.execute("""
            SELECT proposition,epistemic_status
            FROM fiqh.claims WHERE issue_id=%s AND epistemic_status<>'supported'
            ORDER BY proposition
        """, (issue,))
        open_claims = [{"proposition": r[0], "status": r[1]} for r in c.fetchall()]
    factstore = FactStore()
    fact_trace = []
    for name, value, origin, state, source in rows:
        # The only allowed executable facts are explicit development scenario premises.
        # Even an accepted quote is not a certified probative proposition.
        if origin == "stated_premise":
            factstore.assert_fact(name, value, "stated_premise", case_key)
            admission = "DEVELOPMENT_SCENARIO_PREMISE"
        else:
            factstore.assert_fact(name, value, "unverified_hypothesis", str(source or case_key))
            admission = "INERT_UNVERIFIED"
        fact_trace.append({"key": name, "origin": origin, "admission": admission,
                           "evidence_status": state, "source_passage_id": str(source) if source else None})
    verdict = legacy.run_core(factstore)
    output = {
        "run_mode": run_mode, "scientific_status": "DEVELOPMENT_ONLY_NOT_A_FATWA",
        "identifiers": ids, "provenance": provenance,
        "ruleset_version": version, "engine_sha256": engine_sha,
        "rules_manifest_sha256": manifest_sha,
        "registered_rules": [r[0] for r in rules],
        "rule_execution_note": "The legacy core is opaque; per-rule trace is NOT fabricated",
        "facts": fact_trace, "engine_output": verdict,
        "verdict": verdict["verdict"], "stop_id": verdict.get("stop_id"),
        "open_nodes": open_claims,
        "historical_attribution": None, "ansari_consistent_extension": None,
        "probative_validation": "UNVERIFIED",
    }
    output["trace_sha256"] = hashlib.sha256(
        json.dumps(output, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--issue", default="khiyar.ghabn")
    ap.add_argument("--scholar", default="murtada-ansari")
    ap.add_argument("--profile", default="ansari-development")
    ap.add_argument("--scenario", default="ghabn.t8.core.development")
    ap.add_argument("--mode", default="safety_probe",
                    choices=["safety_probe", "historical_reconstruction", "hypothetical_experiment"])
    args = ap.parse_args()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            result = run(conn, args.issue, args.scholar, args.profile, args.scenario, args.mode)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
