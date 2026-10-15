# -*- coding: utf-8 -*-
import json, sys
sys.path.insert(0, "/home/hatch/workspace/ansari-engine")
from engine import run

cases = json.load(open("/home/hatch/workspace/ansari-engine/cases.json", encoding="utf-8"))
ok = 0
for c in cases:
    r = run(c["case"])
    passed = (r["ruling"] == c["expected"])
    ok += passed
    print(f"[{'PASS' if passed else 'FAIL'}] #{c['id']} {c['name']}")
    print(f"      ruling={r['ruling']} | state={r['state']} | rules={','.join(r['rule_refs'])}")
    for step in r["trace"]:
        print(f"      · {step}")
print(f"\n== {ok}/{len(cases)} passed")
