# -*- coding: utf-8 -*-
"""Lossless, conservative PostgreSQL pilot importer. No engine2 mutations.

Requires psycopg>=3. This is a NEW database seed; it does not upgrade an
existing manually curated production corpus. All imports run in one transaction.
"""
import hashlib
import json
import pathlib
import re
import sys
import uuid

import psycopg
from psycopg.types.json import Jsonb

ROOT = pathlib.Path(__file__).resolve().parents[1]
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://github.com/soltan-developer/feqh-muse/phase-b")
SCHOLAR = "murtada-ansari"
SOURCES = [
    ("ghabn", "makasib", "corpus-makasib-v5", "ghabn-case/source_makaseb_v5_ghabn.md"),
    ("ghabn", "rasail_fiqhiya", "corpus-rasail-ladarar", "ghabn-case/source_rasail_ladarar.md"),
    ("udhrah", "makasib", "corpus-makasib-v1", "pilot/bay-udhrah/source_makaseb_v1_udhrah.md"),
]
EVENTS = [
    ("ghabn", "A", "ghabn-case/coding_A.md", r"(?m)^### رخداد\s+([0-9۰-۹]+)\b[^\n]*$"),
    ("ghabn", "B", "ghabn-case/coding_B.md", r"(?m)^### رخداد\s+([0-9۰-۹]+)\b[^\n]*$"),
    ("udhrah", "U", "pilot/bay-udhrah/coding_udhrah_events.md", r"(?m)^## رخداد\s+(U[0-9]+)\b[^\n]*$"),
]
GRAPHS = [
    ("ghabn", "ghabn-case/GRAPH_V2.json"),
    ("udhrah", "pilot/bay-udhrah/GRAPH_UDHRAH_DOC.json"),
]
DEV_FACTS = {
    "txn": "sulh", "ground_active": ["la_darar"],
    "extension_ground": "la_darar", "jahl": True,
    "fahish": True, "iqdam_alim": False,
    "alienation": "none", "maghbun_refusal": False,
    "ghurd_ayn": "absent", "dalala_rida": "none",
    "musamaha_basis": False
}
PERSIAN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def uid(kind, key):
    return uuid.uuid5(NS, kind + ":" + key)


def digest(s):
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def file_text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def jsonarg(v):
    return Jsonb(v) if isinstance(v, (dict, list)) else v


def frozen_insert(cur, table, key, fields):
    """Immutable idempotent upsert: same value is OK, any drift raises."""
    row = {"id": uid(table, key), **fields}
    cols = list(row)
    column_list = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    cur.execute(
        "INSERT INTO fiqh." + table + " (" + column_list + ") VALUES (" +
        placeholders + ") ON CONFLICT DO NOTHING",
        [jsonarg(row[c]) for c in cols]
    )
    cur.execute(
        "SELECT " + column_list + " FROM fiqh." + table + " WHERE id=%s",
        [row["id"]]
    )
    existing = cur.fetchone()
    if existing is None or any(existing[i] != row[c] for i, c in enumerate(cols)):
        raise ValueError("Immutable pilot row drift: " + table + "/" + key)
    return row["id"]


def pages(source):
    """Never turn project DB page markers into verified print pagination."""
    markers = list(re.finditer(r"(?m)^===== ص\s*(\d+)\s*=====\s*$", source))
    if markers:
        for i, m in enumerate(markers):
            value = source[m.end():markers[i + 1].start() if i + 1 < len(markers) else len(source)]
            if value.strip():
                yield ("db-page-" + m.group(1), value, m.group(1))
    else:
        markers = list(re.finditer(r"(?m)^## (?!متن منبع)([^\n]+)$", source))
        if markers:
            for i, m in enumerate(markers):
                value = source[m.start():markers[i + 1].start() if i + 1 < len(markers) else len(source)]
                if value.strip():
                    yield ("section-" + str(i + 1), value, None)
        else:
            yield ("whole-file", source, None)


def events(content, regex):
    hits = list(re.finditer(regex, content))
    for i, m in enumerate(hits):
        body = content[m.start():hits[i + 1].start() if i + 1 < len(hits) else len(content)]
        yield (m.group(1).translate(PERSIAN), body)


def numbered_parts(raw):
    """Extract only explicitly numbered U-event parts; missing parts stay unknown."""
    markers = list(re.finditer(r"(?<![\w\d])([۱-۹]|۱۰|۱۱|۱۲)(?:[–-]([۱-۹]|۱۰|۱۱|۱۲))?\s*[.٫]\s*", raw))
    out = {}
    for i, m in enumerate(markers):
        first = int(m.group(1).translate(PERSIAN))
        last = int(m.group(2).translate(PERSIAN)) if m.group(2) else first
        if not (1 <= first <= last <= 12):
            continue
        txt = raw[m.end():markers[i + 1].start() if i + 1 < len(markers) else len(raw)].strip()
        for n in range(first, last + 1):
            if n not in out:
                out[n] = {"verbatim": txt, "grouped_numbering": first != last}
    return out


