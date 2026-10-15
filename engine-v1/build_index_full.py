# -*- coding: utf-8 -*-
"""Evidence index over the FULL corpus in ~/workspace/book-corpus/*.bin (FTS5)."""
import sqlite3, json, pathlib, time, sys
src = pathlib.Path.home()/"workspace/book-corpus"
out = pathlib.Path.home()/"workspace/ansari-engine/corpus_index.db"
if out.exists(): out.unlink()
db = sqlite3.connect(out)
db.execute("CREATE VIRTUAL TABLE blocks USING fts5(book, page UNINDEXED, content, tokenize='unicode61')")
t0 = time.time(); total = 0; books = 0; skipped = []
for f in sorted(src.glob("*.bin")):
    try:
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        rows = con.execute("SELECT c.page_number, c.properties FROM page_contents c ORDER BY c.page_number, c.weight").fetchall()
        con.close()
    except Exception as e:
        skipped.append((f.name, str(e)[:60])); continue
    vals = []
    for pg, props in rows:
        try: c = json.loads(props).get("Content","")
        except Exception: continue
        if c and c.strip(): vals.append((f.stem, pg, c))
    db.executemany("INSERT INTO blocks VALUES (?,?,?)", vals)
    total += len(vals); books += 1
db.commit()
print(f"books={books} blocks={total} build={time.time()-t0:.1f}s size={out.stat().st_size/1e6:.1f}MB")
if skipped: print("skipped:", skipped)
for q in sys.argv[1:]:
    t0=time.time()
    n = db.execute("SELECT COUNT(*) FROM blocks WHERE blocks MATCH ?", (q,)).fetchone()[0]
    print(f"{q}: {n} blocks in {(time.time()-t0)*1000:.1f} ms")
    for b,pg,c in db.execute("SELECT book,page,substr(content,1,80) FROM blocks WHERE blocks MATCH ? LIMIT 2", (q,)):
        print(f"   [{b} p{pg}]", " ".join(c.split())[:80])
db.close()
