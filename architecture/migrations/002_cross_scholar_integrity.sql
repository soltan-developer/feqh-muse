-- Integrity rules for the multischolar knowledge model.
-- In particular prevent issue/variant and scholar/profile cross-wiring.
BEGIN;
CREATE TABLE fiqh.reasoning_operators (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  name text NOT NULL,
  operator_family text NOT NULL CHECK (operator_family IN ('evidence','dalala','sanad','ijma','urf','aql','conflict','practical_principle','other')),
  input_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  neutral_algorithm_reference text,
  status text NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','reviewed','deprecated'))
);
ALTER TABLE fiqh.method_rules ADD COLUMN operator_id uuid REFERENCES fiqh.reasoning_operators(id);
-- One abstract operator may be used with different activation/priority policies by different scholars.

CREATE FUNCTION fiqh.check_variant_issue() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.variant_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM fiqh.issue_variants
    WHERE id=NEW.variant_id AND issue_id=NEW.issue_id
  ) THEN
    RAISE EXCEPTION 'issue variant does not belong to the selected issue';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER position_variant_guard BEFORE INSERT OR UPDATE
  ON fiqh.positions FOR EACH ROW EXECUTE FUNCTION fiqh.check_variant_issue();
CREATE TRIGGER case_variant_guard BEFORE INSERT OR UPDATE
  ON fiqh.cases FOR EACH ROW EXECUTE FUNCTION fiqh.check_variant_issue();

CREATE FUNCTION fiqh.check_position_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.profile_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM fiqh.methodology_profiles
    WHERE id=NEW.profile_id AND scholar_id=NEW.scholar_id
  ) THEN
    RAISE EXCEPTION 'profile belongs to another scholar';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER position_profile_guard BEFORE INSERT OR UPDATE
  ON fiqh.positions FOR EACH ROW EXECUTE FUNCTION fiqh.check_position_profile();

CREATE FUNCTION fiqh.check_rule_set_profile() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM fiqh.rule_sets s JOIN fiqh.method_rules r ON r.id=NEW.rule_id
    WHERE s.id=NEW.rule_set_id AND s.profile_id=r.profile_id
  ) THEN
    RAISE EXCEPTION 'method rule cannot be attached to a different scholar/profile ruleset';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER rule_set_profile_guard BEFORE INSERT OR UPDATE
  ON fiqh.rule_set_members FOR EACH ROW EXECUTE FUNCTION fiqh.check_rule_set_profile();

-- Historical rules may only be approved after ALL SIX backed components exist.
CREATE FUNCTION fiqh.check_historical_rule_backings() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE backed_count integer;
BEGIN
  IF NEW.execution_layer='historical' THEN
    SELECT count(DISTINCT component) INTO backed_count
    FROM fiqh.rule_backings
    WHERE rule_id=NEW.id AND backing_grade IN ('explicit','inferred');
    IF backed_count <> 6 THEN
      RAISE EXCEPTION 'historical rule requires six independently sourced backed components; got %',backed_count;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER historical_rule_gate BEFORE INSERT OR UPDATE
  ON fiqh.method_rules FOR EACH ROW EXECUTE FUNCTION fiqh.check_historical_rule_backings();

CREATE FUNCTION fiqh.protect_historical_backings() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS(SELECT 1 FROM fiqh.method_rules WHERE id=OLD.rule_id AND execution_layer='historical') THEN
    RAISE EXCEPTION 'historical rule backing is sealed; create a new methodology version instead';
  END IF;
  RETURN OLD;
END $$;
CREATE TRIGGER preserve_historical_backings BEFORE DELETE OR UPDATE
  ON fiqh.rule_backings FOR EACH ROW EXECUTE FUNCTION fiqh.protect_historical_backings();

-- Prevent running a rule not present in its frozen ruleset, even when its scholar is the same.
CREATE FUNCTION fiqh.check_run_step_member() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.rule_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM fiqh.engine_runs run
    JOIN fiqh.rule_set_members member ON member.rule_set_id=run.rule_set_id
    WHERE run.id=NEW.run_id AND member.rule_id=NEW.rule_id
  ) THEN
    RAISE EXCEPTION 'run trace refers to a rule outside its frozen ruleset';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER run_step_member_guard BEFORE INSERT OR UPDATE
  ON fiqh.run_steps FOR EACH ROW EXECUTE FUNCTION fiqh.check_run_step_member();

-- An "approved" rating never proves fiqh truth by itself; source + backing remain necessary.
COMMENT ON COLUMN fiqh.evidence_assessments.probative_authority IS
  'One assessor-specific appraisal; never global evidence truth';
COMMENT ON COLUMN fiqh.positions.position_kind IS
  'Historical attribution must never be silently merged with hypothetical prediction';
COMMENT ON TABLE fiqh.reasoning_operators IS
  'Neutral reusable operations, not unqualified jurisprudential verdicts';
COMMIT;
