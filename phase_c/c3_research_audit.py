# -*- coding: utf-8 -*-
"""Fail-closed integration of Muse C3 research with C1/C2 technical contracts.

A normalized match in a BOOK is NOT necessarily a match to the *same C1 P-ID*.
Never infer approval, original quotation truth or admissible rules from labels.
No database mutations, no engine calls, and no independent-blind answer key.
"""
import argparse
import hashlib
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
C1 = ROOT / "research/phase-c-ansari-general-operators"
C3 = ROOT / "research/phase-c-final-ansari-qualification"
C2 = ROOT / "phase_c"
PARTS = ("scope","activation","defeaters","exceptions","conflict_policy","principle")
AUDIT_STATES = {"CONFIRMED_AS_TEXT","CONTEXT_LIMITED","NOT_VERIFIED",
                "MISATTRIBUTED","CONTRADICTED","INSUFFICIENT"}
C3_STATUSES = {"DIRECTLY_SUPPORTED","INFERENTIALLY_SUPPORTED","PARTIAL",
               "UNKNOWN","CONTRADICTED","UNSUPPORTED","NOT_VERIFIED"}

def get_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(ok,message):
    if not ok:
        raise ValueError("Phase C3 research integrity: "+message)

def norm(s):
    s=unicodedata.normalize("NFKC",s)
    s=s.replace("ي","ی").replace("ك","ک").replace("ۀ","ه")
    return "".join(ch for ch in s if unicodedata.category(ch)[0] in ("L","N")
                   and unicodedata.category(ch)!="Mn")

def source_blocks(path,prefix):
    contents=path.read_text(encoding="utf-8")
    expr=rf"^## ({re.escape(prefix)}-\d{{2}})\s*[—-]\s*.*$"
    markers=list(re.finditer(expr,contents,re.MULTILINE))
    check(bool(markers),"no source blocks in "+str(path))
    return {m.group(1):contents[m.start():markers[i+1].start() if i+1<len(markers) else len(contents)]
            for i,m in enumerate(markers)}

def alignment(ref,blocks,anchor_map,audit_map=None):
    """Untrusted automated textual crosswalk, not scholarly verification."""
    canonical=ref.rstrip("*")
    base="P-15" if canonical.startswith("P-15") else canonical
    reasons=[]
    raw=blocks.get(base) or blocks.get(canonical)
    anchor=anchor_map.get(canonical)
    if raw is None: reasons.append("MISSING_ORIGINAL_SOURCE_BLOCK")
    if anchor is None: reasons.append("MISSING_VERIFICATION_ANCHOR")
    if anchor is not None:
        if anchor.get("found_normalized") is not True:
            reasons.append("ANCHOR_NOT_MATCHED_IN_BOOK_CORPUS")
        if raw is not None and norm(anchor.get("anchor","")) not in norm(raw):
            reasons.append("ID_DRIFT_OR_QUOTE_MISMATCH")
    if audit_map is not None:
        claim=audit_map.get(canonical)
        if claim is None:
            reasons.append("MISSING_MUSE_AUDIT_ROW")
        elif claim not in AUDIT_STATES:
            raise ValueError("Unknown Muse audit value: "+str(claim))
        elif claim!="CONFIRMED_AS_TEXT":
            reasons.append("MUSE_AUDIT_"+claim)
    if ref.endswith("*"): reasons.append("RESEARCH_UNCERTAINTY_MARKER")
    if not reasons:
        status="ANCHOR_ALIGNS_WITH_RESEARCH_BLOCK_ONLY"
    else:
        status="QUARANTINED"
    return {
        "ref":ref,"canonical_ref":canonical,"status":status,
        "blocking_reasons":reasons,
        "book_text_independently_verified":False,
        "print_edition_verified":False,
        "human_scholarly_review":False,
        "not_a_probative_conclusion":True
    }

