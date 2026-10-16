# -*- coding: utf-8 -*-
"""Standalone smoke/contract checks for the issue-centric multi-scholar model.

No network, app services, or existing engine imports required.
Run: python3 architecture/issue-centric-v1/test_schema.py
"""
import json
import pathlib
import sqlite3

HERE = pathlib.Path(__file__).resolve().parent
db = sqlite3.connect(":memory:")
db.execute("PRAGMA foreign_keys = ON")
db.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))

def insert(table, **values):
    keys = list(values)
    sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
    db.execute(sql, tuple(values.values()))

def row_count(table):
    return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

checks = 0
def verify(msg, condition):
    global checks
    checks += 1
    if not condition:
        raise AssertionError(msg)
    print(f"PASS {checks:02d}: {msg}")

def reject_integrity(msg, operation):
    try:
        operation()
    except sqlite3.IntegrityError:
        verify(msg, True)
    else:
        raise AssertionError(msg + " was incorrectly accepted")

for sid, name in [("ANSARI","شیخ مرتضی انصاری"), ("HILLI","علامه حلی")]:
    insert("scholar", id=sid, canonical_name=name, era="historical")
for wid, name, sid in [
    ("MAKASEB","کتاب المکاسب","ANSARI"),
    ("TAHRIR","تحریر الأحکام","HILLI")]:
    insert("work", id=wid, title=name)
    insert("work_contributor", work_id=wid, scholar_id=sid, role="author")
    insert("edition", id="ED-"+wid, work_id=wid, edition_label="test-reference-edition")
for sid, edition, quote in [
    ("SPAN-ANSARI","ED-MAKASEB","عبارت مستند آزمایشی مربوط به مسئله"),
    ("SPAN-HILLI","ED-TAHRIR","عبارت مستقل آزمایشی از عالم دوم")]:
    insert("text_span", id=sid, edition_id=edition,
           quote=quote, span_fingerprint=sid, page_locator="reference only")
insert("issue", id="ISSUE-SALE-WASTE",
       canonical_question="حکم بیع فضولات چیست؟",
       canonical_conditions_json="{}", canonical_facts_json="{}")
for tid, scheme, title in [
    ("TOPIC-KASB","makaseb","مکاسب محرمه"),
    ("TOPIC-CONTEMP","contemporary-economy","فقه اقتصاد و محیط زیست")]:
    insert("topic", id=tid, scheme=scheme, title=title)
    insert("issue_topic", issue_id="ISSUE-SALE-WASTE", topic_id=tid)

verify("one stable issue linked to two independent topic schemes",
       row_count("issue") == 1 and row_count("issue_topic") == 2)

insert("methodology_version", id="ANSARI-v1", scholar_id="ANSARI", version_label="v1")
insert("methodology_version", id="ANSARI-v2", scholar_id="ANSARI", version_label="v2")
insert("methodology_version", id="HILLI-v1", scholar_id="HILLI", version_label="v1")
verify("methodology versions are scholar-owned and historical versions persist",
       row_count("methodology_version") == 3)

for posid, scholar, version, span in [
    ("POS-A","ANSARI","ANSARI-v1","SPAN-ANSARI"),
    ("POS-H","HILLI","HILLI-v1","SPAN-HILLI")]:
    insert("scholar_position", id=posid, issue_id="ISSUE-SALE-WASTE",
           scholar_id=scholar, methodology_version_id=version,
           source_span_id=span, position_text="تمرینی؛ نه فتوای واقعی",
           position_role="research_example", attribution_kind="historical")
verify("two source-backed scholar positions for same issue remain independent",
       row_count("scholar_position") == 2)
reject_integrity("historical position without text span is blocked",
    lambda: insert("scholar_position", id="BAD-POS", issue_id="ISSUE-SALE-WASTE",
                   scholar_id="ANSARI", position_text="بدون مدرک",
                   position_role="adopted", attribution_kind="historical"))
reject_integrity("a position cannot use another scholar's methodology",
    lambda: insert("scholar_position", id="BAD-POS-2", issue_id="ISSUE-SALE-WASTE",
                   scholar_id="HILLI", methodology_version_id="ANSARI-v1",
                   source_span_id="SPAN-HILLI", position_text="ساختگی",
                   position_role="adopted", attribution_kind="historical"))

insert("evidence", id="EVID-1", evidence_type="hadith", summary="شاهد مشترکِ آزمایشی")
insert("evidence_span", evidence_id="EVID-1", span_id="SPAN-ANSARI", role="quotation")
for name, scholar, version, judgment, span in [
    ("ASSESS-A","ANSARI","ANSARI-v1","not_established","SPAN-ANSARI"),
    ("ASSESS-H","HILLI","HILLI-v1","established","SPAN-HILLI")]:
    insert("evidence_assessment", id=name, evidence_id="EVID-1",
           scholar_id=scholar, methodology_version_id=version,
           dimension="hujjiyya", judgment=judgment, source_span_id=span,
           review_status="approved")
