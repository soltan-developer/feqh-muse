# -*- coding: utf-8 -*-
"""Evidence layer (Everything principle): build ONE structured full-text index
over the book databases at ingest time (write-time structuring), so retrieval
at query time touches only the index. Demo corpus: the 8 local volumes."""
import sqlite3, pathlib, json, time
base = pathlib.Path.home()/"workspace/book-db-inspect"
out = pathlib.Path.home()/"workspace/ansari-engine/evidence_index.db"
books = {1571:"مکاسب ج1",1572:"مکاسب ج2",1573:"مکاسب ج3",1574:"مکاسب ج4",1575:"مکاسب ج5",1576:"مکاسب ج6",
         12227:"فرائد ج1",12228:"فرائد ج2"}
if out.exists(): out.unlink()
idx = sqlite3.connect(out)
idx.execute("CREATE VIRTUAL TABLE blocks USING fts5(book, page, content, tokenize='unicode61')")
idx.execute("CREATE TABLE toc(book TEXT, title TEXT, page INT)")
t0=time.time(); n=0
for bid, label in books.items():
    con = sqlite3.connect(f"file:{base/(str(bid)+'.bin')}?mode=ro", uri=True)
    for page, props in con.execute("SELECT page_number, properties FROM page_contents"):
        try: c = json.loads(props).get("Content","")
        except Exception: continue
        if c.strip():
            idx.execute("INSERT INTO blocks VALUES (?,?,?)", (label, page, c)); n+=1
    for title, pg in con.execute("SELECT title, page_number FROM page_content_references"):
        idx.execute("INSERT INTO toc VALUES (?,?,?)", (label, " ".join(title.split()), pg))
    con.close()
idx.commit()
print(f"indexed {n} blocks in {time.time()-t0:.1f}s -> {out} ({out.stat().st_size/1e6:.1f} MB)")

for term in ["الاستصحاب", "خيار الغبن", "أصالة اللزوم"]:
    t0=time.time()
    rows = idx.execute("SELECT book, page, COUNT(*) FROM blocks WHERE blocks MATCH ? GROUP BY book, page LIMIT 5", (f'"{term}"',)).fetchall()
    dt=(time.time()-t0)*1000
    total = idx.execute("SELECT COUNT(*) FROM blocks WHERE blocks MATCH ?", (f'"{term}"',)).fetchone()[0]
    print(f"query «{term}»: {total} blocks, first hits {rows[:2]} ... in {dt:.1f} ms")
idx.close()