def build_review():
    v2_file=C3/"METHOD_RULE_CANDIDATES_V2.json"
    handoff_file=C3/"CHATGPT_HANDOFF.json"
    audit_file=C3/"C1_CRITICAL_AUDIT.json"
    log_file=C3/"SOURCE_VERIFICATION_LOG.json"
    c1_file=C1/"FARAID_PASSAGES.md"
    np_file=C3/"ADDITIONAL_SOURCE_PASSAGES.md"
    binding_file=C2/"c2_operator_bindings.json"
    overrides_file=C2/"c3_v2_binding_overrides.json"
    catalog_file=C2/"operator_catalog.json"

    v2=get_json(v2_file)
    handoff=get_json(handoff_file)
    audit=get_json(audit_file)
    log=get_json(log_file)
    bind=get_json(binding_file)
    overrides=get_json(overrides_file)
    catalog=get_json(catalog_file)

    check(len(v2["rules"])==10,"C3 must contain ten revised candidate proposals")
    check(len(handoff["rules"])==10,"C3 handoff must contain ten rule dossiers")
    check(len(set(x["rule_key"] for x in v2["rules"]))==10,"duplicated research rule key")
    check({x["rule_key"] for x in v2["rules"]}==
          {x["rule_key"] for x in handoff["rules"]},"handoff and v2 rule identity mismatch")
    check(len(set(x["claim_id"] for x in audit["claims"]))==24,"missing or duplicate C1 audit IDs")
    audit_map={x["claim_id"]:x["audited_rating"] for x in audit["claims"]}
    c1blocks=source_blocks(c1_file,"P")
    npblocks=source_blocks(np_file,"NP")
    check(len(c1blocks)==23 and len(npblocks)==11,"source block inventory changed")
    anchors=log["long_anchor_results"]
    routing={x["rule_key"]:x for x in bind["entries"]}
    for entry in overrides["replacements"]:
        check(entry["rule_key"] not in routing,"replacement overwrites a legacy binding")
        routing[entry["rule_key"]]=entry
    operators={x["key"] for x in catalog["operators"]}
    check(overrides["retired_in_v2"]["MR-ANS-AFTER-TASAQUT"].startswith("superseded"),
          "deprecated C2 identity silently changed")

    problems=[]
    evidence_index={}
    for ref in sorted(set(audit_map)|set(c1blocks)|set(npblocks)|set(anchors)):
        if ref.startswith("P-"):
            evidence_index[ref]=alignment(ref,c1blocks,anchors,audit_map)
        elif ref.startswith("NP-"):
            evidence_index[ref]=alignment(ref,npblocks,anchors)
    for ref,data in evidence_index.items():
        if data["blocking_reasons"]:
            problems.append({"scope":"evidence","id":ref,"issues":data["blocking_reasons"]})

    dossiers=[]
    for rule in v2["rules"]:
        key=rule["rule_key"]
        incoming=next(r for r in handoff["rules"] if r["rule_key"]==key)
        check(incoming["may_execute_in_historical_engine"] is False,
              key+" handoff incorrectly permits historical execution")
        check(rule["may_execute_in_historical_engine"] is False,
              key+" research incorrectly permits historical execution")
        check("HOLD" in str(rule["historical_admission"]) and
              "HOLD" in str(incoming["historical_admission"]),
              key+" history admission must remain HOLD")
        check(set(rule["components"])==set(PARTS),
              key+" missing required scientific components")
        check(key in routing,key+" has no technical operator binding")
        op=routing[key]["neutral_operator_key"]
        check(op==rule["neutral_operator_key"]==incoming["neutral_operator_key"],
              key+" operator routing conflicts with C2+overrides")
        check(op in operators,key+" refers to nonexistent technical operator")
        evidence=[]
        for ref in rule["primary_textual_backings"]:
            canonical=ref.rstrip("*")
            check(canonical in evidence_index,
                  key+" primary source reference missing from evidence index: "+ref)
            link=dict(evidence_index[canonical])
            if ref.endswith("*"):
                link["status"]="QUARANTINED"
                link["blocking_reasons"]=list(link["blocking_reasons"])+[
                    "RESEARCH_UNCERTAINTY_MARKER"]
            evidence.append(link)
        adverse=rule["adverse_or_limiting_evidence"]
        check(all(x.startswith(("CE-","OPP-")) for x in adverse),
              key+" adverse references wrongly stored as primary sources")
        if any(x["status"]=="QUARANTINED" for x in evidence):
            problems.append({"scope":"rule","id":key,"issues":["UNVERIFIED_OR_ID_DRIFT_PRIMARY_EVIDENCE"]})
        if any(value not in C3_STATUSES for value in rule["components"].values()):
            problems.append({"scope":"rule","id":key,"issues":["UNRECOGNIZED_RESEARCH_COMPONENT_GRADE"]})
        dossier={
            "rule_key":key,"neutral_operator_key":op,
            "research_grade_proposal_not_approved":rule["research_grade_proposal"],
            "source_pointers":evidence,
            "adverse_or_limiting_evidence_refs":adverse,
            "previously_exposed_development_evidence":rule["previously_exposed_development_evidence"],
            "six_part_research_statuses":rule["components"],
            "proof_questions_not_fact_claims":routing[key]["proof_questions"],
            "scholar_stable_key":"murtada-ansari",
            "scientific_admission":"HOLD_FOR_INDEPENDENT_HUMAN_SCHOLARLY_REVIEW",
            "execution_allowed":False,"auto_grade_allowed":False,
            "quote_verification_required":True,
            "source_crosswalk_independent_confirmation":False,
            "human_review_required":True,
            "juristic_verdict":None,
        }
        dossiers.append(dossier)

    # A positive normalized substring match is not equivalent to verifying C1 ID.
    for ref in ("P-04","P-17"):
        check("ID_DRIFT_OR_QUOTE_MISMATCH" in evidence_index[ref]["blocking_reasons"],
              "Known C1-vs-audit source-ID drift unexpectedly disappeared: "+ref)
    check(all(not r["execution_allowed"] for r in dossiers),"rules unexpectedly executable")

    files=[v2_file,handoff_file,audit_file,log_file,c1_file,np_file,binding_file,
           overrides_file,catalog_file]
    return {
        "schema_version":"phase-c3-conservative-review-v1",
        "input_sha256":{p.relative_to(ROOT).as_posix():sha256(p) for p in files},
        "review_type":"TECHNICAL_CROSSWALK_AND_REVIEW_GATE_ONLY",
        "source_audit_rows":len(audit_map),"candidate_rules":len(dossiers),
        "crosswalk_source_count":len(evidence_index),
        "audit_quarantined_source_count":sum(x["status"]=="QUARANTINED" for x in evidence_index.values()),
        "scientifically_qualified_rules":0,"historical_admissions":0,
        "risk_findings":problems,
        "source_verification_index":evidence_index,
        "method_rules":dossiers,
        "warning":"DO NOT USE AS HISTORICAL RULESET. Source ID drift and corpus-vs-ID matching require a separately verified passage-level crosswalk and independent scholarly adjudication. A positive text match alone is NOT sufficient."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=pathlib.Path)
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    review=build_review()
    if args.check:
        check(len(review["method_rules"])==10,"candidate count drift")
        check(review["historical_admissions"]==0,"historical rule promoted")
        check(review["audit_quarantined_source_count"]>0,"the known bad crosswalk passed")
    if args.output:
        args.output.write_text(json.dumps(review,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
                               encoding="utf-8")
    print(json.dumps({
        "candidate_rules":review["candidate_rules"],
        "quarantined_source_ids":review["audit_quarantined_source_count"],
        "scientifically_qualified_rules":0,"historical_admissions":0,
        "status":"RESEARCH_REVIEW_GATE_ONLY_NOT_EXECUTABLE"
    },ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
