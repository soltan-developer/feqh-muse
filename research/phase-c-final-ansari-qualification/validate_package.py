#!/usr/bin/env python3
"""Structural validation ONLY — says nothing about juristic correctness."""
import json, pathlib, sys
root = pathlib.Path(__file__).parent
errors, notes = [], []
required = ["00_EXECUTION_MANIFEST.md","C1_CRITICAL_AUDIT.md","C1_CRITICAL_AUDIT.json","SOURCE_REGISTRY_AUDIT.md",
 "EDITION_PAGE_CROSSWALK.md","SOURCE_VERIFICATION_LOG.json","ADDITIONAL_SOURCE_PASSAGES.md","ADDITIONAL_SOURCE_PASSAGES.json",
 "REASONING_EVENTS_EXTENDED.md","REASONING_EVENTS_EXTENDED.json","OPEN_QUESTIONS_REASSESSMENT.md",
 "ALTERNATIVE_INTERPRETATIONS.md","INTERNAL_TENSIONS_GRAPH.json","RULE_REVISION_DECISIONS.md","SIX_COMPONENTS_MATRIX.md",
 "COUNTEREVIDENCE_AUDIT.md","EVIDENCE_INDEPENDENCE_MATRIX.md","METHOD_RULE_CANDIDATES_V2.json","HUMAN_REVIEW_PACKET.md",
 "HUMAN_REVIEW_FORM_TEMPLATE.md","CHATGPT_HANDOFF.json","C2_COMPATIBILITY_DELTAS.md",
 "INDEPENDENT_TRANSFER_EVALUATION_PROTOCOL.md","BLIND_TEST_SEPARATION_CHECKLIST.md","SOURCE_COVERAGE_FINAL.md"]
for f in required:
    if not (root/f).exists(): errors.append(f"missing file: {f}")
for f in root.rglob("*.json"):
    try: json.loads(f.read_text(encoding="utf-8"))
    except Exception as e: errors.append(f"JSON parse fail {f.name}: {e}")
v2 = json.loads((root/"METHOD_RULE_CANDIDATES_V2.json").read_text(encoding="utf-8"))
keys = [r["rule_key"] for r in v2["rules"]]
dossiers = sorted(p.stem for p in (root/"RULE_DOSSIERS").glob("*.md"))
if sorted(keys) != dossiers: errors.append(f"dossier/rule mismatch: {sorted(keys)} vs {dossiers}")
ho = json.loads((root/"CHATGPT_HANDOFF.json").read_text(encoding="utf-8"))
if sorted(r["rule_key"] for r in ho["rules"]) != sorted(keys): errors.append("handoff keys mismatch")
for r in ho["rules"]:
    if r["may_execute_in_historical_engine"] is not False: errors.append(f"{r['rule_key']}: may_execute not false")
    if r["historical_admission"] != "HOLD_FOR_INDEPENDENT_HUMAN_SCHOLARLY_REVIEW": errors.append(f"{r['rule_key']}: admission status wrong")
known = {f"P-{i:02d}" for i in range(1,24)} | {"P-15a","P-15b"} | {f"NP-{i:02d}" for i in range(1,12)} | {f"CE-{i:02d}" for i in range(1,8)} | {"CE-NEW-01", "OPP-IN-TEXT-NP03"}
for r in v2["rules"]:
    for ref in r["primary_textual_backings"] + r["adverse_or_limiting_evidence"]:
        base = ref.rstrip("*")
        if base not in known: errors.append(f"{r['rule_key']}: unresolved ref {ref}")
audit = json.loads((root/"C1_CRITICAL_AUDIT.json").read_text(encoding="utf-8"))
notes.append(f"audit counts: {audit['counts']}")
notes.append(f"rules v2: {len(keys)}; dossiers: {len(dossiers)}")
form = (root/"HUMAN_REVIEW_FORM_TEMPLATE.md").read_text(encoding="utf-8")
if "تأیید / رد / نیازمند شاهد / محل نزاع" not in form: errors.append("review form verdict options missing")
print("ERRORS:", len(errors))
for e in errors: print(" -", e)
for n in notes: print("NOTE:", n)
sys.exit(1 if errors else 0)
