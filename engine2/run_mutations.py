# -*- coding: utf-8 -*-
"""Mutation battery (Test 6, Y16): copy the engine, apply ONE controlled
sabotage per copy, and verify the corresponding behavioral probe FAILS.
If a probe still PASSes under its sabotage, the test suite has no teeth."""
import pathlib, shutil, subprocess, sys

SRC = pathlib.Path(__file__).parent
MUTS = [
    ("M1-license-off", "factstore.py", "lic = check_license(rec)", 'lic = "sabotaged"', "P-license"),
    ("M2-guards-off", "extractor.py", "GUARDS_ENABLED = True", "GUARDS_ENABLED = False", "P-neg"),
    ("M3-fawr-default", "engine_unified.py", '"verdict": "STOP", "stop_id": "STOP-T6-INSUFFICIENT-FACTS"', '"verdict": "NO_DELAY_ISSUE", "stop_id": None', "P-fawr"),
    ("M4-hypothesis-admissible", "factstore.py", 'live = [e for e in es if e["origin"] != "unverified_hypothesis"]', "live = list(es)", "P-hyp"),
    ("M5-order-dependent", "engine_unified.py", 'for r in sorted(rules, key=lambda x: x["id"]):', "for r in rules:", "P-order"),
]
PROBES = ["P-forge", "P-license", "P-neg", "P-fawr", "P-hyp", "P-order"]

def run_probe(eng_dir, probe):
    r = subprocess.run([sys.executable, str(SRC / "mutation_probe.py"), str(eng_dir), probe], capture_output=True, text=True)
    return "PROBE-RESULT: PASS" in r.stdout

print("baseline (unmutated engine):")
base = {p: run_probe(SRC, p) for p in PROBES}
for p, ok in base.items():
    print(f"  {p}: {'PASS' if ok else 'FAIL'}")
print("\nmutation table:")
all_caught = all(base.values())
for name, fname, old, new, target in MUTS:
    dst = pathlib.Path(f"/tmp/{name}")
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("__pycache__", "outputs_test4", "inputs_test4"))
    f = dst / fname
    txt = f.read_text(encoding="utf-8")
    assert old in txt, f"patch target not found for {name}"
    f.write_text(txt.replace(old, new, 1), encoding="utf-8")
    caught = not run_probe(dst, target)
    all_caught &= caught
    print(f"  {name}: sabotage in {fname} -> probe {target} {'FAILS (caught)' if caught else 'STILL PASSES (NOT CAUGHT!)'}")
print("\nMUTATION BATTERY:", "PASS — every sabotage caught, baseline green" if all_caught else "FAIL")
import sys as _s; _s.exit(0 if all_caught else 1)
