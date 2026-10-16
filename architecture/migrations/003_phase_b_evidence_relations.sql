-- Phase B: preserve original documentary graph relationships without claiming
-- any undecided relation equals 'supports' or a juridically valid inference.
BEGIN;
CREATE TABLE fiqh.evidence_relations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id uuid NOT NULL REFERENCES fiqh.issues(id),
  source_node_key text NOT NULL,
  target_node_key text NOT NULL,
  relation_original text NOT NULL,
  relation_kind text NOT NULL DEFAULT 'unclassified',
  from_evidence_id uuid REFERENCES fiqh.evidence_items(id),
  to_evidence_id uuid REFERENCES fiqh.evidence_items(id),
  provenance_file text NOT NULL,
  provenance_sha256 text NOT NULL CHECK (provenance_sha256 ~ '^[a-f0-9]{64}$'),
  assessment_status text NOT NULL DEFAULT 'unverified'
    CHECK (assessment_status IN ('unverified','supported','disputed','rejected')),
  UNIQUE (issue_id,provenance_file,source_node_key,target_node_key,relation_original)
);
CREATE FUNCTION fiqh.check_evidence_relation_issue() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.from_evidence_id IS NOT NULL AND
     NOT EXISTS (SELECT 1 FROM fiqh.evidence_items e
                 WHERE e.id=NEW.from_evidence_id AND e.issue_id=NEW.issue_id) THEN
    RAISE EXCEPTION 'source evidence belongs to another issue';
  END IF;
  IF NEW.to_evidence_id IS NOT NULL AND
     NOT EXISTS (SELECT 1 FROM fiqh.evidence_items e
                 WHERE e.id=NEW.to_evidence_id AND e.issue_id=NEW.issue_id) THEN
    RAISE EXCEPTION 'target evidence belongs to another issue';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER evidence_relation_issue_guard
  BEFORE INSERT OR UPDATE ON fiqh.evidence_relations
  FOR EACH ROW EXECUTE FUNCTION fiqh.check_evidence_relation_issue();
COMMENT ON TABLE fiqh.evidence_relations IS
  'Lossless links from the research graphs; raw relations remain unclassified until independent scientific review';
COMMIT;