def seed(conn):
    stats = {"issues": 2, "scholars": 1, "passages": 0, "events": {}, "evidence_nodes": {}, "rule_candidates": 0}
    with conn.transaction():
        with conn.cursor() as c:
            scholar = frozen_insert(c, "scholars", SCHOLAR, {
                "stable_key": SCHOLAR, "display_name": "شیخ مرتضی انصاری",
                "name_ar": "الشيخ مرتضى الأنصاري", "tradition": "Imami",
                "biographical_confidence": "unverified"
            })
            issue_ids = {}
            for key, stable, question in (
                ("ghabn", "khiyar.ghabn", "خیار غبن در معاملات و شرایط و آثار آن چیست؟"),
                ("udhrah", "sale.adhrah", "حکم بیع عذره با اختلاف ادله و فروض موضوع چیست؟")
            ):
                issue_ids[key] = frozen_insert(c, "issues", stable, {
                    "stable_key": stable, "canonical_question": question,
                    "question_language": "fa", "status": "draft"
                })
            # Multi-topic membership is part of the stable technical contract.
            for key, name, kind in [
                ("muamalat", "معاملات", "bab"),
                ("khiyarat", "خیارات", "subbab"),
                ("makasib_muharrama", "مکاسب محرمه", "subbab"),
                ("bay", "بیع", "bab")
            ]:
                frozen_insert(c, "topics", key, {"stable_key": key, "name": name, "kind": kind})
            for issue, topics in [("ghabn", ["muamalat", "khiyarat"]), ("udhrah", ["muamalat", "bay", "makasib_muharrama"])]:
                for key in topics:
                    c.execute("INSERT INTO fiqh.issue_topics (issue_id,topic_id) SELECT %s,id FROM fiqh.topics WHERE stable_key=%s ON CONFLICT DO NOTHING", (issue_ids[issue], key))
            works = {}
            for key, title in [("makasib", "المكاسب"), ("rasail_fiqhiya", "رسائل فقهية"), ("faraid", "فرائد الأصول")]:
                works[key] = frozen_insert(c, "works", key, {
                    "stable_key": key, "title": title, "work_kind": "original",
                    "original_language": "ar", "metadata": {"bibliographic_edition": "not_verified_in_pilot"}
                })
                c.execute("INSERT INTO fiqh.work_contributors (work_id,scholar_id,role,attribution_status) VALUES (%s,%s,'author','unverified') ON CONFLICT DO NOTHING", (works[key], scholar))
            edition_ids = {}
            source_pages = {}
            for issue, work, ed, rel in SOURCES:
                edition = frozen_insert(c, "editions", ed, {
                    "work_id": works[work], "edition_key": ed,
                    "corpus_identifier": rel,
                    "edition_metadata": {"print_edition_unverified": True, "repository_file_sha256": digest(file_text(rel))}
                })
                edition_ids[ed] = edition
                for pagekey, exact, dbpage in pages(file_text(rel)):
                    key = ed + "/" + pagekey
                    passage = frozen_insert(c, "source_passages", key, {
                        "edition_id": edition, "passage_key": pagekey,
                        "database_locator": rel + ("#db-page-" + dbpage if dbpage else "#" + pagekey),
                        "exact_text": exact, "language": "ar", "text_sha256": digest(exact),
                        "capture_status": "unverified"
                    })
                    if dbpage:
                        source_pages[(issue, dbpage)] = passage
                    stats["passages"] += 1
            profile = frozen_insert(c, "methodology_profiles", "ansari-dev-v1", {
                "scholar_id": scholar, "profile_key": "ansari-development",
                "revision": 1, "status": "hypothesis"
            })
            # Distinct snapshots of the two independent Ghabn codings and the 12 U-events.
            for issue, label, rel, expr in EVENTS:
                raw = file_text(rel)
                count = 0
                for seq, body in events(raw, expr):
                    eventkey = (label + "-" + seq).upper()
                    match = re.search(r"ص\s*([0-9۰-۹]+)", body[:180])
                    dbpage = match.group(1).translate(PERSIAN) if match else None
                    source_passage = source_pages.get((issue, dbpage)) if dbpage else None
                    eid = frozen_insert(c, "reasoning_events", issue + "/" + eventkey, {
                        "issue_id": issue_ids[issue], "scholar_id": scholar,
                        "work_id": works["makasib"], "event_key": eventkey,
                        "event_kind": "research_coding_" + label,
                        "epistemic_layer": "interpretation", "status": "draft",
                        "source_passage_id": source_passage
                    })
                    slots = numbered_parts(body) if label == "U" else {}
                    for slot in range(1, 13):
                        content = slots.get(slot) or {
                            "status": "not_separately_verified",
                            "raw_event": body if slot == 1 else None,
                            "raw_event_sha256": digest(body),
                            "coding_source": rel
                        }
                        # Code normalization is not scientific confirmation.
                        frozen_insert(c, "reasoning_parts", issue + "/" + eventkey + "/" + str(slot), {}) if False else None
                        c.execute("INSERT INTO fiqh.reasoning_parts (event_id,ordinal,content,assessment_status) VALUES (%s,%s,%s,'unverified') ON CONFLICT DO NOTHING", (eid, slot, Jsonb(content)))
                        c.execute("SELECT content FROM fiqh.reasoning_parts WHERE event_id=%s AND ordinal=%s", (eid, slot))
                        if c.fetchone()[0] != content:
                            raise ValueError("Event part drift: " + eventkey + "/" + str(slot))
                    count += 1
                if count == 0:
                    raise ValueError("No event sections parsed from " + rel)
                stats["events"][label] = count
            # Graph nodes are research assertions, NOT accredited legal evidence.
            for issue, rel in GRAPHS:
                graph = json.loads(file_text(rel))
                nodes = graph["nodes"]
                if isinstance(nodes, dict):
                    nodes = [{"id": k, **(v if isinstance(v, dict) else {"label": str(v)})} for k, v in nodes.items()]
                count = 0
                for node in nodes:
                    if not isinstance(node, dict) or not node.get("id"):
                        continue
                    stable = "pilot." + issue + "." + str(node["id"])
                    frozen_insert(c, "evidence_items", stable, {
                        "stable_key": stable, "category": "other",
                        "statement": str(node.get("label") or node.get("claim") or node["id"]),
                        "issue_id": issue_ids[issue], "provenance_note": rel,
                        "properties": {"research_graph_node": node, "source_sha256": digest(file_text(rel)), "probative_validation": "unverified"}
                    })
                    count += 1
                stats["evidence_nodes"][issue] = count
            # Keep key unresolved questions as explicit, non-attributed hypotheses.
            for issue, key in [
                ("ghabn", "IJ-SCOPE-BADHL"),
                ("ghabn", "IJ-KHIYAR-SCOPE-BADHL"),
                ("udhrah", "S-UDH-1"),
                ("udhrah", "S-UDH-2"),
                ("udhrah", "S-UDH-3")
            ]:
                frozen_insert(c, "claims", issue + "/" + key, {
                    "issue_id": issue_ids[issue], "proposition": "OPEN: " + key,
                    "claim_kind": "hypothesis", "epistemic_status": "unverified",
                    "is_historical_attribution": False
                })
            rules = {}
            for rel in ("engine2/rules_v4.json", "engine2/rules_t3.json"):
                for node in json.loads(file_text(rel))["nodes"]:
                    rule_id = node["rule_id"]
                    rules[rule_id] = frozen_insert(c, "method_rules", rule_id, {
                        "profile_id": profile, "rule_key": rule_id,
                        "principle": node.get("title", rule_id),
                        "rule_family": "legacy_ghabn",
                        "scope": {"issue_key": "khiyar.ghabn", "runtime": "safety_probe_only"},
                        "activation": {"conditions": node.get("conditions", [])},
                        "defeaters": {"status": "not_independently_qualified"},
                        "exceptions": {"status": "not_independently_qualified"},
                        "conflict_policy": {"status": "legacy_engine_locked"},
                        "scientific_grade": "C", "execution_layer": "hypothesis",
                        "reviewer_status": "pending", "version": 1
                    })
            core_id = "ENGINE2-CORE-LEGACY"
            rules[core_id] = frozen_insert(c, "method_rules", core_id, {
                "profile_id": profile, "rule_key": core_id,
                "principle": "Opaque locked engine2_1 core; no rule-by-rule proof claimed",
                "rule_family": "legacy_ghabn",
                "scope": {"issue_key": "khiyar.ghabn", "runtime": "safety_probe_only"},
                "activation": {"conditions": "engine2_1 locked"},
                "defeaters": {"status": "not_independently_qualified"},
                "exceptions": {"status": "not_independently_qualified"},
                "conflict_policy": {"status": "legacy_engine_locked"},
                "scientific_grade": "C", "execution_layer": "hypothesis",
                "reviewer_status": "pending", "version": 1
            })
            stats["rule_candidates"] = len(rules)
            manifest = digest("".join(digest(file_text(r)) for r in (
                "engine2/rules_v4.json", "engine2/rules_t3.json", "engine2/engine2_1.py"
            )))
            ruleset = frozen_insert(c, "rule_sets", "ansari-dev-v1", {
                "profile_id": profile, "version_key": "locked-engine2-dev-v1",
                "engine_sha256": digest(file_text("engine2/engine_unified.py")),
                "rule_manifest_sha256": manifest,
                "frozen_at": "2026-10-15T00:00:00+00:00"
            })
            for rule in rules.values():
                c.execute("INSERT INTO fiqh.rule_set_members (rule_set_id,rule_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (ruleset, rule))
            for issue, key, facts in [
                ("ghabn", "ghabn.t8.core.development", DEV_FACTS),
                ("udhrah", "udhrah.documentary.no-rule", {})
            ]:
                cid = frozen_insert(c, "cases", key, {
                    "issue_id": issue_ids[issue], "stable_key": key,
                    "fact_pattern": {"development_only": True, "provenance": "phase_b/pilot.py", "facts_not_historical": True}
                })
                for fact, value in facts.items():
                    frozen_insert(c, "case_facts", key + "/" + fact, {
                        "case_id": cid, "fact_key": fact, "value": value,
                        "origin": "stated_premise", "evidence_status": "unverified"
                    })
    return stats


def main():
    import os
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = seed(conn)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
