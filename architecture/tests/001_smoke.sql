-- Synthetic data only; this is a DATABASE CONTRACT test, not a fiqh test.
-- Run after 001 and 002; all fixture rows rolled back.
BEGIN;
DO $$
DECLARE
  t1 uuid; t2 uuid; issue1 uuid; issue2 uuid; wrong_variant uuid;
  scholar1 uuid; scholar2 uuid; profile1 uuid; profile2 uuid;
  work1 uuid; edition1 uuid; passage1 uuid; rule1 uuid; rule2 uuid;
  rs1 uuid; c1 uuid; ev1 uuid; pos1 uuid; blocked boolean; i integer;
BEGIN
  INSERT INTO fiqh.topics(stable_key,name,kind) VALUES ('test-bay','بیع','bab') RETURNING id INTO t1;
  INSERT INTO fiqh.topics(stable_key,name,kind) VALUES ('test-contemporary','فقه معاصر','contemporary') RETURNING id INTO t2;
  INSERT INTO fiqh.issues(stable_key,canonical_question) VALUES ('test-one-issue','پرسش فرضی واحد') RETURNING id INTO issue1;
  INSERT INTO fiqh.issues(stable_key,canonical_question) VALUES ('test-other-issue','پرسش فرضی دیگر') RETURNING id INTO issue2;
  INSERT INTO fiqh.issue_topics(issue_id,topic_id) VALUES (issue1,t1),(issue1,t2);
  IF (SELECT count(*) FROM fiqh.issue_topics WHERE issue_id=issue1) <> 2 THEN
    RAISE EXCEPTION 'one issue was not allowed in multiple topics';
  END IF;

  INSERT INTO fiqh.scholars(stable_key,display_name) VALUES ('test-scholar-A','فقیه فرضی الف') RETURNING id INTO scholar1;
  INSERT INTO fiqh.scholars(stable_key,display_name) VALUES ('test-scholar-B','فقیه فرضی ب') RETURNING id INTO scholar2;
  INSERT INTO fiqh.methodology_profiles(scholar_id,profile_key,revision)
    VALUES (scholar1,'baseline',1) RETURNING id INTO profile1;
  INSERT INTO fiqh.methodology_profiles(scholar_id,profile_key,revision)
    VALUES (scholar2,'baseline',1) RETURNING id INTO profile2;
  INSERT INTO fiqh.positions(issue_id,scholar_id,profile_id,statement,position_kind)
    VALUES (issue1,scholar1,profile1,'نتیجه فرضی الف','hypothetical_prediction') RETURNING id INTO pos1;
  INSERT INTO fiqh.positions(issue_id,scholar_id,profile_id,statement,position_kind)
    VALUES (issue1,scholar2,profile2,'نتیجه فرضی ب','hypothetical_prediction');
  IF (SELECT count(*) FROM fiqh.positions WHERE issue_id=issue1) <> 2 THEN
    RAISE EXCEPTION 'scholar opinions were overwritten or separated into duplicate issues';
  END IF;

  blocked:=false;
  BEGIN
    INSERT INTO fiqh.positions(issue_id,scholar_id,profile_id,statement,position_kind)
      VALUES (issue1,scholar1,profile2,'wrong profile','reconstruction');
  EXCEPTION WHEN others THEN blocked:=true;
  END;
  IF NOT blocked THEN RAISE EXCEPTION 'cross-scholar profile contamination accepted'; END IF;

  INSERT INTO fiqh.issue_variants(issue_id,variant_key) VALUES (issue2,'variant') RETURNING id INTO wrong_variant;
  blocked:=false;
  BEGIN
    INSERT INTO fiqh.cases(issue_id,variant_id,stable_key) VALUES (issue1,wrong_variant,'test-mixed-issue');
  EXCEPTION WHEN others THEN blocked:=true;
  END;
  IF NOT blocked THEN RAISE EXCEPTION 'cross-issue variant was accepted'; END IF;

  INSERT INTO fiqh.works(stable_key,title,work_kind) VALUES ('test-work','متن آزمایشی','original') RETURNING id INTO work1;
  INSERT INTO fiqh.work_contributors(work_id,scholar_id,role,attribution_status)
    VALUES(work1,scholar1,'author','unverified');
  INSERT INTO fiqh.editions(work_id,edition_key) VALUES(work1,'test-edition') RETURNING id INTO edition1;
  INSERT INTO fiqh.source_passages(edition_id,passage_key,printed_page_label,database_locator,exact_text,text_sha256)
    VALUES(edition1,'p-test','12','/128','متن آزمایشیِ بدون انتساب تاریخی',
      encode(digest(convert_to('متن آزمایشیِ بدون انتساب تاریخی','UTF8'),'sha256'),'hex'))
    RETURNING id INTO passage1;

  INSERT INTO fiqh.reasoning_events(issue_id,scholar_id,work_id,event_key,event_kind,epistemic_layer,source_passage_id)
    VALUES(issue1,scholar1,work1,'event1','test','hypothesis',passage1) RETURNING id INTO ev1;
  FOR i IN 1..12 LOOP
    INSERT INTO fiqh.reasoning_parts(event_id,ordinal,content,source_passage_id)
      VALUES(ev1,i,jsonb_build_object('text','synthetic part ' || i),passage1);
  END LOOP;
  IF (SELECT count(*) FROM fiqh.reasoning_parts WHERE event_id=ev1) <> 12 THEN
    RAISE EXCEPTION 'twelve-part reasoning event lost components';
  END IF;

  INSERT INTO fiqh.method_rules(profile_id,rule_key,principle,rule_family,scope,activation,defeaters,exceptions,conflict_policy,scientific_grade)
    VALUES(profile1,'test-rule1','Synthetic only','conflict','{}','{}','{}','{}','{}','C') RETURNING id INTO rule1;
  INSERT INTO fiqh.method_rules(profile_id,rule_key,principle,rule_family,scope,activation,defeaters,exceptions,conflict_policy,scientific_grade)
    VALUES(profile2,'test-rule2','Synthetic only','conflict','{}','{}','{}','{}','{}','C') RETURNING id INTO rule2;

  INSERT INTO fiqh.rule_sets(profile_id,version_key,engine_sha256,rule_manifest_sha256,frozen_at)
    VALUES(profile1,'t1',repeat('a',64),repeat('b',64),now()) RETURNING id INTO rs1;
  INSERT INTO fiqh.rule_set_members(rule_set_id,rule_id) VALUES (rs1,rule1);

  blocked:=false;
  BEGIN
    INSERT INTO fiqh.rule_set_members(rule_set_id,rule_id) VALUES (rs1,rule2);
  EXCEPTION WHEN others THEN blocked:=true;
  END;
  IF NOT blocked THEN RAISE EXCEPTION 'rule from different scholar contaminated frozen ruleset'; END IF;

  blocked:=false;
  BEGIN
    UPDATE fiqh.method_rules SET scientific_grade='A',reviewer_status='approved',execution_layer='historical'
    WHERE id=rule1;
  EXCEPTION WHEN others THEN blocked:=true;
  END;
  IF NOT blocked THEN RAISE EXCEPTION 'historical rule was approved without six source backings'; END IF;

  INSERT INTO fiqh.rule_backings(rule_id,component,passage_id,backing_grade)
  SELECT rule1, component, passage1,'explicit' FROM
    unnest(ARRAY['scope','activation','defeaters','exceptions','conflict_policy','principle']) AS component;
  UPDATE fiqh.method_rules SET scientific_grade='A',reviewer_status='approved',execution_layer='historical'
    WHERE id=rule1;
  IF (SELECT execution_layer FROM fiqh.method_rules WHERE id=rule1) <> 'historical' THEN
    RAISE EXCEPTION 'fully backed historical rule cannot be admitted';
  END IF;

  blocked:=false;
  BEGIN
    DELETE FROM fiqh.rule_backings WHERE rule_id=rule1 AND component='scope';
  EXCEPTION WHEN others THEN blocked:=true;
  END;
  IF NOT blocked THEN RAISE EXCEPTION 'provenance for approved historical rule was deleted'; END IF;

  INSERT INTO fiqh.cases(issue_id,stable_key,test_class) VALUES(issue1,'test-case','development') RETURNING id INTO c1;
  INSERT INTO fiqh.engine_runs(case_id,rule_set_id,run_mode,verdict_state,input_sha256,output_sha256)
    VALUES(c1,rs1,'safety_probe','stop',repeat('1',64),repeat('2',64));
  INSERT INTO fiqh.evaluation_sets(stable_key,evaluation_type,sealed_answer_sha256,sealed_location_external)
    VALUES('test-blind','independent_blind',repeat('3',64),true);
  RAISE NOTICE 'PASS: many-to-many issue classification, scholar isolation, rule provenance, 12-part event and blind seal';
END $$;
ROLLBACK;
