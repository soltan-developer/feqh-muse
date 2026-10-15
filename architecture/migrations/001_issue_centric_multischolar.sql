-- Feqh-Muse knowledge model v1: subject/issue centred, many scholars, auditable.
-- Intentionally separate from the existing engine2 rules. PostgreSQL 15+.
-- Immutable scientific records should be superseded with new versions, not overwritten.
BEGIN;
CREATE SCHEMA IF NOT EXISTS fiqh;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE fiqh.topics (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  name text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('bab','subbab','crosscutting','contemporary','other')),
  parent_id uuid REFERENCES fiqh.topics(id),
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (parent_id IS DISTINCT FROM id)
);
CREATE TABLE fiqh.issues (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  canonical_question text NOT NULL,
  question_language text NOT NULL DEFAULT 'ar',
  subject_definition jsonb NOT NULL DEFAULT '{}'::jsonb,
  scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed','deprecated')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE fiqh.issue_topics (
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  topic_id uuid NOT NULL REFERENCES fiqh.topics(id),
  relation text NOT NULL DEFAULT 'classified_under' CHECK (relation IN ('classified_under','relevant_to','comparative')),
  PRIMARY KEY(issue_id,topic_id,relation)
);
CREATE TABLE fiqh.issue_relations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  from_issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  to_issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  relation text NOT NULL CHECK (relation IN ('subissue','overlaps','exception','analogy','contrasts','historical_variant','related')),
  rationale text NOT NULL,
  status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','reviewed','disputed')),
  CHECK (from_issue_id <> to_issue_id)
);
CREATE TABLE fiqh.issue_variants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  variant_key text NOT NULL,
  conditions jsonb NOT NULL DEFAULT '{}'::jsonb,
  temporal_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  locale_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(issue_id,variant_key)
);
CREATE TABLE fiqh.concepts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  label text NOT NULL,
  language text NOT NULL,
  category text NOT NULL,
  definition text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE fiqh.issue_concepts (
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  concept_id uuid NOT NULL REFERENCES fiqh.concepts(id),
  role text NOT NULL,
  PRIMARY KEY(issue_id,concept_id,role)
);

CREATE TABLE fiqh.scholars (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  name_ar text,
  birth_ah integer,
  death_ah integer,
  tradition text,
  school_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  biographical_confidence text NOT NULL DEFAULT 'unverified'
    CHECK (biographical_confidence IN ('unverified','documented','disputed')),
  CHECK (death_ah IS NULL OR birth_ah IS NULL OR death_ah >= birth_ah)
);
CREATE TABLE fiqh.scholar_relations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scholar_id uuid NOT NULL REFERENCES fiqh.scholars(id),
  other_scholar_id uuid NOT NULL REFERENCES fiqh.scholars(id),
  relation text NOT NULL CHECK (relation IN ('student_of','teacher_of','cites','critiques','influenced_by','other')),
  status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','documented','disputed')),
  CHECK (scholar_id <> other_scholar_id)
);
CREATE TABLE fiqh.works (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  title text NOT NULL,
  work_kind text NOT NULL CHECK (work_kind IN ('original','taqrir','commentary','hashiya','hadith_collection','other')),
  original_language text,
  probable_date_ah integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE fiqh.work_contributors (
  work_id uuid NOT NULL REFERENCES fiqh.works(id),
  scholar_id uuid NOT NULL REFERENCES fiqh.scholars(id),
  role text NOT NULL CHECK (role IN ('author','compiler','reporter','commentator','editor','attributed_author')),
  attribution_status text NOT NULL CHECK (attribution_status IN ('documented','disputed','unverified')),
  PRIMARY KEY(work_id,scholar_id,role)
);
CREATE TABLE fiqh.editions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  work_id uuid NOT NULL REFERENCES fiqh.works(id),
  edition_key text NOT NULL,
  publisher text,
  editor text,
  edition_year text,
  volume_count integer,
  corpus_identifier text,
  edition_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE(work_id,edition_key),
  CHECK (volume_count IS NULL OR volume_count > 0)
);
CREATE TABLE fiqh.source_passages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  edition_id uuid NOT NULL REFERENCES fiqh.editions(id),
  passage_key text NOT NULL,
  volume_label text,
  printed_page_label text,
  database_locator text,
  section_label text,
  paragraph_ordinal integer,
  exact_text text NOT NULL,
  language text,
  text_sha256 text NOT NULL CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
  source_url text,
  capture_status text NOT NULL DEFAULT 'unverified' CHECK (capture_status IN ('unverified','matched','disputed')),
  UNIQUE(edition_id,passage_key)
);
CREATE TABLE fiqh.passage_variants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  witness_key text NOT NULL,
  variant_text text NOT NULL,
  variant_kind text NOT NULL CHECK (variant_kind IN ('omission','substitution','addition','alternate_reading','other')),
  remarks text,
  UNIQUE(passage_id,witness_key,variant_kind)
);
CREATE TABLE fiqh.passage_alignments (
  left_passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  right_passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  relation text NOT NULL CHECK (relation IN ('same_content','parallel','quotes','translation','apparent_tension')),
  status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','verified','disputed')),
  PRIMARY KEY(left_passage_id,right_passage_id,relation),
  CHECK (left_passage_id <> right_passage_id)
);

