# -*- coding: utf-8 -*-
"""Phase C2: deterministic integrity check and FORMAL DESIGN compilation of Muse C1.

The output is NOT an executable juristic rule set; all entries explicitly fail
historical admission and remain untrusted research proposals.
Run: python -m phase_c.c2_compile --output /tmp/c2_packet.json
"""
import argparse
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
C1 = ROOT / "research/phase-c-ansari-general-operators"
C2 = ROOT / "phase_c"
PARTS = ("scope","activation","defeaters","exceptions","conflict_policy","principle")
STATES = {"supported","partial","unsupported"}

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def headings(path, regex):
    return set(re.findall(regex,path.read_text(encoding="utf-8"),flags=re.MULTILINE))

def require(condition,description):
    if not condition:
        raise ValueError("C2 integrity violation: "+description)

def build_packet():
    c1_file=C1/"OPERATOR_CANDIDATES.json"
    bind_file=C2/"c2_operator_bindings.json"
    catalog_file=C2/"operator_catalog.json"
    c1=read_json(c1_file)
    bindings=read_json(bind_file)
    neutral=read_json(catalog_file)
    sources=headings(C1/"FARAID_PASSAGES.md",r"^## (P-\d{2})\b")
    contraries=headings(C1/"CONTRARY_EVIDENCE.md",r"^## (CE-\d{2})\b")
    open_questions=headings(C1/"OPEN_QUESTIONS.md",r"^- \*\*(OQ-C1-\d{2})\b")
    events=headings(C1/"REASONING_EVENTS.md",r"^## (E-C1-\d{2})\b")
    keys={op["key"] for op in neutral["operators"]}

    require(c1["status"]=="RESEARCH_PROPOSAL_ONLY_NOT_QUALIFIED","C1 must remain unapproved")
    require(bindings["scientific_status"]=="UNQUALIFIED_DESIGN_ONLY","bindings must remain unqualified")
    require(neutral["status"]=="DESIGN_ONLY_NOT_AUTHORITATIVE","neutral catalog is not evidence")
    require(len(sources)==23 and len(contraries)==7 and len(open_questions)==7 and len(events)==10,
            "expected 23 source passages, 7 contrary cases, 7 open questions, 10 events")
    rules=c1["method_rules"]
    linked={x["rule_key"]:x for x in bindings["entries"]}
    require(len(rules)==len(linked)==9,"missing, duplicate or added candidates")
    require(len(set(x["key"] for x in rules))==9,"duplicate method rules")
    require({x["key"] for x in rules}==set(linked),"bindings must match all C1 rules")

    counter={"supported":0,"partial":0,"unsupported":0}
    problems=[]
    dossier=[]
    for rule in rules:
        key=rule["key"]
        binding=linked[key]
        require(binding["neutral_operator_key"] in keys,"unknown neutral operator "+key)
        require(binding["unknown_action"]=="STOP_UNVERIFIED","no fail-open allowed")
        require(binding["admission_policy"]=="NEVER_EXECUTE_UNTIL_INDEPENDENT_QUALIFICATION","bad admission policy")
        require(rule["preliminary_grade"] in ("A-CANDIDATE","B-CANDIDATE","C","D","X"),"unrecognized grade")
        require(set(rule["components"])==set(PARTS),"missing six components in "+key)
        require(binding["proof_questions"] and len(binding["proof_questions"])==len(set(binding["proof_questions"])),
                "proof questions incomplete or repeated for "+key)

        components={}
        blocking=[]
        for part in PARTS:
            source=rule["components"][part]
            status=source["status"]
            require(status in STATES,"bad research status for "+key+"/"+part)
            refs=source["evidence"]
            require(isinstance(refs,list),"evidence references must be list")
            for ref in refs:
                require(ref in sources or ref in contraries,"unknown source ID "+ref)
            primary=[ref for ref in refs if ref in sources]
            adverse=[ref for ref in refs if ref in contraries]
            counter[status]+=1
            if status!="supported":
                blocking.append(part+":"+status)
            if adverse:
                problems.append({"rule":key,"part":part,"problem":"CONTRARY_REFERENCE_NOT_PRIMARY_PROOF",
                                 "refs":adverse})
            if "P-23" in primary:
                problems.append({"rule":key,"part":part,"problem":"DEVELOPMENT_CASE_NOT_INDEPENDENT",
                                 "refs":["P-23"]})
            components[part]={
                "research_status":status,"original_source_ids":primary,
                "contrary_evidence_ids":adverse,"research_note":source["note"],
                "source_match_review":"NOT_PERFORMED",
                "independent_human_review":"NOT_PERFORMED",
                "independence_assessed":False
            }
        if rule["neutral_operator_key"] != binding["neutral_operator_key"]:
            problems.append({"rule":key,"problem":"C1_OPERATOR_ROUTING_REVISED",
                             "old":rule["neutral_operator_key"],
                             "new":binding["neutral_operator_key"]})
        for oq in binding["open_questions"]:
            require(oq in open_questions,"unknown open question "+oq)
        if blocking:
            problems.append({"rule":key,"problem":"INCOMPLETE_COMPONENTS","components":blocking})
        dossier.append({
            "rule_key":key,"scholar_stable_key":"murtada-ansari",
            "title":rule["title_fa"],
            "proposed_grade_not_admitted":rule["preliminary_grade"],
            "technical_operator":binding["neutral_operator_key"],
            "software_predicate_questions_NOT_FACTS":binding["proof_questions"],
            "unresolved_question_ids":binding["open_questions"],
            "blocking_note":binding["blocking_note"],
            "six_parts":components,
            "historical_admission":"HOLD",
            "reason":"No source-edition validation, independent human review or actual probative assessment",
            "may_execute_in_engine":False,
            "may_attribute_historical_verdict":False,
            "unknown_action":"STOP_UNVERIFIED"
        })
    require(counter=={"supported":46,"partial":7,"unsupported":1},
            "six-component count drift: "+repr(counter))
    return {
        "schema_version":"phase-c2-review-packet-v1",
        "research_branch_reference":"research/phase-c1-ansari-operators",
        "scientific_status":"UNQUALIFIED_FOR_HISTORICAL_EXECUTION",
        "catalog_operator_count":len(neutral["operators"]),
        "source_passage_count":len(sources),"event_count":len(events),
        "contrary_count":len(contraries),"open_question_count":len(open_questions),
        "research_component_counts":counter,
        "independent_verified_component_count":0,
        "historical_rule_admissions":0,
        "source_manifest_sha256":{
            "operator_candidates":digest(c1_file),
            "formal_bindings":digest(bind_file),
            "source_passages":digest(C1/"FARAID_PASSAGES.md"),
            "contrary_evidence":digest(C1/"CONTRARY_EVIDENCE.md"),
            "open_questions":digest(C1/"OPEN_QUESTIONS.md"),
            "reasoning_events":digest(C1/"REASONING_EVENTS.md"),
            "neutral_operator_catalog":digest(catalog_file)
        },
        "design_review_issues":problems,
        "method_rule_dossiers":dossier,
        "warning":"Technical normalization only; no independent corpus/text matching or expert review. No ruleset ready for execution."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=pathlib.Path)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    packet=build_packet()
    serialized=json.dumps(packet,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized,encoding="utf-8")
    if args.check:
        assert packet["historical_rule_admissions"]==0
        assert all(not x["may_execute_in_engine"] for x in packet["method_rule_dossiers"])
    print(json.dumps({
        "status":"C2_DESIGN_PACKET_VALIDATED_NOT_SCHOLARLY_APPROVED",
        "rules":len(packet["method_rule_dossiers"]),
        "components":packet["research_component_counts"],
        "open_issues":len(packet["design_review_issues"]),
        "independent_verified_components":0,
        "historical_admissions":0
    },ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
