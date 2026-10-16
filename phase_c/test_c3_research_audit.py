# -*- coding: utf-8 -*-
"""Tests for source-ID misalignment, quote status and non-admission of Muse v2."""
import json
import unittest

from phase_c.c3_research_audit import (
    build_review, alignment, C3, C1, get_json, source_blocks, PARTS
)

class SourceIdentityGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet=build_review()
        cls.v2=get_json(C3/"METHOD_RULE_CANDIDATES_V2.json")

    def test_ten_candidate_rules_are_preserved_without_promotions(self):
        self.assertEqual(self.packet["candidate_rules"],10)
        self.assertEqual(self.packet["historical_admissions"],0)
        self.assertEqual(self.packet["scientifically_qualified_rules"],0)

    def test_original_c1_passage_ids_not_rewritten(self):
        blocks=source_blocks(C1/"FARAID_PASSAGES.md","P")
        self.assertEqual(len(blocks),23)
        self.assertIn("تعارض در قطعیات",blocks["P-03"])
        self.assertIn("قوهٔ دلالت",blocks["P-17"])

    def test_c1_audit_p17_anchor_misattributed_to_original_id(self):
        result=self.packet["source_verification_index"]["P-17"]
        self.assertEqual(result["status"],"QUARANTINED")
        self.assertIn("ID_DRIFT_OR_QUOTE_MISMATCH",result["blocking_reasons"])

    def test_c1_audit_p04_anchor_misattributed_to_original_id(self):
        result=self.packet["source_verification_index"]["P-04"]
        self.assertIn("ID_DRIFT_OR_QUOTE_MISMATCH",result["blocking_reasons"])

    def test_real_text_match_is_not_sufficient_without_matching_id(self):
        a=alignment("P-01",{"P-01":"متن اصلی درباره وحدت موضوع"},
                    {"P-01":{"anchor":"متن دیگری","found_normalized":True}},
                    {"P-01":"CONFIRMED_AS_TEXT"})
        self.assertEqual(a["status"],"QUARANTINED")
        self.assertIn("ID_DRIFT_OR_QUOTE_MISMATCH",a["blocking_reasons"])

    def test_research_block_match_is_not_scholarly_validity(self):
        a=alignment("P-01",{"P-01":"بسم الله تعالى"},
                    {"P-01":{"anchor":"بسم الله","found_normalized":True}},
                    {"P-01":"CONFIRMED_AS_TEXT"})
        self.assertEqual(a["status"],"ANCHOR_ALIGNS_WITH_RESEARCH_BLOCK_ONLY")
        self.assertFalse(a["human_scholarly_review"])
        self.assertFalse(a["print_edition_verified"])
        self.assertFalse(a["book_text_independently_verified"])

    def test_muse_not_verified_stays_quarantined(self):
        a=alignment("P-07",{"P-07":"النص"},
                    {"P-07":{"anchor":"النص","found_normalized":False}},
                    {"P-07":"NOT_VERIFIED"})
        self.assertIn("ANCHOR_NOT_MATCHED_IN_BOOK_CORPUS",a["blocking_reasons"])
        self.assertIn("MUSE_AUDIT_NOT_VERIFIED",a["blocking_reasons"])

    def test_missing_verification_anchor_is_explicit(self):
        a=alignment("NP-09",{"NP-09":"مادة الخبر"},{})
        self.assertIn("MISSING_VERIFICATION_ANCHOR",a["blocking_reasons"])

    def test_previously_exposed_evidence_is_not_blind(self):
        for r in self.packet["method_rules"]:
            if "P-23" in r["previously_exposed_development_evidence"]:
                self.assertFalse(r["execution_allowed"])

    def test_split_tasaqut_has_separate_binding_and_no_legacy_promotion(self):
        entries={r["rule_key"]:r for r in self.packet["method_rules"]}
        self.assertIn("MR-ANS-AFTER-TASAQUT-A",entries)
        self.assertIn("MR-ANS-AFTER-TASAQUT-B",entries)
        self.assertNotIn("MR-ANS-AFTER-TASAQUT",entries)
        a=entries["MR-ANS-AFTER-TASAQUT-A"]
        b=entries["MR-ANS-AFTER-TASAQUT-B"]
        self.assertNotEqual(a["proof_questions_not_fact_claims"],
                            b["proof_questions_not_fact_claims"])

    def test_unknown_novel_status_does_not_get_scholarly_approval(self):
        self.assertTrue(all(not r["execution_allowed"]
                            for r in self.packet["method_rules"]))
        self.assertTrue(all(r["juristic_verdict"] is None
                            for r in self.packet["method_rules"]))

    def test_all_six_components_are_preserved(self):
        for r in self.packet["method_rules"]:
            self.assertEqual(set(r["six_part_research_statuses"]),set(PARTS))

    def test_primary_and_opposing_sources_are_different_lists(self):
        for r in self.packet["method_rules"]:
            self.assertTrue(all(p["canonical_ref"].startswith(("P-","NP-"))
                                for p in r["source_pointers"]))
            self.assertTrue(all(x.startswith(("CE-","OPP-"))
                                for x in r["adverse_or_limiting_evidence_refs"]))

    def test_input_sha256_does_not_mean_sealed_blind_key(self):
        self.assertTrue(all(len(value)==64 for value
                            in self.packet["input_sha256"].values()))
        self.assertNotIn("sealed_answers",self.packet)

    def test_deterministic_review(self):
        self.assertEqual(json.dumps(self.packet,sort_keys=True,ensure_ascii=False),
                         json.dumps(build_review(),sort_keys=True,ensure_ascii=False))

if __name__=="__main__":
    unittest.main()
