# -*- coding: utf-8 -*-
"""Ansari Engine CLI — structured case in, ruling + trace out.
Usage: python3 ask.py case.json   |   echo '{...}' | python3 ask.py -"""
import json, sys
sys.path.insert(0, "/home/hatch/workspace/ansari-engine")
from engine import run

src = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
case = json.loads(src)
r = run(case)
state_fa = {"categorical": "قاطع", "conditional": "مشروط", "abstain": "توقف/ارجاع"}[r["state"]]
print(f"حکم: {r['ruling']}")
print(f"وضعیت: {state_fa}")
print(f"قواعد به‌کاررفته: {', '.join(r['rule_refs']) or '—'}")
print("ردّ تصمیم:")
for s in r["trace"]:
    print(f"  · {s}")
