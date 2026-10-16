# -*- coding: utf-8 -*-
"""Adversarial Phase C5 tests: fail-closed on mutated research identities."""
import copy
import unittest
from phase_c.c5_canonical_intake import (
    build_intake, load_sources, validate, sha, verify_external_corpus
)

class C5CanonicalIntake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture,_=load_sources()

    def changed(self):
        return copy.deepcopy(self.fixture)

    def rejected(self, data):
        with self.assertRaises(ValueError):
            validate(data)

    def test_real_c4_34_passage_structural_consistency(self):
        result=validate(self.fixture)
        self.assertEqual(result["canonical_passages"],34)
        self.assertEqual(result["six_part_cells"],60)
        self.assertEqual(result["graph_edges"],95)
        self.assertEqual(result["scientifically_admitted_rules"],0)

    def test_book_verification_not_inferred_without_external_book_files(self):
        result=build_intake()
        self.assertEqual(result["source_passages_checked_against_external_corpus"],0)
        self.assertEqual(result["human_scholarly_review"],"NOT_PERFORMED")
        self.assertFalse(result["method_rule_execution_allowed"])

    def test_real_byte_verification_fails_when_corpus_is_missing(self):
        with self.assertRaises(ValueError):
            verify_external_corpus(self.fixture,"/tmp/phase-c5-no-corpus-supplied")

    def test_wrong_legacy_passage_mapping_rejected(self):
        d=self.changed()
        rows=d["C1_C3_CANONICAL_CROSSWALK.json"]["rows"]
        rows[0]["canonical_passage_id"]=rows[1]["canonical_passage_id"]
        self.rejected(d)

    def test_wrong_database_record_rejected(self):
        d=self.changed()
        d["CANONICAL_PASSAGE_REGISTRY.jsonl"][0]["db_record_id"]+=1
        self.rejected(d)

    def test_modified_quote_unmatched_hash_rejected(self):
        d=self.changed()
        d["CANONICAL_PASSAGE_REGISTRY.jsonl"][0]["raw_quote"]="نقل تحریف‌شده"
        self.rejected(d)

    def test_quote_with_forged_matching_sha_but_bad_offsets_rejected(self):
        d=self.changed()
        p=d["CANONICAL_PASSAGE_REGISTRY.jsonl"][0]
        p["raw_quote"]="خیالی"
        p["raw_quote_sha256"]=sha(p["raw_quote"])
        self.rejected(d)

    def test_duplicated_independent_alias_rejected(self):
        d=self.changed()
        d["CANONICAL_PASSAGE_REGISTRY.jsonl"][1]["legacy_ids"]=["P-01"]
        self.rejected(d)

    def test_missing_source_reference_rejected(self):
        d=self.changed()
        d["RULE_COMPONENTS_V3.json"]["rules"][0]["components"]["scope"]["canonical_backings"]=["ANS-FAKE-R999-S01"]
        self.rejected(d)

    def test_altered_component_mapping_rejected(self):
        d=self.changed()
        d["RULE_COMPONENTS_V3.json"]["rules"][0]["components"]["scope"]["canonical_backings"]=[
          d["CANONICAL_PASSAGE_REGISTRY.jsonl"][1]["canonical_id"]]
        self.rejected(d)

    def test_contrary_reference_in_positive_edge_rejected(self):
        d=self.changed()
        e=d["PROVENANCE_GRAPH_EDGES.json"]["edges"][0]
        e["canonical_ref"]="CE-01"
        self.rejected(d)

    def test_provenance_edge_removed_rejected(self):
        d=self.changed()
        d["PROVENANCE_GRAPH_EDGES.json"]["edges"].pop()
        self.rejected(d)

    def test_made_up_print_edition_rejected(self):
        d=self.changed()
        d["SOURCE_REGISTRY_LOCKED.json"]["sources"][0]["edition_status"]="VERIFIED_PRINT"
        self.rejected(d)

    def test_invented_human_review_rejected(self):
        d=self.changed()
        d["CHATGPT_HANDOFF_C4.json"]["human_review_state"]="COMPLETED"
        self.rejected(d)

    def test_invented_historical_execution_rejected(self):
        d=self.changed()
        d["RULE_COMPONENTS_V3.json"]["rules"][0]["execution_allowed"]=True
        self.rejected(d)

    def test_split_rule_collapse_rejected(self):
        d=self.changed()
        d["RULE_COMPONENTS_V3.json"]["rules"][0]["rule_key"]="MR-ANS-AFTER-TASAQUT"
        self.rejected(d)

    def test_original_blocker_ledger_cannot_be_silently_wiped(self):
        d=self.changed()
        d["C3_BLOCKER_RESOLUTION_MATRIX.json"]["items"]=[]
        self.rejected(d)

    def test_renaming_one_graph_origin_rejected(self):
        d=self.changed()
        d["PROVENANCE_GRAPH_EDGES.json"]["edges"][0]["from"]="MR-ANS-UNKNOWN.scope"
        self.rejected(d)

    def test_no_secret_blind_test_content(self):
        d=self.changed()
        d["CHATGPT_HANDOFF_C4.json"]["blind_test_data"]="SEALED_ANSWERS_DISCLOSED"
        self.rejected(d)

if __name__=="__main__":
    unittest.main()
