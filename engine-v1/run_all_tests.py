# -*- coding: utf-8 -*-
"""One-command test suite for everything built so far."""
import subprocess, sys, sqlite3, time, pathlib, json
E = pathlib.Path.home()/"workspace/ansari-engine"
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout + r.stderr

print("=" * 60); print("۱) موتور v1 — رگرسیون ۱۲ کیس مکاسب")
out = run([sys.executable, str(E/"run_tests.py")])
print("\n".join(l for l in out.splitlines() if "PASS" in l or "FAIL" in l or "/" in l) or out[-400:])

print("=" * 60); print("۲) موتور دوم — دروازه‌ها و کاوشگر ۱ (۵ سناریو)")
out = run([sys.executable, str(E/"engine2/run_probe1.py")])
for l in out.splitlines():
    if any(k in l for k in ("ADMITTED", "kept in hypothesis", "PASS", "FAIL", "OVERALL")): print(" ", l)

print("=" * 60); print("۳) ایندکس شواهد کل پیکره — سه پرس‌وجوی زمان‌دار")
db = sqlite3.connect(E/"corpus_index.db")
print("  بلوک‌های ایندکس‌شده:", db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0],
      "| کتاب‌ها:", db.execute("SELECT COUNT(DISTINCT book) FROM blocks").fetchone()[0])
for q in ["الاستصحاب", "خيار الغبن", "لا ضرر"]:
    t0 = time.time()
    n = db.execute("SELECT COUNT(*) FROM blocks WHERE blocks MATCH ?", (q,)).fetchone()[0]
    print(f"  «{q}»: {n} بلوک در {(time.time()-t0)*1000:.1f} ms")
print("=" * 60); print("تمام شد. برای تست دستی، راهنما در پیام همراه است.")
