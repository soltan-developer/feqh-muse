-- Phase C / 004: pre-admission scholarly qualification gate.
-- Structural safety only: reviewers, matching quotes, and source status
-- are claims requiring independent scientific audit; DB cannot prove fiqh truth.
-- Does NOT approve, rewrite, or import any legacy rule.
BEGIN;

CREATE TABLE fiqh.rule_component_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id uuid NOT NULL,
  component text NOT NULL,
  passage_id uuid NOT NULL,
  reviewer_label text NOT NULL CHECK (length(btrim(reviewer_label)) > 2),
  verdict text NOT NULL CHECK (verdict IN ('accepted','rejected','needs_evidence','contested')),
  reasoning text NOT NULL CHECK (length(btrim(reasoning)) > 5),
  witness_group text,
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (rule_id,component,passage_id)
    REFERENCES fiqh.rule_backings(rule_id,component,passage_id),
  UNIQUE(rule_id,component,passage_id,reviewer_label)
);

CREATE TABLE fiqh.rule_qualification_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  reviewer_label text NOT NULL CHECK (length(btrim(reviewer_label)) > 2),
  verdict text NOT NULL CHECK (verdict IN ('approved','rejected','needs_evidence','contested')),
  rationale text NOT NULL CHECK (length(btrim(rationale)) > 5),
  review_manifest_sha256 text NOT NULL CHECK (review_manifest_sha256 ~ '^[0-9a-f]{64}$'),
  reviewed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(rule_id,reviewer_label)
);

CREATE TABLE fiqh.rule_qualification_objections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_id uuid NOT NULL REFERENCES fiqh.method_rules(id),
  objection_key text NOT NULL,
  source_passage_id uuid REFERENCES fiqh.source_passages(id),
  description text NOT NULL,
  resolution text NOT NULL DEFAULT 'open'
    CHECK (resolution IN ('open','contested','resolved','superseded')),
  reviewed_by text,
  UNIQUE(rule_id,objection_key)
);

-- Conspicuously NOT a rule engine: summary of what evidence has and has
-- not passed structural admission gates. Current pilot has ZERO approvals.
CREATE VIEW fiqh.rule_qualification_readiness AS
SELECT r.id AS rule_id, r.rule_key, r.profile_id,
       r.scientific_grade, r.reviewer_status, r.execution_layer,
       COUNT(DISTINCT v.component) FILTER (
         WHERE v.verdict='accepted' AND b.backing_grade IN ('explicit','inferred')
           AND p.capture_status='matched'
       ) AS substantiated_components,
       COUNT(DISTINCT d.reviewer_label) FILTER (WHERE d.verdict='approved') AS approving_reviewers,
       COUNT(DISTINCT v.passage_id) FILTER (
         WHERE v.verdict='accepted' AND v.component='principle'
           AND b.backing_grade IN ('explicit','inferred')
           AND p.capture_status='matched'
       ) AS principle_witness_passages,
       COUNT(DISTINCT v.witness_group) FILTER (
         WHERE v.verdict='accepted' AND v.component='principle'
           AND b.backing_grade IN ('explicit','inferred')
           AND p.capture_status='matched'
       ) AS principle_independence_groups,
       COUNT(DISTINCT o.id) FILTER (WHERE o.resolution IN ('open','contested')) AS open_objections
FROM fiqh.method_rules r
LEFT JOIN fiqh.rule_component_reviews v ON v.rule_id=r.id
LEFT JOIN fiqh.rule_backings b ON b.rule_id=v.rule_id
  AND b.component=v.component AND b.passage_id=v.passage_id
LEFT JOIN fiqh.source_passages p ON p.id=v.passage_id
LEFT JOIN fiqh.rule_qualification_decisions d ON d.rule_id=r.id
LEFT JOIN fiqh.rule_qualification_objections o ON o.rule_id=r.id
GROUP BY r.id;

CREATE FUNCTION fiqh.phase_c_check_historical_promotion() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  c fiqh.rule_qualification_readiness%ROWTYPE;
  profile_status text;
  has_explicit_principle boolean;
