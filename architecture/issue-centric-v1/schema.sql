-- Feqh-Muse ontology v1: SQLite reference schema, NOT a production migration.
-- Compatible with Python sqlite3 (PRAGMA foreign_keys=ON).
-- Scientific attribution/evidence validation additionally requires an admission service.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
  version TEXT PRIMARY KEY, description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_meta(version, description)
VALUES ('issue-multi-scholar-v1', 'Research reference schema, no engine-rule changes');

CREATE TABLE scholar (
  id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, era TEXT, school TEXT,
  life_start TEXT, life_end TEXT, biographical_note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE scholar_name (
  id TEXT PRIMARY KEY, scholar_id TEXT NOT NULL REFERENCES scholar(id),
  lang TEXT, script TEXT, display_name TEXT NOT NULL, source_span_id TEXT,
  UNIQUE(scholar_id, display_name, lang)
);
CREATE TABLE scholar_relation (
  id TEXT PRIMARY KEY, from_scholar_id TEXT NOT NULL REFERENCES scholar(id),
  to_scholar_id TEXT NOT NULL REFERENCES scholar(id),
  relation_kind TEXT NOT NULL, source_span_id TEXT, certainty TEXT NOT NULL DEFAULT 'unverified',
  CHECK(from_scholar_id <> to_scholar_id)
);

CREATE TABLE work (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, work_type TEXT NOT NULL DEFAULT 'book',
  composition_period TEXT, attribution_note TEXT, language TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE work_contributor (
  work_id TEXT NOT NULL REFERENCES work(id), scholar_id TEXT NOT NULL REFERENCES scholar(id),
  role TEXT NOT NULL, attribution_grade TEXT NOT NULL DEFAULT 'unreviewed',
  PRIMARY KEY(work_id, scholar_id, role)
);
CREATE TABLE edition (
  id TEXT PRIMARY KEY, work_id TEXT NOT NULL REFERENCES work(id), edition_label TEXT NOT NULL,
  publisher TEXT, year_label TEXT, corpus_file_id TEXT, source_url TEXT,
  content_manifest_hash TEXT, status TEXT NOT NULL DEFAULT 'unreviewed',
  UNIQUE(work_id, edition_label)
);
CREATE TABLE text_span (
  id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES edition(id),
  chapter_locator TEXT, volume_locator TEXT, page_locator TEXT,
  database_locator TEXT, start_offset INTEGER, end_offset INTEGER,
  quote TEXT NOT NULL CHECK(length(trim(quote)) > 0),
  quote_sha256 TEXT, span_fingerprint TEXT NOT NULL,
  is_editorial_note INTEGER NOT NULL DEFAULT 0 CHECK(is_editorial_note IN (0,1)),
  provenance_status TEXT NOT NULL DEFAULT 'unverified',
  UNIQUE(edition_id, span_fingerprint),
  CHECK(start_offset IS NULL OR start_offset >= 0),
  CHECK(end_offset IS NULL OR (start_offset IS NOT NULL AND end_offset >= start_offset))
);
CREATE TABLE text_variant (
  id TEXT PRIMARY KEY, span_id TEXT NOT NULL REFERENCES text_span(id),
  variant_edition_id TEXT REFERENCES edition(id), witness_label TEXT,
  variant_text TEXT NOT NULL, effect_note TEXT, review_status TEXT NOT NULL DEFAULT 'unreviewed'
);

CREATE TABLE topic (
  id TEXT PRIMARY KEY, scheme TEXT NOT NULL, title TEXT NOT NULL,
  era_scope TEXT, note TEXT, UNIQUE(scheme, title)
);
CREATE TABLE topic_relation (
  id TEXT PRIMARY KEY, from_topic_id TEXT NOT NULL REFERENCES topic(id),
  to_topic_id TEXT NOT NULL REFERENCES topic(id), relation_type TEXT NOT NULL,
  source_span_id TEXT REFERENCES text_span(id),
  CHECK(from_topic_id <> to_topic_id),
  UNIQUE(from_topic_id, to_topic_id, relation_type)
);
CREATE TABLE issue (
  id TEXT PRIMARY KEY, canonical_question TEXT NOT NULL,
  issue_kind TEXT, hukm_kind TEXT, subject_description TEXT,
  canonical_conditions_json TEXT NOT NULL DEFAULT '{}',
  canonical_facts_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'research', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE issue_topic (
  issue_id TEXT NOT NULL REFERENCES issue(id), topic_id TEXT NOT NULL REFERENCES topic(id),
  relation_type TEXT NOT NULL DEFAULT 'classified_under',
  evidence_span_id TEXT REFERENCES text_span(id),
  PRIMARY KEY(issue_id, topic_id, relation_type)
);
CREATE TABLE issue_relation (
  id TEXT PRIMARY KEY, from_issue_id TEXT NOT NULL REFERENCES issue(id),
  to_issue_id TEXT NOT NULL REFERENCES issue(id), relation_type TEXT NOT NULL,
  review_status TEXT NOT NULL DEFAULT 'proposed', source_span_id TEXT REFERENCES text_span(id),
  CHECK(from_issue_id <> to_issue_id)
);
CREATE TABLE issue_scenario (
  id TEXT PRIMARY KEY, issue_id TEXT NOT NULL REFERENCES issue(id),
  title TEXT NOT NULL, scenario_kind TEXT NOT NULL DEFAULT 'historical',
  context_json TEXT NOT NULL DEFAULT '{}', base_scenario_id TEXT REFERENCES issue_scenario(id),
  status TEXT NOT NULL DEFAULT 'draft'
);
CREATE TABLE scenario_fact (
  id TEXT PRIMARY KEY, scenario_id TEXT NOT NULL REFERENCES issue_scenario(id),
  fact_key TEXT NOT NULL, value_json TEXT,
  epistemic_state TEXT NOT NULL DEFAULT 'unknown'
    CHECK(epistemic_state IN ('stated','verified','derived','unknown','conflict','hypothesis')),
  source_span_id TEXT REFERENCES text_span(id), time_scope TEXT,
  assertion_origin TEXT, review_status TEXT NOT NULL DEFAULT 'unreviewed',
  CHECK (epistemic_state <> 'verified' OR source_span_id IS NOT NULL)
);

CREATE TABLE evidence (
  id TEXT PRIMARY KEY, evidence_type TEXT NOT NULL,
  canonical_ref TEXT, summary TEXT NOT NULL, canonical_subject TEXT,
  provenance_status TEXT NOT NULL DEFAULT 'unverified'
);
CREATE TABLE evidence_span (
  evidence_id TEXT NOT NULL REFERENCES evidence(id), span_id TEXT NOT NULL REFERENCES text_span(id),
  role TEXT NOT NULL, PRIMARY KEY(evidence_id, span_id, role)
);
CREATE TABLE methodology_version (
  id TEXT PRIMARY KEY, scholar_id TEXT NOT NULL REFERENCES scholar(id),
  version_label TEXT NOT NULL, date_from TEXT, date_to TEXT,
  basis_note TEXT, profile_manifest_hash TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft',
  UNIQUE(scholar_id, version_label)
);
CREATE TABLE evidence_assessment (
  id TEXT PRIMARY KEY, evidence_id TEXT NOT NULL REFERENCES evidence(id),
  scholar_id TEXT NOT NULL REFERENCES scholar(id),
  methodology_version_id TEXT NOT NULL REFERENCES methodology_version(id),
  dimension TEXT NOT NULL CHECK(dimension IN ('identity','transmission','dalala','issuance_context','hujjiyya','scope','weight','other')),
  judgment TEXT NOT NULL, rationale TEXT, source_span_id TEXT REFERENCES text_span(id),
  attribution_kind TEXT NOT NULL DEFAULT 'researcher_reconstruction',
  review_status TEXT NOT NULL DEFAULT 'unreviewed',
  CHECK(review_status <> 'approved' OR source_span_id IS NOT NULL)
);
CREATE TRIGGER evidence_assessment_scholar_guard
BEFORE INSERT ON evidence_assessment
BEGIN
  SELECT CASE WHEN (
    SELECT scholar_id FROM methodology_version WHERE id=NEW.methodology_version_id
  ) <> NEW.scholar_id THEN RAISE(ABORT, 'assessment methodology belongs to another scholar') END;
END;

CREATE TABLE scholar_position (
  id TEXT PRIMARY KEY, issue_id TEXT NOT NULL REFERENCES issue(id),
  scholar_id TEXT NOT NULL REFERENCES scholar(id),
  methodology_version_id TEXT REFERENCES methodology_version(id),
  source_span_id TEXT REFERENCES text_span(id),
  position_text TEXT NOT NULL, position_role TEXT NOT NULL,
  attribution_kind TEXT NOT NULL,
  strength_label TEXT NOT NULL DEFAULT 'unreviewed',
  effective_period TEXT, review_status TEXT NOT NULL DEFAULT 'unreviewed',
  CHECK(attribution_kind <> 'historical' OR source_span_id IS NOT NULL),
  CHECK(review_status <> 'approved' OR source_span_id IS NOT NULL)
);
CREATE TRIGGER scholar_position_methodology_guard
BEFORE INSERT ON scholar_position WHEN NEW.methodology_version_id IS NOT NULL
BEGIN
  SELECT CASE WHEN (
    SELECT scholar_id FROM methodology_version WHERE id=NEW.methodology_version_id
  ) <> NEW.scholar_id THEN RAISE(ABORT, 'position methodology belongs to another scholar') END;
END;

CREATE TABLE interpretation (
  id TEXT PRIMARY KEY, scholar_position_id TEXT REFERENCES scholar_position(id),
  source_span_id TEXT REFERENCES text_span(id),
  interpreter_scholar_id TEXT REFERENCES scholar(id), reading_text TEXT NOT NULL,
  reading_kind TEXT NOT NULL DEFAULT 'commentary',
  evidence_grade TEXT NOT NULL DEFAULT 'unreviewed',
  review_status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE method_rule (
  id TEXT PRIMARY KEY, methodology_version_id TEXT NOT NULL REFERENCES methodology_version(id),
  scholar_id TEXT NOT NULL REFERENCES scholar(id),
  title TEXT NOT NULL, issue_scope_json TEXT NOT NULL DEFAULT '{}',
  activation_json TEXT NOT NULL DEFAULT '{}', defeaters_json TEXT NOT NULL DEFAULT '[]',
  exceptions_json TEXT NOT NULL DEFAULT '[]', priority_relation_json TEXT NOT NULL DEFAULT '[]',
  effect_json TEXT NOT NULL DEFAULT '{}', counterexamples_json TEXT NOT NULL DEFAULT '[]',
  historical_version TEXT, evidence_grade TEXT NOT NULL DEFAULT 'X',
  status TEXT NOT NULL DEFAULT 'draft', reviewer_id TEXT,
  CHECK(status <> 'approved' OR (evidence_grade IN ('A','B') AND reviewer_id IS NOT NULL))
);
CREATE TABLE rule_backing (
  rule_id TEXT NOT NULL REFERENCES method_rule(id), span_id TEXT NOT NULL REFERENCES text_span(id),
  backing_component TEXT NOT NULL, quotation_role TEXT NOT NULL,
  PRIMARY KEY(rule_id,span_id,backing_component)
);
CREATE TRIGGER method_rule_scholar_guard
BEFORE INSERT ON method_rule
BEGIN
  SELECT CASE WHEN (
    SELECT scholar_id FROM methodology_version WHERE id=NEW.methodology_version_id
  ) <> NEW.scholar_id THEN RAISE(ABORT, 'method rule belongs to another scholar') END;
END;
CREATE TRIGGER method_rule_approval_requires_backing
BEFORE UPDATE OF status ON method_rule
WHEN NEW.status='approved'
BEGIN
  SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM rule_backing WHERE rule_id=NEW.id)
    THEN RAISE(ABORT, 'rule approval requires source backing') END;
END;

CREATE TABLE reasoning_event (
  id TEXT PRIMARY KEY, issue_id TEXT NOT NULL REFERENCES issue(id),
  scholar_id TEXT NOT NULL REFERENCES scholar(id), work_id TEXT REFERENCES work(id),
  main_span_id TEXT REFERENCES text_span(id),
  event_order INTEGER, event_kind TEXT NOT NULL,
  attribution_kind TEXT NOT NULL DEFAULT 'historical',
  event_payload_json TEXT NOT NULL,
  interpretation_grade TEXT NOT NULL DEFAULT 'unreviewed',
  review_status TEXT NOT NULL DEFAULT 'draft',
  CHECK(attribution_kind <> 'historical' OR main_span_id IS NOT NULL)
);
CREATE TABLE reasoning_event_evidence (
  event_id TEXT NOT NULL REFERENCES reasoning_event(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  role TEXT NOT NULL, assessment_id TEXT REFERENCES evidence_assessment(id),
  PRIMARY KEY(event_id,evidence_id,role)
);
CREATE TABLE argument_node (
  id TEXT PRIMARY KEY, issue_id TEXT NOT NULL REFERENCES issue(id),
  scholar_id TEXT REFERENCES scholar(id), event_id TEXT REFERENCES reasoning_event(id),
  node_kind TEXT NOT NULL, content TEXT NOT NULL,
  provenance_kind TEXT NOT NULL DEFAULT 'researcher_analysis',
  source_span_id TEXT REFERENCES text_span(id),
  node_state TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE argument_edge (
  id TEXT PRIMARY KEY, from_node_id TEXT NOT NULL REFERENCES argument_node(id),
  to_node_id TEXT NOT NULL REFERENCES argument_node(id),
  relation_kind TEXT NOT NULL, source_span_id TEXT REFERENCES text_span(id),
  justification TEXT, review_status TEXT NOT NULL DEFAULT 'unreviewed',
  CHECK(from_node_id <> to_node_id)
);

CREATE TABLE review_record (
  id TEXT PRIMARY KEY, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
  reviewer_ref TEXT NOT NULL, review_role TEXT NOT NULL,
  verdict TEXT NOT NULL, rationale TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  previous_review_id TEXT REFERENCES review_record(id)
);
CREATE TABLE search_scope (
  id TEXT PRIMARY KEY, question TEXT NOT NULL,
  works_json TEXT NOT NULL DEFAULT '[]', editions_json TEXT NOT NULL DEFAULT '[]',
  methodology TEXT NOT NULL, search_terms_json TEXT NOT NULL DEFAULT '[]',
  run_date TEXT NOT NULL, corpus_manifest_hash TEXT,
  result_kind TEXT NOT NULL CHECK(result_kind IN ('found','not_found_in_scope','not_searched','partial','unknown')),
  notes TEXT
);

CREATE TABLE experiment (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, protocol_ref TEXT NOT NULL,
  engine_sha TEXT, rules_sha TEXT, corpus_manifest_hash TEXT,
  methodology_version_id TEXT REFERENCES methodology_version(id),
  test_design_hash TEXT, sealed_key_hash TEXT,
  blind_level TEXT NOT NULL DEFAULT 'development',
  run_status TEXT NOT NULL DEFAULT 'planned'
);
CREATE TABLE experiment_case (
  id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiment(id),
  scenario_id TEXT REFERENCES issue_scenario(id), public_packet_hash TEXT NOT NULL,
  inclusion_kind TEXT NOT NULL DEFAULT 'unseen', status TEXT NOT NULL DEFAULT 'sealed'
);
CREATE TABLE experiment_outcome (
  id TEXT PRIMARY KEY, experiment_case_id TEXT NOT NULL REFERENCES experiment_case(id),
  result_origin TEXT NOT NULL CHECK(result_origin IN ('machine','human_judge','model_commentary')),
  verdict_state TEXT NOT NULL, result_json TEXT NOT NULL,
  trace_hash TEXT, runtime_exit_code INTEGER,
  issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(experiment_case_id,result_origin)
);
CREATE INDEX idx_issue_topic_topic ON issue_topic(topic_id,issue_id);
CREATE INDEX idx_scholar_position_issue ON scholar_position(issue_id,scholar_id);
CREATE INDEX idx_reasoning_event_issue ON reasoning_event(issue_id,scholar_id);
CREATE INDEX idx_evidence_assessment_scholar ON evidence_assessment(scholar_id,evidence_id);
CREATE INDEX idx_text_span_edition_page ON text_span(edition_id,page_locator,database_locator);
CREATE INDEX idx_method_rule_scholar ON method_rule(scholar_id,methodology_version_id);
CREATE INDEX idx_argument_edge_from ON argument_edge(from_node_id);
CREATE INDEX idx_argument_edge_to ON argument_edge(to_node_id);
