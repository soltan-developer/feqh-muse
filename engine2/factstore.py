# -*- coding: utf-8 -*-
"""FactStore + source registry verification (Test 6).

Three levels are kept strictly apart (per the audit):
  L1 a claim carrying a source_id            -> proves nothing by itself
  L2 the quote verified to exist in a        -> machine-checkable here
     registered source (registry lookup +
     normalized substring match)
  L3 the evidence's probative standing       -> NOT machine-established;
     independently validated                  reported as UNVERIFIED unless
                                                a separate basis is registered
Fact origins: stated_premise (from a registered case statement),
verified_evidence (quote-verified in a registered book/source text),
derived (produced by a rule, carries the rule id),
unverified_hypothesis (never satisfies a rule condition)."""
import json, pathlib, re, unicodedata

D = pathlib.Path(__file__).parent
REGISTRY = json.loads((D / "source_registry.json").read_text(encoding="utf-8"))
_CACHE = {}

def _norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[ً-ٰٟـ]", "", s)          # diacritics + tatweel
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
    return re.sub(r"\s+", " ", s).strip()

def source_text(key):
    if key not in _CACHE:
        _CACHE[key] = (D / REGISTRY[key]["path"]).read_text(encoding="utf-8")
    return _CACHE[key]

def resolve_key(source_id):
    if not source_id:
        return None
    parts = source_id.split(":")
    for n in range(len(parts), 0, -1):
        key = ":".join(parts[:n])
        if key in REGISTRY:
            return key
    return None

def verify_record(rec):
    """Return (status, origin). status in REJECTED_* / QUOTE_VERIFIED."""
    sid = rec.get("source_id")
    if not sid:
        return "REJECTED_NO_SOURCE_ID", None
    key = resolve_key(sid)
    if key is None:
        return "REJECTED_UNREGISTERED_SOURCE", None
    quote = rec.get("quote")
    if not quote or _norm(quote) not in _norm(source_text(key)):
        return "REJECTED_QUOTE_NOT_IN_SOURCE", None
    origin = "stated_premise" if REGISTRY[key]["kind"] == "case_statement" else "verified_evidence"
    return "QUOTE_VERIFIED", origin

ORIGINS = ("stated_premise", "verified_evidence", "derived", "unverified_hypothesis")

class FactStore:
    def __init__(self):
        self.facts = {}   # name -> {"value", "origin", "ref"}
    def assert_fact(self, name, value, origin, ref=None):
        assert origin in ORIGINS, origin
        self.facts[name] = {"value": value, "origin": origin, "ref": ref}
    def derive(self, name, value, rule_id):
        self.facts[name] = {"value": value, "origin": "derived", "ref": rule_id}
    def entry(self, name):
        return self.facts.get(name)
    def effective(self, name):
        """The value a rule may use. unverified_hypothesis and absence both
        yield (None, origin) — a hypothesis never satisfies a condition."""
        e = self.facts.get(name)
        if e is None:
            return None, None
        if e["origin"] == "unverified_hypothesis":
            return None, "unverified_hypothesis"
        return e["value"], e["origin"]
    def plain(self):
        return {k: v["value"] for k, v in self.facts.items() if v["origin"] != "unverified_hypothesis"}