CREATE TABLE fiqh.evidence_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  category text NOT NULL CHECK (category IN ('quran','sunna','aql','ijma','urf','sira','shuhra','asl_amali','fiqh_principle','scholar_opinion','other')),
  statement text NOT NULL,
  issue_id uuid REFERENCES fiqh.issues(id),
  provenance_note text,
  properties jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE fiqh.evidence_sources (
  evidence_id uuid NOT NULL REFERENCES fiqh.evidence_items(id),
  passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  relation text NOT NULL CHECK (relation IN ('original','reports','explains','opposes','context')),
  PRIMARY KEY(evidence_id,passage_id,relation)
);
CREATE TABLE fiqh.claims (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid REFERENCES fiqh.issues(id),
  proposition text NOT NULL,
  claim_kind text NOT NULL CHECK (claim_kind IN ('textual','historical','interpretive','legal','hypothesis','absence_search')),
  epistemic_status text NOT NULL DEFAULT 'unverified'
    CHECK (epistemic_status IN ('unverified','supported','challenged','conflict','rejected')),
  attribution_scholar_id uuid REFERENCES fiqh.scholars(id),
  is_historical_attribution boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (NOT is_historical_attribution OR attribution_scholar_id IS NOT NULL)
);
CREATE TABLE fiqh.claim_evidence (
  claim_id uuid NOT NULL REFERENCES fiqh.claims(id),
  evidence_id uuid NOT NULL REFERENCES fiqh.evidence_items(id),
  relation text NOT NULL CHECK (relation IN ('supports','refutes','limits','quotes','contextualizes')),
  inference_status text NOT NULL DEFAULT 'unverified'
    CHECK (inference_status IN ('unverified','licensed','disputed','rejected')),
  license_reference text,
  PRIMARY KEY(claim_id,evidence_id,relation),
  CHECK (inference_status <> 'licensed' OR license_reference IS NOT NULL)
);
CREATE TABLE fiqh.evidence_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id uuid NOT NULL REFERENCES fiqh.evidence_items(id),
  scholar_id uuid REFERENCES fiqh.scholars(id),
  assessor_label text NOT NULL,
  assessed_passage_id uuid REFERENCES fiqh.source_passages(id),
  source_authenticity text NOT NULL DEFAULT 'unverified',
  quote_match text NOT NULL DEFAULT 'unverified',
  semantic_entailment text NOT NULL DEFAULT 'unverified',
  probative_authority text NOT NULL DEFAULT 'unverified',
  argument text,
  assessed_at timestamptz NOT NULL DEFAULT now(),
  CHECK (source_authenticity IN ('unverified','accepted','disputed','rejected')),
  CHECK (quote_match IN ('unverified','accepted','disputed','rejected')),
  CHECK (semantic_entailment IN ('unverified','accepted','disputed','rejected')),
  CHECK (probative_authority IN ('unverified','accepted','disputed','rejected'))
);

