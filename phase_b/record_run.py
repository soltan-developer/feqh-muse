# -*- coding: utf-8 -*-
"""Explicit append-only recording of a fresh adapter safety-probe execution.

The adapter is read-only; this separate command writes a complete snapshot
to engine_runs.raw_output with a cryptographic hash. No fake fired-rule steps.
"""
import argparse
import hashlib
import json
import os

import psycopg
from psycopg.types.json import Jsonb
from phase_b.adapter import run


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str,
                      separators=(",", ":")).encode("utf-8")


def record(conn, issue, scholar, profile, scenario):
    with conn.transaction():
        result = run(conn, issue, scholar, profile, scenario, run_mode="safety_probe")
        ids = result.get("identifiers")
        if ids is None:
            # Identity mismatch must not be attributed to any existing case.
            raise ValueError("Request rejected before identifying a valid case/profile")
        with conn.cursor() as c:
            c.execute("""SELECT rs.id FROM fiqh.rule_sets rs
                         WHERE rs.profile_id=%s AND rs.engine_sha256=%s
                         AND rs.rule_manifest_sha256=%s""",
                      (ids["methodology_profile_id"], result.get("engine_sha256", ""),
                       result.get("rules_manifest_sha256", "")))
            found = c.fetchone()
            if found is None:
                # A deliberate out-of-domain STOP may omit hashes; resolve the
                # profile's frozen ruleset only for recording a refused execution.
                if result.get("stop_id") != "STOP-OUT-OF-DOMAIN":
                    raise ValueError("Missing locked ruleset; no audit record created")
                c.execute("SELECT id FROM fiqh.rule_sets WHERE profile_id=%s",
                          (ids["methodology_profile_id"],))
                found = c.fetchone()
                if found is None:
                    raise ValueError("No frozen ruleset for refusal audit")
            ruleset = found[0]
            state = ("out_of_domain" if result.get("stop_id") == "STOP-OUT-OF-DOMAIN"
                     else "stop" if result["verdict"] in ("STOP", "UNDETERMINED_PIVOTAL")
                     else "conditional")
            input_payload = {
                "identifiers": ids, "run_mode": "safety_probe",
                "issue_key": result["provenance"]["issue_key"],
                "scenario_key": result["provenance"]["scenario_key"],
            }
            c.execute("""INSERT INTO fiqh.engine_runs (
                         case_id,rule_set_id,run_mode,verdict_state,verdict,
                         input_sha256,output_sha256,raw_output,exit_code,finished_at
                         ) VALUES (%s,%s,'safety_probe',%s,%s,%s,%s,%s,0,now())
                         RETURNING id""",
                      (ids["scenario_id"], ruleset, state, result["verdict"],
                       hashlib.sha256(canonical(input_payload)).hexdigest(),
                       hashlib.sha256(canonical(result)).hexdigest(), Jsonb(result)))
            run_id = c.fetchone()[0]
            if result.get("stop_id"):
                c.execute("""INSERT INTO fiqh.run_steps
                             (run_id,ordinal,status,premises,trace)
                             VALUES (%s,1,'stopped',%s,%s)""",
                          (run_id, Jsonb([]),
                           Jsonb({"stop_id": result["stop_id"],
                                  "note": "Guard stop; no fiqh rule asserted as fired"})))
    return {"run_id": str(run_id), "verdict": result["verdict"],
            "stop_id": result.get("stop_id"), "verdict_state": state,
            "output_sha256": hashlib.sha256(canonical(result)).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--issue", default="khiyar.ghabn")
    p.add_argument("--scholar", default="murtada-ansari")
    p.add_argument("--profile", default="ansari-development")
    p.add_argument("--scenario", default="ghabn.t8.core.development")
    a = p.parse_args()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        out = record(conn, a.issue, a.scholar, a.profile, a.scenario)
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
