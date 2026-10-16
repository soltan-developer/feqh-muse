#!/usr/bin/env python3
"""C4 structural+content validator. Technical only — never a scholarly verdict."""
import json, pathlib, sys, hashlib, re
root = pathlib.Path(__file__).parent
errors = []
def norm(s):
    s = re.sub(r'[\u0640\u064B-\u0652]', '', s or '')
    return re.sub(r'\s+', ' ', s).strip()
# 1. JSON/JSONL validity
for f in list(root.rglob("*.json")) + list(root.rglob("*.jsonl")):
    try:
        if f.suffix == ".jsonl": [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        else: json.loads(f.read_text(encoding="utf-8"))
    except Exception as e: errors.append(f"parse: {f.name}: {e}")
# 2. canonical uniqueness + quote-at-locus re-verification against local corpus (if present)
reg = [json.loads(l) for l in (root/"CANONICAL_PASSAGE_REGISTRY.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
ids = [r["canonical_id"] for r in reg]
if len(ids) != len(set(ids)): errors.append("canonical id collision")
corpus = pathlib.Path.home()/"workspace/book-corpus"
if corpus.exists():
    import sqlite3
    cache = {}
    def rectext(book, rid):
        if book not in cache: cache[book] = sqlite3.connect(f"file:{corpus/(book+'.bin')}?mode=ro", uri=True)
        row = cache[book].execute("SELECT properties FROM page_contents WHERE id=?", (rid,)).fetchone()
        return json.loads(row[0]).get("Content") or "" if row else ""
    for r in reg:
        txt = rectext(r["book_id"], r["db_record_id"])
        seg = txt[r["quote_span"]["start"]:r["quote_span"]["end"]]
        if seg != r["raw_quote"]: errors.append(f"{r['canonical_id']}: span/raw mismatch")
        if hashlib.sha256(r["raw_quote"].encode()).hexdigest() != r["raw_quote_sha256"]: errors.append(f"{r['canonical_id']}: hash mismatch")
        if r["print_edition"] != "PRINT_EDITION_UNKNOWN": errors.append(f"{r['canonical_id']}: print edition must stay UNKNOWN")
else:
    print("NOTE: local corpus absent — locus re-verification skipped")
# 3. crosswalk destinations exist
cw = json.loads((root/"C1_C3_CANONICAL_CROSSWALK.json").read_text(encoding="utf-8"))
idset = set(ids)
for row in cw["rows"]:
    refs = row.get("canonical_passage_id") or []
    if isinstance(refs, str): refs = [refs]
    for x in refs:
        if x not in idset: errors.append(f"crosswalk dangling ref {x}")
# 4. components: 10 rules x 6 cells, HOLD, no execution; CE never a positive backing
v3 = json.loads((root/"RULE_COMPONENTS_V3.json").read_text(encoding="utf-8"))
if len(v3["rules"]) != 10: errors.append("rule count != 10")
for r in v3["rules"]:
    if r["execution_allowed"] is not False: errors.append(f"{r['rule_key']}: execution_allowed")
    if len(r["components"]) != 6: errors.append(f"{r['rule_key']}: components != 6")
    for comp, cell in r["components"].items():
        for b in cell["canonical_backings"]:
            if b not in idset: errors.append(f"{r['rule_key']}.{comp}: dangling backing {b}")
            if str(b).startswith("CE-"): errors.append(f"{r['rule_key']}.{comp}: CE as positive backing")
# 5. handoff invariants
ho = json.loads((root/"CHATGPT_HANDOFF_C4.json").read_text(encoding="utf-8"))
if ho.get("human_review_state") != "NOT_PERFORMED": errors.append("human_review_state must be NOT_PERFORMED")
for r in ho["rules"]:
    if r["historical_admission"] != "HOLD" or r["execution_allowed"] is not False: errors.append(f"handoff {r['rule_key']} invariants")
print("ERRORS:", len(errors))
for e in errors: print(" -", e)
sys.exit(1 if errors else 0)