-- Optional specialist evidence: no assumption of universally accepted rijal or ijma rules.
CREATE TABLE fiqh.narrations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id uuid NOT NULL UNIQUE REFERENCES fiqh.evidence_items(id),
  wording text NOT NULL,
  original_language text NOT NULL DEFAULT 'ar',
  transmission_notes text
);
CREATE TABLE fiqh.narrators (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  identity_key text NOT NULL UNIQUE,
  name text NOT NULL,
  identity_status text NOT NULL DEFAULT 'unverified'
    CHECK (identity_status IN ('unverified','documented','disputed'))
);
CREATE TABLE fiqh.narration_chains (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  narration_id uuid NOT NULL REFERENCES fiqh.narrations(id),
  chain_key text NOT NULL,
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  transmission_status text NOT NULL DEFAULT 'unverified',
  UNIQUE(narration_id,chain_key)
);
CREATE TABLE fiqh.chain_members (
  chain_id uuid NOT NULL REFERENCES fiqh.narration_chains(id),
  ordinal integer NOT NULL CHECK (ordinal > 0),
  narrator_id uuid NOT NULL REFERENCES fiqh.narrators(id),
  transmission_relation text,
  PRIMARY KEY(chain_id,ordinal)
);
CREATE TABLE fiqh.narrator_assessments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  narrator_id uuid NOT NULL REFERENCES fiqh.narrators(id),
  assessing_scholar_id uuid REFERENCES fiqh.scholars(id),
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  assessment text NOT NULL,
  status text NOT NULL DEFAULT 'attributed' CHECK (status IN ('attributed','verified','disputed')),
  CHECK (assessing_scholar_id IS NOT NULL OR source_passage_id IS NOT NULL)
);
CREATE TABLE fiqh.consensus_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id uuid NOT NULL UNIQUE REFERENCES fiqh.evidence_items(id),
  reporting_scholar_id uuid REFERENCES fiqh.scholars(id),
  kind text NOT NULL CHECK (kind IN ('muhassal','manqul','no_disagreement','tasalum','uncertain')),
  scope_description text NOT NULL,
  potentially_madraki boolean,
  evidentiary_role text NOT NULL DEFAULT 'unverified'
    CHECK (evidentiary_role IN ('unverified','independent','corroborative','historical','disputed')),
  detected_dissent jsonb NOT NULL DEFAULT '[]'::jsonb
);
CREATE TABLE fiqh.custom_contexts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  context_key text NOT NULL UNIQUE,
  community text NOT NULL,
  historical_period text,
  geography text,
  function text NOT NULL CHECK (function IN ('lexical','subject_identification','sira','practice','technical','other')),
  assumptions jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE fiqh.custom_evidence (
  evidence_id uuid NOT NULL REFERENCES fiqh.evidence_items(id),
  context_id uuid NOT NULL REFERENCES fiqh.custom_contexts(id),
  scope_note text NOT NULL,
  PRIMARY KEY(evidence_id,context_id)
);

-- Scholar's evolving methodology is not a global engine switch.
CREATE TABLE fiqh.methodology_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scholar_id uuid NOT NULL REFERENCES fiqh.scholars(id),
  profile_key text NOT NULL,
  revision integer NOT NULL CHECK (revision > 0),
  effective_period text,
  status text NOT NULL DEFAULT 'hypothesis'
    CHECK (status IN ('hypothesis','reviewed','disputed','superseded')),
  parent_profile_id uuid REFERENCES fiqh.methodology_profiles(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(scholar_id,profile_key,revision),
  CHECK (parent_profile_id IS DISTINCT FROM id)
);
CREATE TABLE fiqh.method_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid NOT NULL REFERENCES fiqh.methodology_profiles(id),
  rule_key text NOT NULL,
  principle text NOT NULL,
  rule_family text NOT NULL,
  scope jsonb NOT NULL,
  activation jsonb NOT NULL,
  defeaters jsonb NOT NULL,
  exceptions jsonb NOT NULL,
  conflict_policy jsonb NOT NULL,
  scientific_grade text NOT NULL CHECK (scientific_grade IN ('A','B','C','D','X')),
  execution_layer text NOT NULL DEFAULT 'hypothesis'
    CHECK (execution_layer IN ('historical','hypothesis')),
  reviewer_status text NOT NULL DEFAULT 'pending'
    CHECK (reviewer_status IN ('pending','approved','rejected')),
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  UNIQUE(profile_id,rule_key,version),
  CHECK (execution_layer <> 'historical' OR (scientific_grade IN ('A','B') AND reviewer_status = 'approved'))
);
CREATE TABLE fiqh.rule_backings (
  rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  component text NOT NULL CHECK (component IN ('scope','activation','defeaters','exceptions','conflict_policy','principle')),
  passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  backing_grade text NOT NULL CHECK (backing_grade IN ('explicit','inferred','commentary','disputed')),
  note text,
  PRIMARY KEY(rule_id,component,passage_id)
);
CREATE TABLE fiqh.rule_relations (
  from_rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  to_rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  relation text NOT NULL CHECK (relation IN ('defeats','exception_to','qualifies','supports','conflicts','supersedes')),
  reason text NOT NULL,
  PRIMARY KEY(from_rule_id,to_rule_id,relation),
  CHECK (from_rule_id <> to_rule_id)
);