verify("same evidence can receive distinct scholar-grounded assessments",
       row_count("evidence") == 1 and row_count("evidence_assessment") == 2)
reject_integrity("cross-scholar assessment profile rejected",
    lambda: insert("evidence_assessment", id="BAD-AS", evidence_id="EVID-1",
                  scholar_id="HILLI", methodology_version_id="ANSARI-v1",
                  dimension="hujjiyya", judgment="whatever"))
reject_integrity("approved evidence assessment cannot omit source span",
    lambda: insert("evidence_assessment", id="BAD-AS2", evidence_id="EVID-1",
                  scholar_id="ANSARI", methodology_version_id="ANSARI-v1",
                  dimension="hujjiyya", judgment="whatever",
                  review_status="approved"))

insert("method_rule", id="RULE-1", methodology_version_id="ANSARI-v1",
       scholar_id="ANSARI", title="مثال تمرینی غیرفقهی",
       evidence_grade="A", reviewer_id="human-reviewer", status="draft")
reject_integrity("rule cannot become approved before backing exists",
    lambda: db.execute("UPDATE method_rule SET status='approved' WHERE id='RULE-1'"))
insert("rule_backing", rule_id="RULE-1", span_id="SPAN-ANSARI",
       backing_component="scope", quotation_role="illustrative")
db.execute("UPDATE method_rule SET status='approved' WHERE id='RULE-1'")
verify("approval gate requires grade/reviewer and at least one textual backing",
       db.execute("SELECT status FROM method_rule WHERE id='RULE-1'").fetchone()[0] == "approved")
reject_integrity("cross-scholar method rule is rejected",
    lambda: insert("method_rule", id="BAD-R", methodology_version_id="ANSARI-v1",
                   scholar_id="HILLI", title="جعل انتساب"))

insert("issue_scenario", id="SC-1", issue_id="ISSUE-SALE-WASTE",
       title="فروض تست", context_json="{}")
for fid, state, value in [
    ("F-UNKNOWN","unknown",None),
    ("F-FALSE","stated","false"),
    ("F-CONFLICT","conflict",None)]:
    insert("scenario_fact", id=fid, scenario_id="SC-1",
           fact_key="same_field", value_json=value,
           epistemic_state=state)
verify("unknown, explicitly false and conflict are structurally different",
       len({r[0] for r in db.execute("SELECT epistemic_state FROM scenario_fact")}) == 3)
reject_integrity("verified facts require source span",
    lambda: insert("scenario_fact", id="F-FAKE", scenario_id="SC-1",
                    fact_key="fake", value_json="true", epistemic_state="verified"))

twelve_parts = (
    "issue_question", "subject_constraints", "juristic_question", "positions",
    "for_against_evidence", "hujjiyya_and_dalala", "objections_and_replies",
    "rejected_alternatives", "controlling_basis", "conclusion_and_grade",
    "precise_source", "cross_references"
)
event = {x: [] for x in twelve_parts}
event["issue_question"] = "تمرین مدل"
event["precise_source"] = "SPAN-ANSARI"
insert("reasoning_event", id="EV-1", issue_id="ISSUE-SALE-WASTE",
       scholar_id="ANSARI", work_id="MAKASEB", main_span_id="SPAN-ANSARI",
       event_kind="reasoning", event_payload_json=json.dumps(event, ensure_ascii=False))
stored = json.loads(db.execute("SELECT event_payload_json FROM reasoning_event WHERE id='EV-1'").fetchone()[0])
verify("12-part reasoning-event payload is preserved",
       set(twelve_parts) <= set(stored) and len(stored) == 12)
reject_integrity("historical reasoning without text span is rejected",
    lambda: insert("reasoning_event", id="BAD-EV", issue_id="ISSUE-SALE-WASTE",
                   scholar_id="HILLI", event_kind="reasoning",
                   event_payload_json="{}", attribution_kind="historical"))

insert("experiment", id="EXP-1", title="pilot", protocol_ref="ADR-001",
       engine_sha="demo", rules_sha="demo",
       methodology_version_id="ANSARI-v1", blind_level="development")
insert("experiment_case", id="EC-1", experiment_id="EXP-1",
       scenario_id="SC-1", public_packet_hash="placeholder")
insert("experiment_outcome", id="OUT-1", experiment_case_id="EC-1",
       result_origin="machine", verdict_state="STOP", result_json='{"reason":"unknown"}')
insert("experiment_outcome", id="OUT-2", experiment_case_id="EC-1",
       result_origin="human_judge", verdict_state="UNREVIEWED",
       result_json='{}')
verify("machine outcome and human judgment are stored separately",
       row_count("experiment_outcome") == 2)
verify("foreign-key referential integrity remains valid",
       db.execute("PRAGMA foreign_key_check").fetchall() == [])
print("SCHEMA CONTRACT PASS —",checks,"checks; tables =",
      db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
