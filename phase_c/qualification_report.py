# -*- coding: utf-8 -*-
"""Read-only Phase C qualification inventory and operator-contract validator.

Do NOT award A/B grades or promote rules from this report.
"""
import argparse
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def validate_catalog():
    data = json.loads((ROOT / "phase_c/operator_catalog.json").read_text(encoding="utf-8"))
    assert data["status"] == "DESIGN_ONLY_NOT_AUTHORITATIVE"
    allowed = {"evidence","dalala","sanad","ijma","urf","aql","conflict","practical_principle","other"}
    keys = set()
    for op in data["operators"]:
        assert op["key"] not in keys
        keys.add(op["key"])
        assert op["family"] in allowed
        assert isinstance(op["inputs"],list) and op["inputs"]
        assert isinstance(op["outputs"],list) and op["outputs"]
        assert isinstance(op["refuse_if"],list)
        assert not ({"fiqh_verdict", "historical_fatwa", "rule_approved"} & set(op["outputs"]))
    return len(keys)

def report(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT r.rule_key, s.stable_key, r.scientific_grade,
                             r.execution_layer, q.substantiated_components,
                             q.approving_reviewers, q.principle_witness_passages,
                             q.principle_independence_groups, q.open_objections
                       FROM fiqh.rule_qualification_readiness q
                       JOIN fiqh.method_rules r ON r.id=q.rule_id
                       JOIN fiqh.methodology_profiles p ON p.id=r.profile_id
                       JOIN fiqh.scholars s ON s.id=p.scholar_id
                       ORDER BY s.stable_key, r.rule_key""")
        records = []
        for row in cur.fetchall():
            key,scholar,grade,layer,parts,reviewers,witnesses,groups,objections=row
            records.append({
                "rule_key": key, "scholar":scholar,"grade":grade,"current_layer":layer,
                "accepted_components":parts,"approval_count":reviewers,
                "principle_witnesses":witnesses,
                "claimed_independent_groups":groups,
                "unresolved_objections":objections,
                "qualification_status":"ALREADY_HISTORICAL_REQUIRES_HUMAN_AUDIT" if layer=="historical" else "NOT_QUALIFIED"
            })
    return {"scientific_scope":"TECHNICAL_ADMISSION_INVENTORY_ONLY",
            "does_not_prove_probative_authority":True,
            "candidate_count":len(records),
            "historical_count":sum(r["current_layer"]=="historical" for r in records),
            "neutral_operators_registered":validate_catalog(),
            "rules":records}

if __name__=="__main__":
    import psycopg
    ap=argparse.ArgumentParser()
    ap.add_argument("--database-url",default=os.getenv("DATABASE_URL"),required=False)
    ap.add_argument("--assert-baseline",action="store_true")
    args=ap.parse_args()
    if not args.database_url:
        ap.error("DATABASE_URL is required")
    with psycopg.connect(args.database_url) as conn:
        result=report(conn)
    if args.assert_baseline:
        assert result["candidate_count"]==13, "Phase B candidates missing or additional rules introduced"
        assert result["historical_count"]==0, "Unexpected promotion of unreviewed historical rule"
        assert all(r["accepted_components"]==0 for r in result["rules"]), "Unexpected reviewed component"
    print(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True))
