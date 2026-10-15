# -*- coding: utf-8 -*-
"""Blind run (Test 7, mission 7): executes BC1-BC8 against the LOCKED v3
engine and scores against blind_expectations.json (sealed SHA 890eff93...).
No rule changes are permitted after this run; failures are classified,
not repaired."""
import hashlib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import engine_unified as U
import extractor
from factstore import FactStore

D = pathlib.Path(__file__).parent
exp = json.loads((D / "blind_expectations.json").read_text(encoding="utf-8"))
assert hashlib.sha256((D / "blind_expectations.json").read_bytes()).hexdigest() == "890eff93eeafd758e481574f6f8d626b0d3c13a14e047946523db90c6f7391fc", "seal broken"

def store(facts, ref):
    s = FactStore()
    for k, v in facts.items():
        s.assert_fact(k, v, "stated_premise", ref)
    return s

BASE = {"jahl": True, "fahish": True, "iqdam_alim": False}
FULL = {"badhl": "none", "alienation": "none", "maghbun_refusal": False, "ghurd_ayn": "unknown", "dalala_rida": "none", "musamaha_basis": False}
results = {}

f = {**BASE, **FULL, "txn": "bay", "ground_active": ["ijma", "la_darar"], "extension_ground": "la_darar", "badhl": "tendered_gharama", "maghbun_refusal": False}
results["BC1"] = U.run_core(store(f, "BC1"))["verdict"]

f = {"delay_beyond_urf": True, "jahl_khiyar_during_delay": False, "jahl_fawriyya_during_delay": False, "mani_during_delay": False, "nasi_during_delay": True}
results["BC2"] = U.run_fawr(store(f, "BC2"))["verdict"]

results["BC3"] = U.run_t3(store({"act": "isqat", "timing": "post_zuhur", "wording_scope": "umum", "with_iwad": True}, "BC3"))["verdict"]

recs = []
for case in ("B", "C"):
    r, _ = extractor.extract((D / f"raw_test5/{case}.txt").read_text(encoding="utf-8"), case)
    recs += r
o = U.run_sulh(recs)
results["BC4"] = f"{o['verdict']}:{o['stop_id']}"

f = {**BASE, **FULL, "txn": "bay", "ground_active": ["ijma", "la_darar"], "extension_ground": "ijma", "badhl": "tendered_gharama", "maghbun_refusal": True}
results["BC5"] = U.run_core(store(f, "BC5"))["verdict"]

f = {"delay_beyond_urf": True, "jahl_khiyar_during_delay": False, "mani_during_delay": False}
o = U.run_fawr(store(f, "BC6"))
results["BC6"] = f"{o['verdict']}:{o['stop_id']}"

f = {**BASE, "txn": "bay", "ground_active": ["la_darar"], "extension_ground": "la_darar"}
results["BC7"] = U.run_core(store(f, "BC7"))["verdict"]

novel = "شهادت کارشناس عرف تأیید می‌کند اطلاق این معامله به غبن متعارف محدود بوده است."
recs, rep = extractor.extract(novel, "BC8")
sulh = {"fact": "sulh_present", "value": True, "source_id": "RAW:A:EX-SULH", "quote": "مصالحه کرده‌اند", "tier": 1, "kind": "tasrih"}
o = U.run_sulh([sulh] + recs)
results["BC8"] = f"{o['verdict']}:{o['stop_id']}"

score = 0
for cid in sorted(exp):
    got, want = results[cid], exp[cid]["predicted"]
    ok = got == want
    score += ok
    print(f"{cid}: predicted={want} | got={got} | {'MATCH' if ok else 'MISMATCH'}")
print(f"\nBLIND SCORE: {score}/{len(exp)} verdict-level matches (BC2 was a pre-declared expected scientific failure)")
