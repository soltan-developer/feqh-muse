-- Phase C contract probes: synthetic reviews, no fiqh finding.
-- Run after Phase B import and 004. Rolled back in full.
BEGIN;
DO $$
DECLARE
  sch uuid; ed uuid; p1 uuid; p2 uuid;
  prof uuid; r_a uuid; r_b uuid; obj uuid;
  component_name text; did_fail boolean;
  components text[] := ARRAY['scope','activation','defeaters','exceptions','conflict_policy','principle'];
BEGIN
  IF (SELECT count(*) FROM fiqh.method_rules WHERE rule_family='legacy_ghabn'
      AND execution_layer='hypothesis' AND reviewer_status='pending') <> 13 THEN
    RAISE EXCEPTION 'Phase B rule candidates changed or were automatically promoted';
  END IF;
  IF EXISTS(SELECT 1 FROM fiqh.rule_qualification_readiness
            WHERE execution_layer='historical') THEN
    RAISE EXCEPTION 'unexpected historical rules in baseline';
  END IF;
  RAISE NOTICE 'PASS C01: all thirteen Phase B legacy rules remain unapproved hypotheses';

  INSERT INTO fiqh.scholars(stable_key,display_name)
  VALUES ('c-synthetic-researcher','فقیه ساختگی تست') RETURNING id INTO sch;
  INSERT INTO fiqh.methodology_profiles(scholar_id,profile_key,revision,status)
  VALUES (sch,'c-review-demo',1,'reviewed') RETURNING id INTO prof;
  SELECT id INTO ed FROM fiqh.editions ORDER BY id LIMIT 1;
  IF ed IS NULL THEN RAISE EXCEPTION 'Phase B import is missing'; END IF;
  INSERT INTO fiqh.source_passages(edition_id,passage_key,exact_text,text_sha256,capture_status)
  VALUES(ed,'c-synthetic-1','EXPLICIT SYNTHETIC WITNESS 1',
         encode(digest(convert_to('EXPLICIT SYNTHETIC WITNESS 1','UTF8'),'sha256'),'hex'),'matched')
  RETURNING id INTO p1;
  INSERT INTO fiqh.source_passages(edition_id,passage_key,exact_text,text_sha256,capture_status)
  VALUES(ed,'c-synthetic-2','EXPLICIT SYNTHETIC WITNESS 2',
         encode(digest(convert_to('EXPLICIT SYNTHETIC WITNESS 2','UTF8'),'sha256'),'hex'),'matched')
  RETURNING id INTO p2;

  INSERT INTO fiqh.method_rules
    (profile_id,rule_key,principle,rule_family,scope,activation,
     defeaters,exceptions,conflict_policy,scientific_grade)
  VALUES(prof,'C-DEMO-A','SYNTHETIC ONLY','other','{}','{}','{}','{}','{}','A')
  RETURNING id INTO r_a;

  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_a;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'historical promotion accepted with zero backs'; END IF;
  RAISE NOTICE 'PASS C02: zero-backing promotion refused';

  FOREACH component_name IN ARRAY components LOOP
    INSERT INTO fiqh.rule_backings(rule_id,component,passage_id,backing_grade)
    VALUES (r_a,component_name,p1,'explicit');
  END LOOP;
  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_a;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'six unreviewed backings were enough'; END IF;
  RAISE NOTICE 'PASS C03: six bare backings no longer suffice';

  did_fail:=false;
  BEGIN
    INSERT INTO fiqh.rule_component_reviews(rule_id,component,passage_id,
             reviewer_label,verdict,reasoning)
    VALUES(r_a,'scope',p2,'qa-witness-one','accepted','invalid cross-attachment');
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'review may reference a non-backed span'; END IF;
  RAISE NOTICE 'PASS C04: review must reference a real rule/component/passage backing';

  FOREACH component_name IN ARRAY components LOOP
    INSERT INTO fiqh.rule_component_reviews(rule_id,component,passage_id,
        reviewer_label,verdict,reasoning,witness_group)
    VALUES(r_a,component_name,p1,'qa-witness-one','accepted',
        'synthetic cross-check of captured passage only', 'group-one');
  END LOOP;
  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_a;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'no-human-decision promotion accepted'; END IF;
  RAISE NOTICE 'PASS C05: human approval still required';

  INSERT INTO fiqh.rule_qualification_decisions(rule_id,reviewer_label,verdict,
     rationale,review_manifest_sha256)
  VALUES(r_a,'independent-reviewer-one','approved','synthetic review one', repeat('a',64));
  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_a;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'single human decision was enough'; END IF;
  RAISE NOTICE 'PASS C06: second independent reviewer still required';

  INSERT INTO fiqh.rule_qualification_decisions(rule_id,reviewer_label,verdict,
     rationale,review_manifest_sha256)
  VALUES(r_a,'independent-reviewer-two','approved','synthetic review two', repeat('b',64));
  UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
  WHERE id=r_a;
  IF (SELECT execution_layer FROM fiqh.method_rules WHERE id=r_a) <> 'historical' THEN
    RAISE EXCEPTION 'A-grade synthetic qualification should be accepted';
  END IF;
  RAISE NOTICE 'PASS C07: A-grade structurally reviewed demonstration passes';

  did_fail:=false;
  BEGIN
    UPDATE fiqh.rule_component_reviews SET verdict='rejected' WHERE rule_id=r_a;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'review could be rewritten after qualification'; END IF;
  RAISE NOTICE 'PASS C08: qualification review sealed';

  INSERT INTO fiqh.method_rules
    (profile_id,rule_key,principle,rule_family,scope,activation,
     defeaters,exceptions,conflict_policy,scientific_grade)
  VALUES(prof,'C-DEMO-B','SYNTHETIC INFERENTIAL ONLY','other','{}','{}','{}','{}','{}','B')
  RETURNING id INTO r_b;
  FOREACH component_name IN ARRAY components LOOP
    INSERT INTO fiqh.rule_backings(rule_id,component,passage_id,backing_grade)
    VALUES(r_b,component_name,p1,'inferred');
    INSERT INTO fiqh.rule_component_reviews(rule_id,component,passage_id,
        reviewer_label,verdict,reasoning,witness_group)
    VALUES(r_b,component_name,p1,'qa-witness-one','accepted',
        'first source is not enough for B grade', 'group-one');
  END LOOP;
  INSERT INTO fiqh.rule_qualification_decisions(rule_id,reviewer_label,verdict,
     rationale,review_manifest_sha256)
  VALUES
    (r_b,'independent-reviewer-one','approved','synthetic review one',repeat('c',64)),
    (r_b,'independent-reviewer-two','approved','synthetic review two',repeat('d',64));

  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_b;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'B grade wrongly accepted one witness'; END IF;
  RAISE NOTICE 'PASS C09: B-grade needs two witnessed sources';

  INSERT INTO fiqh.rule_backings(rule_id,component,passage_id,backing_grade)
  VALUES(r_b,'principle',p2,'inferred');
  INSERT INTO fiqh.rule_component_reviews(rule_id,component,passage_id,
      reviewer_label,verdict,reasoning,witness_group)
  VALUES(r_b,'principle',p2,'qa-witness-two','accepted',
      'second documented independent group', 'group-two');
  INSERT INTO fiqh.rule_qualification_objections(rule_id,objection_key,description)
  VALUES(r_b,'OPEN-COUNTER','contradictory witness not yet resolved')
  RETURNING id INTO obj;
  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
    WHERE id=r_b;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'rule promoted with open defeater'; END IF;
  RAISE NOTICE 'PASS C10: unresolved objection blocks promotion';

  UPDATE fiqh.rule_qualification_objections SET resolution='resolved',reviewed_by='reviewer-independent'
  WHERE id=obj;
  UPDATE fiqh.method_rules SET execution_layer='historical',reviewer_status='approved'
  WHERE id=r_b;
  RAISE NOTICE 'PASS C11: B-grade synthetic review may pass after two witnesses and resolved objection';

  did_fail:=false;
  BEGIN
    UPDATE fiqh.method_rules SET principle='silent rewrite' WHERE id=r_b;
  EXCEPTION WHEN OTHERS THEN did_fail:=true;
  END;
  IF NOT did_fail THEN RAISE EXCEPTION 'historical record changed in-place'; END IF;
  RAISE NOTICE 'PASS C12: historical rule immutable, requires new version';
END $$;
ROLLBACK;