CREATE TABLE fiqh.positions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  scholar_id uuid NOT NULL REFERENCES fiqh.scholars(id),
  variant_id uuid REFERENCES fiqh.issue_variants(id),
  profile_id uuid REFERENCES fiqh.methodology_profiles(id),
  statement text NOT NULL,
  conclusion_code text,
  position_kind text NOT NULL
    CHECK (position_kind IN ('historical_report','historical_interpretation','reconstruction','hypothetical_prediction')),
  strength text NOT NULL DEFAULT 'unverified'
    CHECK (strength IN ('unverified','explicit','azhar','aqwa','probable','conditional','contested','stop')),
  knowledge_status text NOT NULL DEFAULT 'unreviewed'
    CHECK (knowledge_status IN ('unreviewed','reviewed','disputed','superseded')),
  valid_period_note text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE fiqh.position_sources (
  position_id uuid NOT NULL REFERENCES fiqh.positions(id),
  passage_id uuid NOT NULL REFERENCES fiqh.source_passages(id),
  relation text NOT NULL CHECK (relation IN ('textual_basis','cited_opinion','commentary','contradicts')),
  PRIMARY KEY(position_id,passage_id,relation)
);
CREATE TABLE fiqh.reasoning_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  scholar_id uuid REFERENCES fiqh.scholars(id),
  work_id uuid REFERENCES fiqh.works(id),
  event_key text NOT NULL,
  event_kind text NOT NULL,
  epistemic_layer text NOT NULL CHECK (epistemic_layer IN ('historical_text','interpretation','hypothesis')),
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed','disputed','open')),
  UNIQUE(issue_id,event_key)
);
CREATE TABLE fiqh.reasoning_parts (
  event_id uuid NOT NULL REFERENCES fiqh.reasoning_events(id),
  ordinal integer NOT NULL CHECK (ordinal BETWEEN 1 AND 12),
  content jsonb NOT NULL,
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  assessment_status text NOT NULL DEFAULT 'unverified'
    CHECK (assessment_status IN ('unverified','supported','disputed','not_applicable')),
  PRIMARY KEY(event_id,ordinal)
);
CREATE TABLE fiqh.reasoning_edges (
  from_event_id uuid NOT NULL REFERENCES fiqh.reasoning_events(id),
  to_event_id uuid NOT NULL REFERENCES fiqh.reasoning_events(id),
  relation text NOT NULL CHECK (relation IN ('supports','defeats','qualifies','resolves','quotes','precedes','exception','cross_work','open_question')),
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  epistemic_status text NOT NULL DEFAULT 'unverified',
  PRIMARY KEY(from_event_id,to_event_id,relation),
  CHECK (from_event_id <> to_event_id)
);

