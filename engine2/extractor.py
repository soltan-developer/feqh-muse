# -*- coding: utf-8 -*-
"""Deterministic raw-text extractor v2 (Test 6, mission 2).

Same narrow, auditable pattern family as v1, plus a GUARD layer: before a
positive pattern is accepted, the sentence containing the match is checked
for meaning-inverting markers. Guards never create facts; they only
abstain (with a logged reason) or downgrade the record to a hypothesis.
GUARDS_ENABLED is a deliberate test seam used by the mutation battery."""
import re

GUARDS_ENABLED = True
NEG_MARKERS = ["نمی‌دهد", "نمی دهد", "نشان نداد", "انکار می‌کند", "رد می‌کند", "نفی می‌کند", "نبوده است"]
DOUBT_MARKERS = ["تردید است", "تردید دارد", "معلوم نیست", "مشخص نیست"]
EXCEPTION_MARKERS = ["مگر ", "مگراینکه", "مگر اینکه"]
HYPOTH_MARKERS = ["بر فرض", "فرض کنیم", "فرض شود"]
HEARSAY_MARKERS = ["نقل شده است", "گفته می‌شود", "گفته‌اند", "روایت شده است"]
BLOCK_MARKERS = NEG_MARKERS + DOUBT_MARKERS + EXCEPTION_MARKERS
DOWNGRADE_MARKERS = HYPOTH_MARKERS + HEARSAY_MARKERS

PATTERNS = [
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
    ("EX-WITNESS-SCOPEALL", "itlaq_scope", "all", 3, "witness",
     r"یک شاهد معتبر[^\n]*تمام مراتب غبن"),
    ("EX-SCOPEALL-QARINA", "itlaq_scope", "all", 3, "witness",
     r"قرینه[^\n]*تمام مراتب غبن را دربرمی‌گرفته|تمام مراتب غبن را دربرمی‌گرفته است"),
    ("EX-EXPERT-URF", "itlaq_scope", "limited", 2, "expert_urf",
     r"گزارش کارشناسی عرف[^\n]*منصرف است"),
    ("EX-TASRIH-UMUM", "itlaq_scope", "all", 1, "tasrih",
     r"تصریح شده است که[^\n]*تمام مراتب غبن"),
]

def _sentence_of(text, pos):
    start = max(text.rfind(c, 0, pos) for c in ".!؟؛\n") + 1
    ends = [text.find(c, pos) for c in ".!؟؛\n"]
    ends = [e for e in ends if e != -1]
    end = min(ends) if ends else len(text)
    return text[start:end]

def extract(text, case_id):
    """Return (records, report). Records may carry downgraded='hypothesis';
    report lists every abstention with its guard reason."""
    records, report = [], []
    for rid, fact, value, tier, kind, rx in PATTERNS:
        m = re.search(rx, text)
        if not m:
            continue
        sent = _sentence_of(text, m.start())
        downgraded = None
        if GUARDS_ENABLED:
            hit = next((g for g in BLOCK_MARKERS if g in sent), None)
            if hit:
                report.append({"extractor_rule": rid, "action": "ABSTAIN", "guard": hit, "sentence": sent.strip()})
                continue
            hit = next((g for g in DOWNGRADE_MARKERS if g in sent), None)
            if hit:
                downgraded = "hypothesis"
                report.append({"extractor_rule": rid, "action": "DOWNGRADE_TO_HYPOTHESIS", "guard": hit, "sentence": sent.strip()})
            elif "اگر" in sent[:sent.find(m.group(0)[:20])]:
                downgraded = "hypothesis"
                report.append({"extractor_rule": rid, "action": "DOWNGRADE_TO_HYPOTHESIS", "guard": "اگر (conditional)", "sentence": sent.strip()})
        rec = {"fact": fact, "value": value, "tier": tier, "kind": kind,
               "source_id": f"RAW:{case_id}:{rid}", "quote": m.group(0), "extractor_rule": rid}
        if downgraded:
            rec["downgraded"] = downgraded
        records.append(rec)
    return records, report
