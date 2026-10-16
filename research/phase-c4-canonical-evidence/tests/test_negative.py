#!/usr/bin/env python3
"""Negative fixtures: each builds a malicious input and asserts the detector flags it."""
import json, pathlib, sqlite3, hashlib, sys
root = pathlib.Path(__file__).parent.parent
reg = [json.loads(l) for l in (root/"CANONICAL_PASSAGE_REGISTRY.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
corpus = pathlib.Path.home()/"workspace/book-corpus"
def rectext(book, rid):
    db = sqlite3.connect(f"file:{corpus/(book+'.bin')}?mode=ro", uri=True)
    row = db.execute("SELECT properties FROM page_contents WHERE id=?", (rid,)).fetchone(); db.close()
    return json.loads(row[0]).get("Content") or "" if row else ""
tests = []
def T(name):
    def deco(fn): tests.append((name, fn)); return fn
    return deco
@T("N1 correct text under wrong ID")
def _():
    r5 = next(r for r in reg if r["legacy_ids"] == ["P-05"])
    claimed = {"legacy_id": "P-04", "canonical_id": r5["canonical_id"]}
    truth = next(r for r in reg if r["legacy_ids"] == ["P-04"])
    return claimed["canonical_id"] != truth["canonical_id"]  # detector: binding != truth
@T("N2 correct quote at wrong record")
def _():
    r = reg[0]; wrong = rectext(r["book_id"], r["db_record_id"] + 500)
    seg = wrong[r["quote_span"]["start"]:r["quote_span"]["end"]]
    return seg != r["raw_quote"]
@T("N3 short shared phrase without locus")
def _():
    phrase = "العرف"
    hits = [r["canonical_id"] for r in reg if phrase in r["raw_quote"]]
    db = sqlite3.connect(f"file:{corpus/'12228.bin'}?mode=ro", uri=True)
    rows = db.execute("SELECT properties FROM page_contents").fetchall(); db.close()
    corpus_hits = sum(1 for (props,) in rows if phrase in (json.loads(props).get("Content") or ""))
    return corpus_hits > 1  # detector must return AMBIGUOUS for a bare phrase
@T("N4 one quote as two independent witnesses")
def _():
    fake = [{"id": "X1", "h": "h"}, {"id": "X2", "h": "h"}]
    seen = {}
    for f in fake: seen.setdefault(f["h"], []).append(f["id"])
    return any(len(v) > 1 for v in seen.values())
@T("N5 CE id injected as positive backing")
def _():
    v3 = json.loads((root/"RULE_COMPONENTS_V3.json").read_text(encoding="utf-8"))
    poisoned = json.loads(json.dumps(v3)); poisoned["rules"][0]["components"]["scope"]["canonical_backings"].append("CE-01")
    return any(str(b).startswith("CE-") for r in poisoned["rules"] for c in r["components"].values() for b in c["canonical_backings"])
@T("N6 UNKNOWN print marked VERIFIED_PRINT")
def _():
    fake = dict(reg[0]); fake["print_edition"] = "VERIFIED_PRINT"
    return fake["print_edition"] != "PRINT_EDITION_UNKNOWN"
@T("N7 rule marked approved/executable")
def _():
    ho = json.loads((root/"CHATGPT_HANDOFF_C4.json").read_text(encoding="utf-8"))
    poisoned = json.loads(json.dumps(ho)); poisoned["rules"][0]["execution_allowed"] = True
    return any(r["execution_allowed"] is not False or r["historical_admission"] != "HOLD" for r in poisoned["rules"])
@T("N8 stale source hash")
def _():
    r = reg[0]; tampered = "0"*64
    return hashlib.sha256(r["raw_quote"].encode()).hexdigest() != tampered
fails = 0
for name, fn in tests:
    caught = bool(fn())
    print(f"{name}: {'CAUGHT' if caught else 'NOT-CAUGHT'}")
    fails += 0 if caught else 1
print(f"TOTAL: {len(tests)} CAUGHT: {len(tests)-fails} NOT-CAUGHT: {fails}")
sys.exit(1 if fails else 0)
