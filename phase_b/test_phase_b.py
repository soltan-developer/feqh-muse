# -*- coding: utf-8 -*-
"""PostgreSQL integration contracts. Synthetic scholar data is rolled back."""
import json
import os
import pathlib
import subprocess
import sys
import unittest

import psycopg
from psycopg.types.json import Jsonb

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from phase_b.adapter import baseline_core, run
from phase_b.pilot import DEV_FACTS, digest, file_text, seed


class PhaseB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg.connect(os.environ["DATABASE_URL"])
        cls.first = seed(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_01_import_counts_and_two_codings(self):
        with self.conn.cursor() as c:
            c.execute("SELECT count(*) FROM fiqh.issues")
            self.assertEqual(c.fetchone()[0], 2)
            c.execute("SELECT event_kind,count(*) FROM fiqh.reasoning_events GROUP BY 1")
            counts = dict(c.fetchall())
            self.assertEqual(counts.get("research_coding_U"), 12)
            self.assertGreaterEqual(counts.get("research_coding_A", 0), 30)
            self.assertGreaterEqual(counts.get("research_coding_B", 0), 35)
            c.execute("SELECT count(*) FROM fiqh.reasoning_parts")
            self.assertEqual(c.fetchone()[0], 12 * sum(counts.values()))
            c.execute("SELECT count(*) FROM fiqh.source_passages WHERE capture_status='unverified'")
            self.assertEqual(c.fetchone()[0], self.first["passages"])

    def test_02_idempotent_second_import(self):
        with self.conn.cursor() as c:
            c.execute("SELECT count(*) FROM fiqh.reasoning_events")
            before = c.fetchone()[0]
            c.execute("SELECT count(*) FROM fiqh.evidence_items")
            evidence = c.fetchone()[0]
        self.assertEqual(seed(self.conn), self.first)
        with self.conn.cursor() as c:
            c.execute("SELECT count(*) FROM fiqh.reasoning_events")
            self.assertEqual(c.fetchone()[0], before)
            c.execute("SELECT count(*) FROM fiqh.evidence_items")
            self.assertEqual(c.fetchone()[0], evidence)

    def test_03_multi_topic(self):
        with self.conn.cursor() as c:
            c.execute("""SELECT count(*) FROM fiqh.issue_topics t JOIN fiqh.issues i
                         ON i.id=t.issue_id WHERE i.stable_key='khiyar.ghabn'""")
            self.assertGreaterEqual(c.fetchone()[0], 2)

    def test_04_locked_core_same_result(self):
        res = run(self.conn, "khiyar.ghabn", "murtada-ansari",
                  "ansari-development", "ghabn.t8.core.development")
        self.assertEqual(res["engine_output"], baseline_core(DEV_FACTS))
        self.assertEqual(res["historical_attribution"], None)
        self.assertEqual(res["scientific_status"], "DEVELOPMENT_ONLY_NOT_A_FATWA")
        self.assertIn(res["verdict"], ("UNDETERMINED_PIVOTAL", "STOP"))
        self.assertTrue(res["trace_sha256"])

    def test_05_udhrah_no_fabricated_verdict(self):
        res = run(self.conn, "sale.adhrah", "murtada-ansari",
                  "ansari-development", "udhrah.documentary.no-rule")
        self.assertEqual(res["stop_id"], "STOP-OUT-OF-DOMAIN")
        self.assertIsNone(res["historical_attribution"])

    def test_06_wrong_case_issue_rejected(self):
        res = run(self.conn, "sale.adhrah", "murtada-ansari",
                  "ansari-development", "ghabn.t8.core.development")
        self.assertEqual(res["stop_id"], "STOP-IDENTITY-OR-SCOPE-MISMATCH")

    def test_07_historical_gate_not_self_promoting(self):
        res = run(self.conn, "khiyar.ghabn", "murtada-ansari",
                  "ansari-development", "ghabn.t8.core.development",
                  run_mode="historical_reconstruction")
        self.assertEqual(res["stop_id"], "STOP-UNAPPROVED-METHODOLOGY")

    def test_08_source_provenance_is_not_probative_validation(self):
        with self.conn.cursor() as c:
            c.execute("SELECT count(*) FROM fiqh.evidence_assessments WHERE probative_authority='accepted'")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT count(*) FROM fiqh.source_passages WHERE printed_page_label IS NOT NULL")
            self.assertEqual(c.fetchone()[0], 0)
            c.execute("SELECT count(*) FROM fiqh.method_rules WHERE execution_layer='historical'")
            self.assertEqual(c.fetchone()[0], 0)

    def test_09_synthetic_scholars_versions_and_evidence_appraisals(self):
        # Test-only rows in a savepoint: NOT real attributed scholarship.
        with self.conn.transaction():
            with self.conn.cursor() as c:
                c.execute("""INSERT INTO fiqh.scholars(stable_key,display_name)
                             VALUES ('synthetic-test-only','SYNTHETIC QA')
                             RETURNING id""")
                other = c.fetchone()[0]
                c.execute("""SELECT id FROM fiqh.issues WHERE stable_key='khiyar.ghabn'""")
                issue = c.fetchone()[0]
                c.execute("""SELECT id FROM fiqh.scholars WHERE stable_key='murtada-ansari'""")
                ansari = c.fetchone()[0]
                c.execute("""INSERT INTO fiqh.methodology_profiles(scholar_id,profile_key,revision)
                             VALUES (%s,'synthetic-profile',1) RETURNING id""", (other,))
                version1 = c.fetchone()[0]
                c.execute("""INSERT INTO fiqh.methodology_profiles(scholar_id,profile_key,revision,parent_profile_id)
                             VALUES (%s,'synthetic-profile',2,%s) RETURNING id""", (other,version1))
                version2 = c.fetchone()[0]
                self.assertNotEqual(version1, version2)
                c.execute("""INSERT INTO fiqh.positions(issue_id,scholar_id,profile_id,statement,position_kind)
                             VALUES (%s,%s,%s,'SYNTHETIC NOT A FIQH POSITION','hypothetical_prediction')""", (issue,other,version1))
                c.execute("SELECT id FROM fiqh.evidence_items LIMIT 1")
                ev = c.fetchone()[0]
                for scholar in (ansari, other):
                    c.execute("""INSERT INTO fiqh.evidence_assessments
                                 (evidence_id,scholar_id,assessor_label,probative_authority)
                                 VALUES (%s,%s,'SYNTHETIC QA','unverified')""", (ev,scholar))
                # A foreign scholar's profile must not be attached to Ansari's position.
                with self.assertRaises(psycopg.Error):
                    with self.conn.transaction():
                        c.execute("""INSERT INTO fiqh.positions(issue_id,scholar_id,profile_id,statement,position_kind)
                                     VALUES (%s,%s,%s,'SHOULD FAIL','hypothetical_prediction')""", (issue,ansari,version2))
                self.assertEqual(run(self.conn, "khiyar.ghabn", "synthetic-test-only",
                    str(version1), "ghabn.t8.core.development")["stop_id"], "STOP-INACTIVE-SCHOLAR")
                # Trigger a rollback of ALL synthetic data after assertions.
                raise_rollback = True
                if raise_rollback:
                    c.execute("SELECT 1")
            # A top-level conn.rollback would roll back setup too; use an explicit outer rollback via context exception.
            raise SyntheticRollback()


class SyntheticRollback(Exception):
    pass


# Wrap the synthetic test in an expected rollback so QA cannot contaminate the corpus.
_original = PhaseB.test_09_synthetic_scholars_versions_and_evidence_appraisals
def _rollback_safe(self):
    try:
        _original(self)
    except SyntheticRollback:
        return
PhaseB.test_09_synthetic_scholars_versions_and_evidence_appraisals = _rollback_safe


if __name__ == "__main__":
    unittest.main(verbosity=2)