BEGIN
  IF TG_OP='UPDATE' AND OLD.execution_layer='historical' THEN
    RAISE EXCEPTION 'historical rule is immutable: supersede with a new profile/rule revision';
  END IF;
  IF NEW.execution_layer<>'historical' THEN RETURN NEW; END IF;

  SELECT status INTO profile_status
  FROM fiqh.methodology_profiles WHERE id=NEW.profile_id;
  IF profile_status IS DISTINCT FROM 'reviewed' THEN
    RAISE EXCEPTION 'qualification HOLD: scholar methodology profile is not reviewed';
  END IF;

  IF NEW.scientific_grade NOT IN ('A','B') OR NEW.reviewer_status<>'approved' THEN
    RAISE EXCEPTION 'qualification HOLD: A/B scientific grade and approved reviewer status required';
  END IF;
  SELECT * INTO c FROM fiqh.rule_qualification_readiness WHERE rule_id=NEW.id;
  IF NOT FOUND OR c.substantiated_components <> 6 THEN
    RAISE EXCEPTION 'qualification HOLD: six independently reviewed and source-matched component backings required';
  END IF;
  IF c.approving_reviewers < 2 THEN
    RAISE EXCEPTION 'qualification HOLD: two distinct human reviewer approvals required';
  END IF;
  IF c.open_objections > 0 THEN
    RAISE EXCEPTION 'qualification HOLD: unresolved objection exists';
  END IF;
  IF NEW.scientific_grade='A' THEN
    SELECT EXISTS (
      SELECT 1 FROM fiqh.rule_component_reviews v
      JOIN fiqh.rule_backings b
        ON b.rule_id=v.rule_id AND b.component=v.component AND b.passage_id=v.passage_id
      JOIN fiqh.source_passages p ON p.id=b.passage_id
      WHERE v.rule_id=NEW.id AND v.component='principle'
        AND v.verdict='accepted' AND b.backing_grade='explicit'
        AND p.capture_status='matched'
    ) INTO has_explicit_principle;
    IF NOT has_explicit_principle THEN
      RAISE EXCEPTION 'qualification HOLD: A-grade principle must have explicitly backed text';
    END IF;
  ELSE
    IF c.principle_witness_passages < 2 OR c.principle_independence_groups < 2 THEN
      RAISE EXCEPTION 'qualification HOLD: B-grade inference needs two independently reviewed textual witnesses';
    END IF;
  END IF;
  RETURN NEW;
END $$;

-- The original 002 migration still enforces A/B + six backing TYPES.
-- This extra gate adds human review and matched-source requirements.
CREATE TRIGGER phase_c_historical_promotion_guard
BEFORE UPDATE ON fiqh.method_rules
FOR EACH ROW EXECUTE FUNCTION fiqh.phase_c_check_historical_promotion();

-- Scientific records that have been admitted are sealed in-place.
-- Any correction requires a new rule/profile revision and a new decision.
CREATE FUNCTION fiqh.phase_c_protect_qualification_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid;
BEGIN
  rid := CASE WHEN TG_OP='DELETE' THEN OLD.rule_id ELSE NEW.rule_id END;
  IF EXISTS(SELECT 1 FROM fiqh.method_rules WHERE id=rid AND execution_layer='historical') THEN
    RAISE EXCEPTION 'qualification dossier is sealed: supersede in a new revision';
  END IF;
  RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER phase_c_component_review_seal
BEFORE UPDATE OR DELETE ON fiqh.rule_component_reviews
FOR EACH ROW EXECUTE FUNCTION fiqh.phase_c_protect_qualification_evidence();
CREATE TRIGGER phase_c_decision_review_seal
BEFORE UPDATE OR DELETE ON fiqh.rule_qualification_decisions
FOR EACH ROW EXECUTE FUNCTION fiqh.phase_c_protect_qualification_evidence();

COMMENT ON VIEW fiqh.rule_qualification_readiness IS
  'Technical admission readiness, NEVER an automated ruling on fiqh truth, probative authority, or accuracy of human testimony.';
COMMIT;
