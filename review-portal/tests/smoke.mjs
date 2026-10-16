import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Script } from 'node:vm';
const folder=new URL('../',import.meta.url);
const read=(file)=>readFileSync(new URL(file,folder),'utf8');
const data=JSON.parse(read('data/review-data.json'));
const html=read('index.html');
const css=read('styles.css');
const js=read('app.js');
const parts=['scope','activation','defeaters','exceptions','conflict_policy','principle'];
const assertions=[];
function check(name,fn){fn();assertions.push(name);}
check('browser JavaScript syntax',()=>new Script(js,{filename:'app.js'}));
check('C4 dataset schema and non-admission',()=>{
  assert.equal(data.schema_version,'feqh-scholar-review-portal-v1');
  assert.equal(data.status,'RESEARCH_ONLY_NOT_INDEPENDENTLY_SCHOLARLY_APPROVED');
  assert.equal(data.rules.length,10);
  assert.equal(data.sources.length,34);
});
check('canonical source identities are unique and byte-digest intact',()=>{
  const ids=new Set();
  for(const s of data.sources){
    assert.match(s.id,/^ANS-\d+-R\d+-S\d+$/);
    assert.ok(!ids.has(s.id),'duplicate source ID '+s.id);ids.add(s.id);
    assert.equal(s.id.split('-R')[0].replace('ANS-',''),s.book);
    assert.equal(+s.id.match(/-R(\d+)-/)[1],s.record);
    assert.equal(s.hash,createHash('sha256').update(s.quote,'utf8').digest('hex'));
    assert.equal(s.printEdition,'PRINT_EDITION_UNKNOWN');
    assert.ok(s.quote.length>=5);
  }
});
check('ten unique rules have six linked parts',()=>{
  const ruleIds=new Set(),ids=new Set(data.sources.map(s=>s.id));
  for(const r of data.rules){
    assert.ok(!ruleIds.has(r.id));ruleIds.add(r.id);
    assert.deepEqual(Object.keys(r.components).sort(),[...parts].sort());
    for(const cell of Object.values(r.components)){
      assert.ok(cell.status);
      for(const ref of cell.canonicalBackings){
        assert.ok(ids.has(ref),r.id+' dangling citation '+ref);
      }
      for(const adverse of cell.adverseRefs)assert.match(adverse,/^(CE-|OPP-)/);
    }
  }
  assert.equal(ruleIds.size,10);
  assert.ok(ruleIds.has('MR-ANS-AFTER-TASAQUT-A'));
  assert.ok(ruleIds.has('MR-ANS-AFTER-TASAQUT-B'));
  assert.ok(!ruleIds.has('MR-ANS-AFTER-TASAQUT'));
});
check('localized shell has required interaction controls',()=>{
  assert.match(html,/<html lang="fa" dir="rtl">/);
  for(const id of ['rule-list','rule-view','reviewer-name','edition-note','export-dialog','download-json','download-md','import-input','theme-toggle'])
    assert.ok(html.includes('id="'+id+'"'),id);
  assert.ok(html.includes('app.js')&&html.includes('styles.css'));
});
check('all rule responses are explicitly local and non-historical',()=>{
  assert.ok(js.includes('localStorage.setItem'));
  assert.ok(js.includes('submitted_at'));
  assert.ok(js.includes('!!r.submitted_at'));
  assert.ok(js.includes('historical_admissions:0'));
  assert.ok(js.includes('reviewer_role:'));
  assert.ok(js.includes('source_sha'));
  assert.ok(js.includes('navigator.share'));
  assert.ok(js.includes('downloadJson'));
  assert.ok(!js.includes('fetch("https://'));
  assert.ok(!js.includes("fetch('https://"));
});
check('static assets make no CDN or backend data requests',()=>{
  assert.ok(!css.includes('@import'));
  assert.ok(!html.includes('src="https://'));
  assert.ok(!html.includes('href="https://'));
  assert.equal((js.match(/\bfetch\(/g)||[]).length,1);
  assert.ok(js.includes("fetch('./data/review-data.json'"));
});
check('review dossier includes research text and open questions',()=>{
  for(const r of data.rules)assert.ok(r.dossierMarkdown&&r.dossierMarkdown.includes('HOLD'));
  assert.ok(data.openNodes.includes('CE-01 OPEN_TENSION'));
});
console.log('PASS review portal static smoke:',assertions.length,'checks');
for(const a of assertions)console.log('✓',a);
