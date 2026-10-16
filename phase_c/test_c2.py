# -*- coding: utf-8 -*-
import copy
import hashlib
import json
import unittest

from phase_c.c2_compile import build_packet, PARTS
from phase_c.c2_predicates import preflight


class C2FormulationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet=build_packet()

    def test_source_and_event_inventory(self):
        self.assertEqual(self.packet["source_passage_count"],23)
        self.assertEqual(self.packet["event_count"],10)
        self.assertEqual(self.packet["contrary_count"],7)
        self.assertEqual(self.packet["open_question_count"],7)

    def test_all_nine_candidates_mapped(self):
        rules=self.packet["method_rule_dossiers"]
        self.assertEqual(len(rules),9)
        self.assertEqual(len({x["rule_key"] for x in rules}),9)
        self.assertEqual(self.packet["catalog_operator_count"],11)

    def test_six_parts_with_exact_counts(self):
        self.assertEqual(self.packet["research_component_counts"],{
            "supported":46,"partial":7,"unsupported":1})
        self.assertTrue(all(set(r["six_parts"])==set(PARTS)
                            for r in self.packet["method_rule_dossiers"]))

    def test_research_support_never_implies_qualified(self):
        for r in self.packet["method_rule_dossiers"]:
            self.assertEqual(r["historical_admission"],"HOLD")
            self.assertFalse(r["may_execute_in_engine"])
            self.assertFalse(r["may_attribute_historical_verdict"])
            for part in r["six_parts"].values():
                self.assertEqual(part["independent_human_review"],"NOT_PERFORMED")
                self.assertEqual(part["source_match_review"],"NOT_PERFORMED")
        self.assertEqual(self.packet["historical_rule_admissions"],0)

    def test_exception_gap_is_exposed(self):
        r=next(r for r in self.packet["method_rule_dossiers"]
               if r["rule_key"]=="MR-ANS-AFTER-TASAQUT")
        self.assertEqual(r["six_parts"]["exceptions"]["research_status"],"unsupported")

    def test_distinguish_jam_tarjih_takhyir(self):
        rules={x["rule_key"]:x["technical_operator"]
               for x in self.packet["method_rule_dossiers"]}
        self.assertEqual(rules["MR-ANS-JAM-QARINA"],"licensed-jam")
        self.assertEqual(rules["MR-ANS-TARJIH-OPEN"],"tarjih-candidate-assessment")
        self.assertEqual(rules["MR-ANS-TAKHYIR-LAST"],"takhyir-eligibility-gate")
        self.assertEqual(len(set(rules.values())),8)

    def test_cross_source_not_qualified_by_exposed_case(self):
        issues=self.packet["design_review_issues"]
        self.assertTrue(any(o["problem"]=="DEVELOPMENT_CASE_NOT_INDEPENDENT"
                            for o in issues))
        self.assertTrue(any(o["problem"]=="CONTRARY_REFERENCE_NOT_PRIMARY_PROOF"
                            for o in issues))

    def test_integrity_manifest_sha_lengths(self):
        self.assertEqual(len(self.packet["source_manifest_sha256"]),7)
        self.assertTrue(all(len(v)==64 for v in
                            self.packet["source_manifest_sha256"].values()))

    def test_absent_question_is_unknown_not_false(self):
        result=preflight(["same_subject","same_time"],{"same_subject":"true"})
        self.assertEqual(result["technical_preflight"],"STOP_UNVERIFIED_PREMISES")

    def test_false_does_not_turn_into_unknown(self):
        result=preflight(["same_subject"],{"same_subject":"false"})
        self.assertEqual(result["technical_preflight"],"NO_CANDIDATE_ROUTE")

    def test_conflict_is_distinct_from_unknown(self):
        result=preflight(["same_subject","same_respect"],
                         {"same_subject":"unknown","same_respect":"conflict"})
        self.assertEqual(result["technical_preflight"],"STOP_CONFLICTING_PREMISES")

    def test_fully_stated_premises_do_not_authorize_fatwa(self):
        result=preflight(["q1","q2"],{"q1":"true","q2":"true"})
        self.assertEqual(result["technical_preflight"],"HOLD_SCIENTIFIC_QUALIFICATION")
        self.assertFalse(result["historical_admission"])
        self.assertIsNone(result["juristic_verdict"])

    def test_unrecognized_or_malformed_predicate_rejected(self):
        with self.assertRaises(ValueError):
            preflight(["q1"],{"q2":"true"})
        with self.assertRaises(ValueError):
            preflight(["q1"],{"q1":"yes"})
        with self.assertRaises(ValueError):
            preflight([],{})

    def test_compiled_packet_is_deterministic(self):
        self.assertEqual(json.dumps(self.packet,sort_keys=True,ensure_ascii=False),
                         json.dumps(build_packet(),sort_keys=True,ensure_ascii=False))

if __name__=="__main__":
    unittest.main()
