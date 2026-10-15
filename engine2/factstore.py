# -*- coding: utf-8 -*-
"""FactStore v2 + source registry + citation licenses (Test 7).

Trust boundary (the audit's core demand):
- assert_fact() is the PREMISE path only. It refuses origin
  'verified_evidence' outright — no caller can mint verified trust by
  choosing a label.
- Verified facts enter ONLY through admit_record(), which internally runs
  (1) source authenticity (registry), (2) quote existence in the source,
  (3) citation LICENSE: the quote must actually license the claimed
  (fact, value) — either because a deterministic extractor rule re-matches
  on the quote, or because a registered inference license matches.
  An attributed-but-unlicensed claim is preserved in .claims, inert.
- The store keeps EVERY entry per fact (no silent overwrite); two
  different non-hypothesis values make effective() return CONFLICT.
- Probative standing (does the source's content deserve belief) is still
  NOT machine-established and is reported UNVERIFIED by callers."""
import json, pathlib, re, unicodedata

D = pathlib.Path(__file__).parent
REGISTRY = json.loads((D / "source_registry.json").read_text(encoding="utf-8"))
LICENSES = json.loads((D / "inference_licenses.json").read_text(encoding="utf-8"))["licenses"]
_CACHE = {}

def _norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"[ً-ٰٟـ]", "", s)
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
    """Attribution levels 1-2. Returns (status, origin)."""
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

def check_license(rec):
    """Does this quote license this (fact, value)? Returns a license id or None."""
    if rec.get("extractor_rule"):
        import extractor
        pats = {p[0]: p for p in extractor.PATTERNS}
        p = pats.get(rec["extractor_rule"])
        if p and p[1] == rec.get("fact") and p[2] == rec.get("value") and re.search(p[5], rec.get("quote", "")):
            return f"extractor:{rec['extractor_rule']}"
    key = resolve_key(rec.get("source_id", ""))
    kind = REGISTRY[key]["kind"] if key else None
    for lic in LICENSES:
        if lic["fact"] == rec.get("fact") and lic["value"] == rec.get("value") \
           and lic["source_kind"] == kind and re.search(lic["quote_regex"], rec.get("quote", "")):
            return f"registry:{lic['fact']}={lic['value']}"
    return None

ORIGINS = ("stated_premise", "verified_evidence", "derived", "unverified_hypothesis")

class FactStore:
    def __init__(self):
        self.entries = {}   # name -> [ {value, origin, ref, resolution, meta} ]
        self.claims = []    # attributed-but-unlicensed records (inert, preserved)
    # --- premise path ---
    def assert_fact(self, name, value, origin, ref=None):
        if origin == "verified_evidence":
            raise ValueError("trust boundary: verified_evidence can only enter via admit_record()")
        assert origin in ORIGINS, origin
        self.entries.setdefault(name, []).append({"value": value, "origin": origin, "ref": ref, "resolution": False, "meta": None})
    def derive(self, name, value, rule_id):
        self.entries.setdefault(name, []).append({"value": value, "origin": "derived", "ref": rule_id, "resolution": True, "meta": None})
    # --- evidence path (the ONLY way to verified/premise-grade evidence) ---
    def admit_record(self, rec):
        """Returns (status, origin). status: ADMITTED_LICENSED /
        ATTRIBUTED_UNLICENSED / REJECTED_* / HYPOTHESIS_ONLY."""
        status, origin = verify_record(rec)
        if status != "QUOTE_VERIFIED":
            return status, None
        if rec.get("downgraded") == "hypothesis":
            self.entries.setdefault(rec["fact"], []).append({"value": rec["value"], "origin": "unverified_hypothesis", "ref": rec.get("source_id"), "resolution": False, "meta": rec})
            return "HYPOTHESIS_ONLY", "unverified_hypothesis"
        lic = check_license(rec)
        if lic is None:
            self.claims.append(rec)
            return "ATTRIBUTED_UNLICENSED", None
        self.entries.setdefault(rec["fact"], []).append({"value": rec["value"], "origin": origin, "ref": rec.get("source_id"), "resolution": False, "meta": rec})
        return "ADMITTED_LICENSED", origin
    # --- reads ---
    def entry(self, name):
        es = self.entries.get(name, [])
        return es[-1] if es else None
    def all_entries(self, name):
        return list(self.entries.get(name, []))
    def effective(self, name):
        es = self.entries.get(name, [])
        if not es:
            return None, None
        res = [e for e in es if e["resolution"]]
        if res:
            return res[-1]["value"], res[-1]["origin"]
        live = [e for e in es if e["origin"] != "unverified_hypothesis"]
        if not live:
            return None, "unverified_hypothesis"
        vals = {json.dumps(e["value"], sort_keys=True, ensure_ascii=False) for e in live}
        if len(vals) > 1:
            return "CONFLICT", live[0]["origin"]
        return live[0]["value"], live[0]["origin"]
    def plain(self):
        out = {}
        for name in self.entries:
            v, o = self.effective(name)
            if v is not None and v != "CONFLICT":
                out[name] = v
        return out