CREATE TABLE fiqh.cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  variant_id uuid REFERENCES fiqh.issue_variants(id),
  stable_key text NOT NULL UNIQUE,
  fact_pattern jsonb NOT NULL DEFAULT '{}'::jsonb,
  test_class text NOT NULL DEFAULT 'development'
    CHECK (test_class IN ('development','independent_blind','hypothetical','historical')),
  status text NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','frozen','retired')),
  frozen_at timestamptz
);
CREATE TABLE fiqh.case_facts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES fiqh.cases(id),
  fact_key text NOT NULL,
  value jsonb NOT NULL,
  origin text NOT NULL CHECK (origin IN ('stated_premise','textual_claim','derived','unverified_hypothesis')),
  provenance_passage_id uuid REFERENCES fiqh.source_passages(id),
  derivation_rule_id uuid REFERENCES fiqh.method_rules(id),
  evidence_status text NOT NULL DEFAULT 'unverified'
    CHECK (evidence_status IN ('unverified','quote_verified','licensed','disputed','rejected')),
  CHECK (origin <> 'derived' OR derivation_rule_id IS NOT NULL)
);
CREATE TABLE fiqh.rule_sets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid NOT NULL REFERENCES fiqh.methodology_profiles(id),
  version_key text NOT NULL,
  engine_sha256 text NOT NULL CHECK (engine_sha256 ~ '^[0-9a-f]{64}$'),
  rule_manifest_sha256 text NOT NULL CHECK (rule_manifest_sha256 ~ '^[0-9a-f]{64}$'),
  frozen_at timestamptz NOT NULL,
  UNIQUE(profile_id,version_key)
);
CREATE TABLE fiqh.rule_set_members (
  rule_set_id uuid NOT NULL REFERENCES fiqh.rule_sets(id),
  rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  PRIMARY KEY(rule_set_id,rule_id)
);
CREATE TABLE fiqh.engine_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES fiqh.cases(id),
  rule_set_id uuid NOT NULL REFERENCES fiqh.rule_sets(id),
  run_mode text NOT NULL CHECK (run_mode IN ('historical_reconstruction','hypothetical_experiment','safety_probe')),
  verdict_state text NOT NULL CHECK (verdict_state IN ('established','conditional','conflict','stop','out_of_domain','execution_error')),
  verdict text,
  input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
  output_sha256 text NOT NULL CHECK (output_sha256 ~ '^[0-9a-f]{64}$'),
  raw_output jsonb NOT NULL DEFAULT '{}'::jsonb,
  exit_code integer,
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);
CREATE TABLE fiqh.run_steps (
  run_id uuid NOT NULL REFERENCES fiqh.engine_runs(id),
  ordinal integer NOT NULL CHECK (ordinal > 0),
  rule_id uuid REFERENCES fiqh.method_rules(id),
  status text NOT NULL CHECK (status IN ('fired','blocked_false','blocked_unknown','blocked_conflict','defeated','stopped')),
  premises jsonb NOT NULL DEFAULT '[]'::jsonb,
  trace jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY(run_id,ordinal)
);
CREATE TABLE fiqh.search_scopes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id uuid NOT NULL REFERENCES fiqh.claims(id),
  searched_editions jsonb NOT NULL,
  queries jsonb NOT NULL,
  method text NOT NULL,
  searched_at timestamptz NOT NULL DEFAULT now(),
  outcome text NOT NULL CHECK (outcome IN ('not_found','found','inconclusive')),
  CHECK (jsonb_typeof(searched_editions) = 'array' AND jsonb_array_length(searched_editions) > 0)
);
CREATE TABLE fiqh.human_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reviewer_pseudonym text NOT NULL,
  target_kind text NOT NULL CHECK (target_kind IN ('claim','rule','position','event','evidence','run','case','source')),
  target_id uuid NOT NULL,
  decision text NOT NULL CHECK (decision IN ('approved','rejected','needs_evidence','contested')),
  rationale text NOT NULL,
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  recorded_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE fiqh.evaluation_sets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  evaluation_type text NOT NULL CHECK (evaluation_type IN ('development','internal_blind','independent_blind')),
  sealed_answer_sha256 text CHECK (sealed_answer_sha256 ~ '^[0-9a-f]{64}$'),
  sealed_location_external boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'preregistered'
    CHECK (status IN ('preregistered','executed','unsealed','retired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (evaluation_type <> 'independent_blind' OR sealed_location_external)
);
CREATE TABLE fiqh.evaluation_cases (
  evaluation_set_id uuid NOT NULL REFERENCES fiqh.evaluation_sets(id),
  case_id uuid NOT NULL REFERENCES fiqh.cases(id),
  run_id uuid REFERENCES fiqh.engine_runs(id),
  disclosure_status text NOT NULL DEFAULT 'sealed'
    CHECK (disclosure_status IN ('sealed','opened','excluded_with_reason')),
  PRIMARY KEY(evaluation_set_id,case_id)
);
-- Index the high-volume navigational joins; JSONB indexes can be added later per real queries.
CREATE INDEX ON fiqh.issue_topics(topic_id);
CREATE INDEX ON fiqh.issue_relations(to_issue_id);
CREATE INDEX ON fiqh.work_contributors(scholar_id);
CREATE INDEX ON fiqh.source_passages(edition_id,printed_page_label);
CREATE INDEX ON fiqh.evidence_items(issue_id,category);
CREATE INDEX ON fiqh.positions(issue_id,scholar_id);
CREATE INDEX ON fiqh.reasoning_events(issue_id,scholar_id);
CREATE INDEX ON fiqh.method_rules(profile_id,rule_family);
CREATE INDEX ON fiqh.case_facts(case_id,fact_key);
CREATE INDEX ON fiqh.engine_runs(rule_set_id,started_at);
COMMIT;
