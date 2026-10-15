# -*- coding: utf-8 -*-
"""Deterministic raw-text extractor (Test 5, Experiment 1).

NOT a general NLP system: a small set of ordered, auditable phrase patterns
for the phrase families used in the test cases. Every extracted value is an
evidence record carrying the exact matched span as its quote. Anything not
matched extracts NOTHING (the fact stays absent -> UNKNOWN downstream).
The extractor never guesses, never defaults, and never uses the expected
verdict to choose a pattern."""
import re

PATTERNS = [
    # (rule_id, fact, value, tier, kind, regex)
    ("EX-SULH", "sulh_present", True, 1, "tasrih",
     r"مصالحه کرده‌اند|مصالحه می‌کنند|صلح کرده‌اند"),
    ("EX-ITLAQ", "wording", "itlaq", 1, "tasrih",
     r"عبارت مصالحه مطلق است|عبارت[^\n]*مطلق"),
    ("EX-NO-INFO", "explicit_no_further_info", True, 1, "tasrih",
     r"اطلاعات دیگری نداریم|هیچ اطلاعاتی[^\n]*نداریم"),
    ("EX-W1-INSIRAF", "itlaq_scope", "limited", 3, "witness",
     r"شاهد نخست[^\n]*منصرف بوده است"),
    ("EX-W2-SCOPEALL", "itlaq_scope", "all", 3, "witness",
     r"شاهد دوم[^\n]*تمام مراتب غبن را شامل می‌شده است"),
    ("EX-INSIRAF-WITNESS", "itlaq_scope", "limited", 3, "witness",
     r"یک شاهد معتبر[^\n]*عرف این معامله[^\n]*فقط ناظر به غبن متعارف"),
    ("EX-SCOPEALL-QARINA", "itlaq_scope", "all", 3, "witness",
     r"قرینه[^\n]*تمام مراتب غبن را دربرمی‌گرفته|تمام مراتب غبن را دربرمی‌گرفته است"),
    ("EX-EXPERT-URF", "itlaq_scope", "limited", 2, "expert_urf",
     r"گزارش کارشناسی عرف[^\n]*منصرف است"),
]

def extract(text, case_id):
    """Return a list of evidence records extracted from the raw text."""
    records = []
    for rid, fact, value, tier, kind, rx in PATTERNS:
        m = re.search(rx, text)
        if m:
            records.append({
                "fact": fact, "value": value, "tier": tier, "kind": kind,
                "source_id": f"RAW:{case_id}:{rid}",
                "quote": m.group(0),
                "extractor_rule": rid,
            })
    return records
