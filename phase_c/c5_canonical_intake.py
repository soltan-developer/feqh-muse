# -*- coding: utf-8 -*-
"""Phase C5: fail-closed canonical research intake (NOT a juristic engine).

Checks C4's immutable, local canonical quotes/aliases/backings. A source corpus
verification is NEVER inferred from hashes supplied by the same research packet.
Independent full-book recheck is optional for review reports, but REQUIRED for
a 'CORPUS_VERIFIED' status. No path in this module authorizes historical rules.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sqlite3

ROOT=pathlib.Path(__file__).resolve().parents[1]
C4=ROOT/"research/phase-c4-canonical-evidence"
PARTS=("scope","activation","defeaters","exceptions","conflict_policy","principle")
IDENTITY=re.compile(r"^ANS-(\d+)-R(\d+)-S(\d+)$")

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def require(test, msg):
    if not test:
        raise ValueError("C5_INTAKE_REJECTED: "+msg)

def load_sources():
    files=["SOURCE_REGISTRY_LOCKED.json","CANONICAL_PASSAGE_REGISTRY.jsonl",
           "C1_C3_CANONICAL_CROSSWALK.json","RULE_COMPONENTS_V3.json",
           "PROVENANCE_GRAPH_EDGES.json","CHATGPT_HANDOFF_C4.json",
           "C3_BLOCKER_RESOLUTION_MATRIX.json"]
    data={}
    for name in files:
        path=C4/name
        data[name]=load_jsonl(path) if name.endswith(".jsonl") else load_json(path)
    return data, {f:hashlib.sha256((C4/f).read_bytes()).hexdigest() for f in files}

def validate(data):
    sources=data["SOURCE_REGISTRY_LOCKED.json"]
    register=data["CANONICAL_PASSAGE_REGISTRY.jsonl"]
    xwalk=data["C1_C3_CANONICAL_CROSSWALK.json"]
    rules=data["RULE_COMPONENTS_V3.json"]["rules"]
    edges=data["PROVENANCE_GRAPH_EDGES.json"]["edges"]
    handoff=data["CHATGPT_HANDOFF_C4.json"]
    blockers=data["C3_BLOCKER_RESOLUTION_MATRIX.json"]

    require(len(register)==34, "expected 34 raw passage entries")
    require(len(rules)==len(handoff["rules"])==10, "expected ten C4 dossiers")
    require(len(edges)==95, "expected 95 provenance edges")
    require(len(xwalk["rows"])==65, "expected 34 original and 31 legacy audit rows")
    require(sources["book_repo"]["commit"] and len(sources["book_repo"]["commit"])==40,
            "book corpus commit missing")
    bookset={str(b["book_id"]):b for b in sources["sources"]}
    require(len(bookset)==3 and all(b["edition_status"]=="PRINT_EDITION_UNKNOWN"
                                    and b["printed_page"] is None and b["edition_id"] is None
                                    for b in bookset.values()),"invented source edition")

    byid={}
    bylegacy={}
    for passage in register:
        cid=passage["canonical_id"]
        identity=IDENTITY.fullmatch(cid)
        require(identity is not None, "invalid canonical ID "+cid)
        require(cid not in byid, "duplicate canonical ID "+cid)
        require(identity.group(1)==str(passage["book_id"]) and
                int(identity.group(2))==passage["db_record_id"],
                "canonical ID points to another book or DB record: "+cid)
        require(str(passage["book_id"]) in bookset, "unregistered source book")
        segment=passage["raw_quote"]
        span=passage["quote_span"]
        require(bool(segment) and isinstance(span["start"],int) and
                isinstance(span["end"],int) and span["start"]>=0 and
                span["end"]-span["start"]==len(segment),
                "span length and quote length disagree: "+cid)
        require(sha(segment)==passage["raw_quote_sha256"],
                "tampered quoted text / SHA: "+cid)
        require(passage["print_edition"]=="PRINT_EDITION_UNKNOWN",
                "printed-edition certainty invented: "+cid)
        require(passage["match_class"]=="EXACT_TEXT_AND_ID_MATCH",
                "C4 claim is not raw canonical match: "+cid)
        require(len(passage["legacy_ids"])==1,"ambiguous source aliases: "+cid)
        legacy=passage["legacy_ids"][0]
        require(re.fullmatch(r"(?:P|NP)-\d{2}",legacy) is not None,
                "invalid P/NP original alias")
        require(legacy not in bylegacy,"source alias maps to multiple canonical passages")
        bylegacy[legacy]=cid
        byid[cid]=passage

    source_crosswalk=[row for row in xwalk["rows"]
                      if row.get("legacy_document") in (
                          "C1 FARAID_PASSAGES.md",
                          "Final package ADDITIONAL_SOURCE_PASSAGES.md")]
    require(len(source_crosswalk)==34,"missing exact legacy source crosswalk entries")
    require({r["legacy_id"] for r in source_crosswalk}==set(bylegacy),
            "crosswalk/source aliases differ")
    for row in source_crosswalk:
        ref=row["legacy_id"]
        require(row["match_class"]=="EXACT_TEXT_AND_ID_MATCH" and
                row["canonical_passage_id"]==bylegacy[ref],
                "legacy source alias was silently relabelled: "+ref)
        passage=byid[bylegacy[ref]]
        require(str(row["book_id"])==passage["book_id"] and
                row["db_record_id"]==passage["db_record_id"] and
                row["db_page"]==passage["db_page"],
                "crosswalk's record and page disagree: "+ref)

    rulekeys={r["rule_key"] for r in rules}
    require(len(rulekeys)==10 and
            rulekeys=={r["rule_key"] for r in handoff["rules"]},
            "rule set mismatch / duplicate")
    require("MR-ANS-AFTER-TASAQUT" not in rulekeys and
            {"MR-ANS-AFTER-TASAQUT-A","MR-ANS-AFTER-TASAQUT-B"}<=rulekeys,
            "split tasaqut must remain separate")
    require(handoff["human_review_state"]=="NOT_PERFORMED",
            "human reviewer result fabricated")
    require(handoff["blind_test_data"].startswith("NONE"),
            "unexpected blind-test content")

    positive=set()
    adverse=set()
    for rule in rules:
        key=rule["rule_key"]
        matching=next(r for r in handoff["rules"] if r["rule_key"]==key)
        require(rule["historical_admission"]=="HOLD_FOR_INDEPENDENT_HUMAN_SCHOLARLY_REVIEW"
                and rule["execution_allowed"] is False,
                "rule scholarly admission attempted: "+key)
        require(matching["historical_admission"]=="HOLD" and
                matching["execution_allowed"] is False,
                "handoff rule admission attempted: "+key)
        require(set(rule["components"])==set(PARTS) and
                set(matching["components"])==set(PARTS),
                "a methodological component missing: "+key)
        for part in PARTS:
            cell=rule["components"][part]
            mirror=matching["components"][part]
            require(cell["execution_allowed"] is False and
                    cell["historical_admission"]=="HOLD",
                    "component admission attempted: "+key+"."+part)
            pairs=list(zip(cell["legacy_refs"],cell["canonical_backings"]))
            require(len(pairs)==len(cell["legacy_refs"])==len(cell["canonical_backings"]),
                    "legacy/canonical pair count mismatch: "+key+"."+part)
            require(cell["canonical_backings"]==mirror["canonical_backings"],
                    "v3/handoff canonical backings disagree: "+key+"."+part)
            for old,new in pairs:
                require(old in bylegacy and new in byid and bylegacy[old]==new,
                        "unmapped or substituted backing: "+key+"."+part+"/"+old)
                positive.add((key+"."+part,old,new))
            for ref in cell.get("adverse_refs",[]):
                require(ref.startswith(("CE-","OPP-")) and ref not in bylegacy,
                        "opposing source used as an original positive quotation")
                adverse.add((key+"."+part,ref,None))
            require(mirror.get("adverse_refs",[])==cell.get("adverse_refs",[]),
                    "adverse basket changed in handoff")
        for new in rule.get("additional_canonical_backings",[]):
            require(new in byid, "additional backing has no canonical passage: "+new)

    seen_positive=set()
    seen_adverse=set()
    for edge in edges:
        origin=edge["from"]
        legacy=edge["legacy_ref"]
        canonical=edge.get("canonical_ref")
        if edge.get("basket")=="adverse":
            require(canonical is None and legacy.startswith(("CE-","OPP-")),
                    "adverse edge became positive")
            seen_adverse.add((origin,legacy,None))
        else:
            require(canonical in byid and bylegacy.get(legacy)==canonical,
                    "provenance edge has wrong identity: "+str(edge))
            if origin.endswith(".additional"):
                require(origin.split(".")[0] in rulekeys,
                        "unknown additional source rule")
            else:
                require((origin,legacy,canonical) in positive,
                        "graph edge not present in six-part component grid")
                seen_positive.add((origin,legacy,canonical))
    require(positive==seen_positive,"six-part evidence graph lost or added positive edges")
    require(adverse==seen_adverse,"contrary evidence graph lost or added adverse edges")

    require(blockers["summary"]=={
        "total_blockers_reconstructed":33,"resolved":28,"retired_or_open":5},
        "C3 historical blocker ledger altered")
    require(len(blockers["items"])==33,"C3 blocker record missing")
    return {"canonical_passages":len(register),
            "original_aliases":len(bylegacy),
            "six_part_cells":len(rules)*6,
            "graph_edges":len(edges),
            "positive_component_links":len(positive),
            "adverse_component_links":len(adverse),
            "c3_reconstructed_blockers":len(blockers["items"]),
            "scientifically_admitted_rules":0}

def verify_external_corpus(data,corpus_dir):
    """Check real decompressed SQLite database bytes when supplied explicitly.

    Do not treat same-packet raw quote hashes as independent book verification.
    """
    registry=data["CANONICAL_PASSAGE_REGISTRY.jsonl"]
    books={x["book_id"]:x for x in data["SOURCE_REGISTRY_LOCKED.json"]["sources"]}
    verified=0
    for book, meta in books.items():
        db=pathlib.Path(corpus_dir)/(book+".bin")
        require(db.is_file(),"explicit corpus missing: "+str(db))
        require(hashlib.sha256(db.read_bytes()).hexdigest()==meta["decompressed_file_sha256"],
                "decompressed book hash mismatch: "+book)
        connection=sqlite3.connect("file:"+str(db.resolve())+"?mode=ro",uri=True)
        try:
            for passage in (p for p in registry if p["book_id"]==book):
                rec=connection.execute(
                    "SELECT page_number, properties FROM page_contents WHERE id=?",
                    (passage["db_record_id"],)).fetchone()
                require(rec is not None,"DB row missing: "+passage["canonical_id"])
                txt=json.loads(rec[1]).get("Content") or ""
                span=passage["quote_span"]
                require(txt[span["start"]:span["end"]]==passage["raw_quote"],
                        "raw original quote mismatch: "+passage["canonical_id"])
                require(int(rec[0])==int(passage["db_page"]),
                        "database page mismatch: "+passage["canonical_id"])
                verified+=1
        finally:
            connection.close()
    require(verified==34,"not all canonical passages verified with original corpus")
    return verified

def build_intake(corpus_dir=None):
    data,digests=load_sources()
    checks=validate(data)
    if corpus_dir is None:
        verification="NOT_INDEPENDENTLY_RECHECKED_AGAINST_BOOK_FILES"
        verified=0
    else:
        verified=verify_external_corpus(data,corpus_dir)
        verification="CORPUS_SHA256_AND_RECORD_SPANS_RECHECKED_NOT_PRINT_EDITION"
    return {
        "schema_version":"phase-c5-canonical-research-intake-v1",
        "status":"REVIEW_ONLY_NOT_EXECUTABLE",
        "inputs_sha256":digests,
        "c4_corpus_commit":data["SOURCE_REGISTRY_LOCKED.json"]["book_repo"]["commit"],
        "source_verification":verification,
        "source_passages_checked_against_external_corpus":verified,
        "technical_structural_checks":checks,
        "legacy_blocker_disposition":"PRESERVED_IN_C3_BLOCKER_RESOLUTION_MATRIX",
        "human_scholarly_review":"NOT_PERFORMED",
        "print_edition_verification":"NOT_PERFORMED",
        "method_rule_historical_admissions":0,
        "method_rule_execution_allowed":False,
        "no_qualification_from_canonical_identity":True,
        "warning":"C4 self-consistency and optionally original DB-byte checks DO NOT establish scholarly authenticity, witness independence, or validity of legal reasoning."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--corpus-dir",type=pathlib.Path)
    p.add_argument("--output",type=pathlib.Path)
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    result=build_intake(args.corpus_dir)
    if args.check:
        require(result["method_rule_historical_admissions"]==0 and
                result["method_rule_execution_allowed"] is False,
                "non-admission violated")
    if args.output:
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
                               encoding="utf-8")
    print(json.dumps({"status":result["status"],
        "verification":result["source_verification"],
        **result["technical_structural_checks"],
        "historical_admissions":0},ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
