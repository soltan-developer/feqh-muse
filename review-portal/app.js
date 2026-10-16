/* Feqh Muse Scholar Review · local-first, research-only, no remote submission. */
(function () {
  'use strict';
  const STORAGE = 'feqh-muse-review-draft-v1';
  const SCHEMA = 'feqh-muse-self-review-v1';
  const PARTS = [
    ['scope','دامنه کاربرد','قاعده در چه مسائل و با چه شرایط موضوعی معتبر است؟'],
    ['activation','شرایط فعال‌سازی','کدام مقدمات باید احراز شوند تا قاعده قابل اعمال باشد؟'],
    ['defeaters','موانع و معارض‌ها','چه قرینه یا دلیل دیگری مسیر قاعده را مسدود می‌کند؟'],
    ['exceptions','استثناها','چه مواردی از شمول ادعا خارج می‌شوند؟'],
    ['conflict_policy','نسبت با سایر قواعد','در برخورد با حکومت، ورود، جمع و ترجیح چه نسبتی دارد؟'],
    ['principle','اصل و مبنای قاعده','آیا اصل ادعا به رأی مختار شیخ مستند است؟']
  ];
  const CHOICES = [
    ['approve','تأیید'],['reject','رد'],['revise','اصلاح'],['defer','تعلیق']
  ];
  const STATUS = {
    DIRECTLY_SUPPORTED:'شاهد مستقیم',
    INFERENTIALLY_SUPPORTED:'استظهار پژوهشی',
    PARTIAL:'پشتوانه جزئی',
    UNKNOWN:'نامعلوم',
    UNSUPPORTED:'فاقد شاهد',
    CONTRADICTED:'مورد نقض',
    NOT_VERIFIED:'تأییدنشده'
  };
  let DATA, draft, selected, activeTab='overview', filter='all', search='', evidenceFocus='', toastTimer;
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value === null || value === undefined ? '' : value)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  const iso = () => new Date().toISOString();
  const byId = (id) => DATA.rules.find(r => r.id===id);
  const sourceById = (id) => DATA.sources.find(s => s.id === id);
  const toast = (message) => {
    const el = $('toast'); el.textContent=message; el.classList.add('visible');
    clearTimeout(toastTimer); toastTimer=setTimeout(() => el.classList.remove('visible'),3800);
  };
  function newDraft() {
    return {review_schema:SCHEMA,source_sha:DATA.source_sha,reviewer:'',edition_note:'',
      created_at:iso(),updated_at:iso(),reviews:{}};
  }
  function reviewFor(id) {
    if (!draft.reviews[id]) draft.reviews[id]={parts:{},decision:'',reason:'',updated_at:null,submitted_at:null};
    for (const [key] of PARTS)
      if (!draft.reviews[id].parts[key]) draft.reviews[id].parts[key]={decision:'',reason:''};
    return draft.reviews[id];
  }
  function restore() {
    let stored=null;
    try {stored=JSON.parse(localStorage.getItem(STORAGE)||'null');} catch (e) {}
    draft=newDraft();
    if (stored && stored.review_schema===SCHEMA && stored.source_sha===DATA.source_sha && typeof stored.reviews==='object') {
      draft.reviewer=String(stored.reviewer||'').slice(0,160);
      draft.edition_note=String(stored.edition_note||'').slice(0,350);
      draft.created_at=stored.created_at||draft.created_at;
      for (const rule of DATA.rules) {
        const r=stored.reviews[rule.id];
        if (!r || typeof r!=='object') continue;
        const clean={parts:{},decision:validDecision(r.decision),reason:String(r.reason||'').slice(0,10000),
          updated_at:r.updated_at||null,submitted_at:r.submitted_at||null};
        for (const [key] of PARTS) {
          const part=r.parts && r.parts[key] ? r.parts[key] : {};
          clean.parts[key]={decision:validDecision(part.decision),reason:String(part.reason||'').slice(0,10000)};
        }
        draft.reviews[rule.id]=clean;
      }
    }
  }
  function validDecision(x){return CHOICES.some(y=>y[0]===x) ? x : '';}
  function save() {
    draft.updated_at=iso();
    try {localStorage.setItem(STORAGE,JSON.stringify(draft)); $('save-indicator').textContent='● ذخیره شد';}
    catch(e) { $('save-indicator').textContent='ذخیره مرورگر ناموفق'; toast('ذخیره مرورگر ممکن نیست؛ خروجی JSON بگیرید.');}
  }
  function partValid(p) {
    return !!p && !!validDecision(p.decision) &&
      (p.decision==='approve' || String(p.reason||'').trim().length>=8);
  }
  function completion(id) {
    const r=reviewFor(id);
    const partsDone=PARTS.filter(([k])=>partValid(r.parts[k])).length;
    const overall=!!validDecision(r.decision) && r.reason.trim().length>=12 &&
      draft.reviewer.trim().length>=2;
    return {partsDone,complete:partsDone===6 && overall,overall};
  }
  function totalDone() {return DATA.rules.filter(r=>completion(r.id).complete).length;}
  function completionBadge(id) {
    const x=completion(id),r=reviewFor(id);
    if (x.complete) return '✓';
    if (r.decision || x.partsDone) return '•';
    return '';
  }
  function renderNav() {
    const n=totalDone(),all=DATA.rules.length;
    $('stat-total').textContent=all; $('stat-done').textContent=n;$('stat-left').textContent=all-n;
    $('side-progress-value').textContent=n+' از '+all;
    $('side-progress-bar').style.width=(100*n/all)+'%';
    $('side-progress-hint').textContent=n===all?'همه پرونده‌ها ثبت شده‌اند؛ گزارش را دریافت کنید.':'با تکمیل شش جزء و تصمیم مستدل، یک پرونده تکمیل می‌شود.';
    const subset=DATA.rules.filter(r=>(filter==='all'||(filter==='completed')===completion(r.id).complete)
      &&(r.title.includes(search)||r.id.toLowerCase().includes(search.toLowerCase())));
    $('rule-list').innerHTML=subset.map(r=>{
      const c=completion(r.id),selectedClass=r.id===selected?' active':'';
      return '<button type="button" class="rule-nav-item'+selectedClass+'" data-action="navigate" data-id="'+esc(r.id)+'" aria-current="'+(selectedClass?'page':'false')+'">'
        +'<span class="nav-number">'+String(r.priority).padStart(2,'0')+'</span>'
        +'<span class="nav-name">'+esc(r.title)+'</span>'
        +'<span class="nav-icon'+(c.complete?' done':'')+'">'+completionBadge(r.id)+'</span></button>';
    }).join('') || '<div style="padding:20px;color:var(--muted);font-size:11px">پرونده‌ای یافت نشد.</div>';
  }
  function badge(status) {
    const cls=status==='DIRECTLY_SUPPORTED'?'accent':status==='UNKNOWN'||status==='PARTIAL'?'warning':'';
    return '<span class="tag '+cls+'">'+esc(STATUS[status]||status)+'</span>';
  }
  function refs(ids) {
    return (ids||[]).map(id=>'<button type="button" class="evidence-pill" data-action="source" data-source="'+esc(id)+'">'+esc(id)+'</button>').join('');
  }
  function tabs() {
    return '<div class="top-steps" role="tablist" aria-label="مراحل بررسی">'+
      [['overview','01','پرونده و مبانی'],['evidence','02','متن و شواهد'],['review','03','داوری و نظر شما']]
      .map(t=>'<button role="tab" aria-selected="'+String(activeTab===t[0])+'" class="step-tab'+(activeTab===t[0]?' active':'')+'" data-action="tab" data-tab="'+t[0]+'"><span>'+t[1]+'</span>'+t[2]+'</button>').join('')+'</div>';
  }
  function renderRule() {
    const rule=byId(selected);
    if(!rule)return;
    const c=completion(rule.id),rr=reviewFor(rule.id);
    const k=rule.id;
    const top='<section class="rule-hero"><div class="rule-headline"><div>'+
      '<div class="rule-kicker">پرونده پژوهشی '+String(rule.priority).padStart(2,'0')+' / '+DATA.rules.length+'</div>'+
      '<h2>'+esc(rule.title)+'</h2><div class="rule-code">'+esc(k)+'</div></div>'+
      '<span class="tag '+(c.complete?'accent':'warning')+'">'+(c.complete?'ثبت داوری تکمیل':'در حال بررسی')+'</span></div>'+
      '<div class="badges"><span class="tag warning">'+esc(rule.grade)+'</span>'+
      '<span class="tag">پژوهشی · غیرقابل‌اجرا</span><span class="tag">'+c.partsDone+' از ۶ جزء بررسی شده</span></div>'+tabs()+'</section>';
    let detail='';
    if(activeTab==='overview') detail=renderOverview(rule);
    else if(activeTab==='evidence')detail=renderEvidence(rule);
    else detail=renderReview(rule,rr,c);
    const index=DATA.rules.findIndex(r=>r.id===k);
    let pager='<div class="pager"><button type="button" class="secondary" data-action="navigate" data-id="'+esc(DATA.rules[Math.max(0,index-1)].id)+'" '+(index===0?'disabled':'')+'>→ پرونده قبل</button>'+
      '<button type="button" class="secondary" data-action="navigate" data-id="'+esc(DATA.rules[Math.min(DATA.rules.length-1,index+1)].id)+'" '+(index===DATA.rules.length-1?'disabled':'')+'>پرونده بعد ←</button></div>';
    $('rule-view').innerHTML=top+detail+pager;
  }
  function renderOverview(rule) {
    let cs=PARTS.map(([key,label,desc])=>{
      const part=rule.components[key];
      return '<article class="mini-card"><div class="mini-card-title"><span>'+esc(label)+'</span>'+badge(part.status)+'</div>'+
        '<p>'+esc(desc)+'</p><div class="evidence-links">'+refs(part.canonicalBackings)+
        (part.adverseRefs&&part.adverseRefs.length?'<span class="tag danger">مخالف: '+esc(part.adverseRefs.join('، '))+'</span>':'')+
        '</div><button type="button" data-action="review-part" data-part="'+key+'">ثبت نظر این جزء ←</button></article>';
    }).join('');
    return '<section class="tab-content"><div class="section-card"><div class="heading-row"><h3>شناخت پرونده</h3><span class="tag">نسخه C4</span></div>'+
      '<p>این قاعده از متون شیخ استخراج و توسط میوز به‌صورت «نامزد روش اجتهادی» صورت‌بندی شده است. رنگ و درجه شواهد، حاصل پژوهش اولیه است و به‌معنی تأیید علمی مستقل نیست.</p>'+
      '<div class="warning-inline">شناسه‌های کانونی به متن دیتابیس مرتبط‌اند؛ چاپ کاغذی و صفحه چاپی هنوز مشخص نشده است.</div></div>'+
      '<div class="section-card"><div class="heading-row"><h3>شش محور داوری</h3><span class="section-subtitle">برای مشاهده شاهد روی شناسه کلیک کنید</span></div>'+
      '<div class="rule-overview-grid">'+cs+'</div></div>'+
      '<section class="section-card"><div class="heading-row"><h3>پرونده کامل میوز</h3><span class="tag">متن پژوهشی، نه رأی نهایی</span></div>'+
      '<details><summary class="secondary" style="display:inline-block;cursor:pointer">نمایش گزارش پژوهشی این قاعده</summary><pre class="trace-pre">'+esc(rule.dossierMarkdown)+'</pre></details></section>'+
      '<div class="section-card"><div class="heading-row"><h3>پشتیبان‌گیری و انتقال</h3></div><p>نتیجه‌های شما در همین مرورگر ذخیره می‌شود. برای ارسال به ChatGPT فایل JSON را دریافت و در گفت‌وگو پیوست کنید؛ نسخه JSON قابل ورود مجدد به همین سایت است.</p>'+
      '<div class="pager"><button class="secondary" id="import-file" data-action="import">↑ واردکردن گزارش</button><button class="secondary" id="clear-local" data-action="reset">پاک‌کردن داده این مرورگر</button></div></div>'+
      '</section>';
  }
  function renderEvidence(rule) {
    const set=new Set();
    for(const part of Object.values(rule.components))for(const id of part.canonicalBackings||[])set.add(id);
    for(const id of rule.additionalBackings||[])set.add(id);
    const all=[...set];
    const visible=evidenceFocus?all.filter(x=>x===evidenceFocus):all;
    let cards=visible.map(id=>{
      const s=sourceById(id);
      if(!s)return '<div class="warning-inline">شناسه شاهد در داده‌های صفحه وجود ندارد: '+esc(id)+'</div>';
      const title=DATA.books.find(b=>b.id===s.book);
      return '<article class="source-card" id="source-'+esc(id)+'"><div class="source-top"><span class="source-ref">'+esc(id)+'</span><span class="tag warning">چاپ نامعلوم</span></div>'+
        '<div class="source-meta">'+esc(title?title.title:s.book)+' · رکورد '+esc(s.record)+' · صفحه دیتابیس '+esc(s.page)+' · '+esc(s.speaker)+'</div>'+
        '<blockquote class="arabic-quote" lang="ar">'+esc(s.quote)+'</blockquote>'+
        '<details class="context-box"><summary>نمایش سیاق قبل و بعدِ قطعه</summary><p>'+esc(s.before)+' <span class="context-word">'+esc(s.quote)+'</span> '+esc(s.after)+'</p></details>'+
        '<button type="button" class="copy-quote" data-action="copy-source" data-source="'+esc(id)+'">کپی شاهد و شناسه</button></article>';
    }).join('');
    return '<section class="tab-content"><div class="section-card"><div class="heading-row"><h3>متن و شناسه‌های مستند</h3><span class="tag">'+visible.length+' از '+all.length+' شاهد</span></div>'+
      '<p>نقل‌ها از رجیستر کانونی C4 آورده شده‌اند. شماره صفحه، صفحه دیتابیس است نه صفحه چاپی. متن‌های کوتاه برای مراجعه اولیه‌اند؛ داوری معتبر نیازمند مطالعه کل سیاق و نسخه مبنا است.</p>'+
      (evidenceFocus?'<button type="button" class="secondary" data-action="all-sources">نمایش تمام شواهد پرونده</button>':'')+
      '</div>'+cards+(visible.length===0?'<div class="section-card"><p>شاهد مرتبطی وجود ندارد.</p></div>':'')+'</section>';
  }
  function renderReview(rule,review,c) {
    const parts=PARTS.map(([key,label,desc],i)=>{
      const rec=review.parts[key],part=rule.components[key];
      const choices=CHOICES.map(([v,title])=>'<button type="button" class="choice'+(rec.decision===v?' selected '+(v==='reject'?'reject':v==='revise'?'revise':v==='defer'?'unknown':''):'')+
        '" data-action="part-decision" data-part="'+key+'" data-value="'+v+'" aria-pressed="'+String(rec.decision===v)+'">'+title+'</button>').join('');
      return '<article class="part-card'+(partValid(rec)?' part-filled':'')+'" id="part-'+key+'"><div class="part-heading"><h4>'+
        String(i+1).padStart(2,'0')+' · '+esc(label)+' <span class="part-eng">'+key+'</span></h4>'+badge(part.status)+'</div>'+
        '<p class="part-descr">'+esc(desc)+'</p><div class="part-sources"><span class="part-sources-label">شواهد:</span>'+
        refs(part.canonicalBackings)+(part.adverseRefs&&part.adverseRefs.length?'<span class="tag danger">مخالف: '+esc(part.adverseRefs.join('، '))+'</span>':'')+
        '</div><div class="decision-row" role="group" aria-label="نظر درباره '+esc(label)+'">'+choices+'</div>'+
        '<label class="field-label" for="reason-'+key+'">استدلال یا توضیح شما '+(rec.decision==='reject'||rec.decision==='revise'||rec.decision==='defer'?'(برای این تصمیم الزامی)':'(اختیاری)')+'</label>'+
        '<textarea id="reason-'+key+'" class="reason-input" data-kind="part-note" data-part="'+key+'" placeholder="نظر شما درباره نسبت عبارت شیخ با این جزء، قیود و اشکالات…">'+esc(rec.reason)+'</textarea></article>';
    }).join('');
    const finals=CHOICES.map(([v,title])=>'<button type="button" class="choice'+(review.decision===v?' selected '+(v==='reject'?'reject':v==='revise'?'revise':v==='defer'?'unknown':''):'')+
      '" data-action="final-decision" data-value="'+v+'" aria-pressed="'+String(review.decision===v)+'">'+title+'</button>').join('');
    return '<section class="tab-content"><div class="section-card review-intro"><span aria-hidden="true">✧</span><div>'+
      '<h3>داوری جزءبه‌جزء</h3><p>هر شش جزء را بررسی کنید. برای رد، اصلاح یا تعلیق هر جزء، توضیح مستدل لازم است. تصمیم کلی شما جایگزین ارزیابی اجزا نمی‌شود.</p></div></div>'+
      '<div class="part-list">'+parts+'</div>'+
      '<div class="final-card"><h3>تصمیم نهایی شما درباره این قاعده</h3><p>این یک تصمیم علمیِ شخصی در محیط پژوهش است. حتی «تأیید» موجب تغییر وضعیت تاریخی قاعده یا اجرای آن نمی‌شود.</p>'+
      '<div class="final-choices" role="group" aria-label="تصمیم نهایی">'+finals+'</div>'+
      '<label class="field-label" for="final-reason" style="margin-top:14px">دلیل اصلی تصمیم (الزامی؛ حداقل ۱۲ نویسه)</label>'+
      '<textarea id="final-reason" class="reason-input" data-kind="final-note" placeholder="جمع‌بندی استدلال شما، دامنه اعتبار، اشکالات باقی‌مانده و نسبت با نظر مختار شیخ…">'+esc(review.reason)+'</textarea>'+
      '<div class="submit-row"><span class="checklist-count" id="checklist-text">'+c.partsDone+' از ۶ جزء دارای رأی کامل</span>'+
      '<button type="button" class="primary" data-action="complete-rule">ثبت و تأیید ثبت نظر این پرونده</button></div>'+
      '<p id="review-error" class="error-note" role="alert"></p></div></section>';
  }
  function refresh() {
    renderNav();renderRule();
  }
  function goto(id, tab) {
    if(!byId(id))return;
    selected=id;activeTab=tab||'overview';evidenceFocus='';
    refresh();
    document.querySelector('.sidebar').classList.remove('open');
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function updatePart(part,value) {
    if(!PARTS.some(x=>x[0]===part))return;
    const rec=reviewFor(selected);
    rec.parts[part].decision=value;
    rec.submitted_at=null;rec.updated_at=iso();
    save();refresh();
  }
  function statusName(x) {return ({approve:'تأیید',reject:'رد',revise:'نیازمند اصلاح',defer:'تعلیق'})[x]||'ثبت‌نشده';}
  function validateRule(id) {
    const r=reviewFor(id);
    if(!draft.reviewer.trim())return 'ابتدا نام پژوهشگر را در بالای صفحه وارد کنید.';
    for(const [key,label] of PARTS){
      const p=r.parts[key];
      if(!p.decision)return 'هنوز درباره «'+label+'» نظری انتخاب نکرده‌اید.';
      if(!partValid(p))return 'برای رد/اصلاح/تعلیق «'+label+'»، دست‌کم ۸ نویسه دلیل ثبت کنید.';
    }
    if(!r.decision)return 'تصمیم کلی قاعده را انتخاب کنید.';
    if(r.reason.trim().length<12)return 'دلیل نهایی باید دست‌کم ۱۲ نویسه باشد.';
    return '';
  }
  function getExport() {
    return {
      review_schema:SCHEMA,source_sha:DATA.source_sha,
      book_commit:DATA.book_commit,
      exported_at:iso(),created_at:draft.created_at,
      reviewer:draft.reviewer,edition_note:draft.edition_note,
      reviewer_role:'PRIMARY_RESEARCHER_SELF_REVIEW_NOT_INDEPENDENT',
      research_qualification_effect:'NONE',
      historical_admissions:0,
      source_dataset_status:DATA.status,
      cases:DATA.rules.map(rule=>{
        const rev=reviewFor(rule.id);
        return {rule_key:rule.id,title:rule.title,grade_proposal:rule.grade,
          outcome:rev.decision,reason:rev.reason,
          complete:completion(rule.id).complete,
          parts:Object.fromEntries(PARTS.map(([part])=>[part,{
            outcome:rev.parts[part].decision,reason:rev.parts[part].reason,
            research_status:rule.components[part].status,
            canonical_source_refs:rule.components[part].canonicalBackings,
            adverse_refs:rule.components[part].adverseRefs}])),
          updated_at:rev.updated_at,submitted_at:rev.submitted_at};
      })
    };
  }
  function asMarkdown(data) {
    let arr=['# صورت‌جلسه داوری پژوهشگر اصلی — Feqh Muse','',
      '**داور:** '+(data.reviewer||'ثبت نشده'),
      '**نقش:** پژوهشگر اصلی، نه داور مستقل',
      '**چاپ بررسی‌شده:** '+(data.edition_note||'ثبت نشده'),
      '**تاریخ خروجی:** '+data.exported_at,
      '**مبنای داده:** '+data.source_sha,
      '**اثر بر اجرای تاریخی:** ندارد؛ تمام قواعد HOLD باقی می‌مانند.',''];
    for(const item of data.cases){
      arr.push('## '+item.title,'','شناسه: '+item.rule_key,
        '','**نتیجه کلی:** '+statusName(item.outcome),
        '','**استدلال کلی:** '+(item.reason||'ثبت نشده'),'');
      for(const [key,label] of PARTS){
        const p=item.parts[key];
        arr.push('### '+label+' ('+key+')','','- تصمیم: '+statusName(p.outcome),
          '- توضیح: '+(p.reason||'ثبت نشده'),
          '- شواهد کانونی: '+(p.canonical_source_refs.join('، ')||'ندارد'),
          '- شواهد مخالف: '+(p.adverse_refs.join('، ')||'ندارد'),'');
      }
    }
    return arr.join('\n');
  }
  function download(filename,text,type) {
    const b=new Blob([text],{type:type||'application/json;charset=utf-8'});
    const url=URL.createObjectURL(b);
    const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();
    a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);
  }
  function downloadJson() {download('feqh-muse-scholar-review-'+iso().slice(0,10)+'.json',JSON.stringify(getExport(),null,2));toast('گزارش JSON دریافت شد. فایل را در گفت‌وگو پیوست کنید.');}
  function downloadMd() {download('feqh-muse-scholar-review-'+iso().slice(0,10)+'.md',asMarkdown(getExport()),'text/markdown;charset=utf-8');toast('نسخه Markdown دریافت شد.');}
  async function share(){
    const content=JSON.stringify(getExport(),null,2);
    const file=new File([content],'feqh-muse-scholar-review.json',{type:'application/json'});
    if(navigator.share && navigator.canShare && navigator.canShare({files:[file]})){
      try{await navigator.share({files:[file],title:'گزارش داوری علمی Feqh Muse'});return;}
      catch(e){if(e.name==='AbortError')return;}
    }
    downloadJson();toast('اشتراک‌گذاری مستقیم در این دستگاه فعال نیست؛ فایل JSON دریافت شد.');
  }
  function requestImport() {$('import-input').click();}
  function importData(obj) {
    if(!obj || obj.review_schema!==SCHEMA || obj.source_sha!==DATA.source_sha ||
       !Array.isArray(obj.cases) || obj.cases.length!==DATA.rules.length)
      throw Error('این فایل با نسخه و ساختار داده سایت سازگار نیست.');
    const incoming=new Set(obj.cases.map(r=>r.rule_key));
    if(incoming.size!==DATA.rules.length || DATA.rules.some(r=>!incoming.has(r.id)))
      throw Error('شناسه پرونده‌های فایل با داده فعلی مطابقت ندارد.');
    draft=newDraft();
    draft.reviewer=String(obj.reviewer||'').slice(0,160);
    draft.edition_note=String(obj.edition_note||'').slice(0,350);
    for(const item of obj.cases){
      const rec=reviewFor(item.rule_key);
      rec.decision=validDecision(item.outcome);
      rec.reason=String(item.reason||'').slice(0,10000);
      for(const [key] of PARTS){
        const p=item.parts&&item.parts[key]?item.parts[key]:{};
        rec.parts[key]={decision:validDecision(p.outcome),reason:String(p.reason||'').slice(0,10000)};
      }
      rec.updated_at=iso();rec.submitted_at=null;
    }
    save();
    $('reviewer-name').value=draft.reviewer;$('edition-note').value=draft.edition_note;
    refresh();
  }
  function bind() {
    document.addEventListener('click', async e => {
      const hit=e.target.closest('[data-action]');
      if(hit){
        const action=hit.dataset.action;
        if(action==='navigate')return goto(hit.dataset.id);
        if(action==='tab'){activeTab=hit.dataset.tab;evidenceFocus='';renderRule();return;}
        if(action==='source'){activeTab='evidence';evidenceFocus=hit.dataset.source;renderRule();return;}
        if(action==='all-sources'){evidenceFocus='';renderRule();return;}
        if(action==='review-part'){activeTab='review';renderRule();document.getElementById('part-'+hit.dataset.part)?.scrollIntoView({behavior:'smooth',block:'start'});return;}
        if(action==='part-decision')return updatePart(hit.dataset.part,hit.dataset.value);
        if(action==='final-decision'){reviewFor(selected).decision=hit.dataset.value;reviewFor(selected).submitted_at=null;save();refresh();return;}
        if(action==='complete-rule'){
          const error=validateRule(selected);
          if(error){$('review-error').textContent=error;toast(error);return;}
          const r=reviewFor(selected);r.submitted_at=iso();r.updated_at=iso();save();refresh();toast('نظر شما درباره این قاعده تکمیل و در مرورگر ثبت شد.');return;
        }
        if(action==='copy-source'){
          const s=sourceById(hit.dataset.source);
          if(s){try{await navigator.clipboard.writeText(s.id+'\n'+s.quote+'\nرکورد: '+s.record+' / صفحه دیتابیس: '+s.page);toast('نقل و ارجاع کپی شد.');}catch(x){toast('مرورگر اجازه کپی خودکار نداد.');}}
          return;
        }
        if(action==='import')return requestImport();
        if(action==='reset'){if(confirm('تمام تصمیم‌های ذخیره‌شده در این مرورگر پاک شوند؟ ابتدا نسخه JSON دریافت کنید.')){localStorage.removeItem(STORAGE);draft=newDraft();$('reviewer-name').value='';$('edition-note').value='';refresh();toast('یادداشت‌های این مرورگر پاک شدند.');}return;}
      }
      if(e.target.closest('#export-header'))return $('export-dialog').showModal();
      if(e.target.closest('#close-dialog'))return $('export-dialog').close();
      if(e.target.closest('#download-json'))return downloadJson();
      if(e.target.closest('#download-md'))return downloadMd();
      if(e.target.closest('#share-review'))return share();
      if(e.target.closest('#copy-json')){
        try{await navigator.clipboard.writeText(JSON.stringify(getExport(),null,2));toast('گزارش در حافظه کپی شد.');}
        catch(x){toast('کپی مستقیم ممکن نشد؛ فایل JSON دریافت کنید.');}
        return;
      }
      if(e.target.closest('#mobile-menu'))return document.querySelector('.sidebar').classList.toggle('open');
      if(e.target.closest('#theme-toggle')){
        const light=document.documentElement.classList.toggle('light');
        localStorage.setItem('feqh-review-theme',light?'light':'dark');return;
      }
      if(e.target.classList.contains('filter')){
        filter=e.target.dataset.filter;
        document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===e.target));renderNav();return;
      }
      if(e.target===$('export-dialog'))$('export-dialog').close();
    });
    document.addEventListener('input',e=>{
      const el=e.target;
      if(el.id==='search-rule'){search=el.value.trim();renderNav();return;}
      if(el.id==='reviewer-name'||el.id==='edition-note'){
        draft[el.id==='reviewer-name'?'reviewer':'edition_note']=el.value;
        save();renderNav();return;
      }
      if(el.matches('textarea[data-kind]')){
        const r=reviewFor(selected);
        if(el.dataset.kind==='final-note')r.reason=el.value;
        else if(el.dataset.kind==='part-note' && PARTS.some(x=>x[0]===el.dataset.part))
          r.parts[el.dataset.part].reason=el.value;
        r.submitted_at=null;r.updated_at=iso();save();renderNav();
        const count=$('checklist-text');
        if(count)count.textContent=completion(selected).partsDone+' از ۶ جزء دارای رأی کامل';
      }
    });
    $('import-input').addEventListener('change',async e=>{
      const f=e.target.files&&e.target.files[0];
      e.target.value='';
      if(!f)return;
      if(f.size>2_000_000){toast('فایل بزرگ‌تر از حد مجاز است.');return;}
      try{importData(JSON.parse(await f.text()));toast('گزارش وارد شد؛ برای تکمیل هر پرونده دوباره بررسی کنید.');}
      catch(err){toast('ورود فایل ناموفق: '+err.message);}
    });
  }
  async function start(){
    bind();
    const theme=localStorage.getItem('feqh-review-theme');
    if(theme==='light')document.documentElement.classList.add('light');
    try{
      const response=await fetch('./data/review-data.json',{cache:'no-store'});
      if(!response.ok)throw Error('HTTP '+response.status);
      DATA=await response.json();
      if(!DATA||DATA.schema_version!=='feqh-scholar-review-portal-v1'||DATA.rules.length!==10||DATA.sources.length!==34)
        throw Error('داده‌های علمی با نسخه مورد انتظار سازگار نیستند.');
      restore();selected=DATA.rules[0].id;
      $('reviewer-name').value=draft.reviewer;$('edition-note').value=draft.edition_note;
      renderNav();renderRule();
    }catch(err){
      $('rule-view').innerHTML='<div class="section-card"><h3>بارگذاری داده پژوهشی ناموفق بود</h3><p>'+esc(err.message)+'</p><p>سایت را روی GitHub Pages یا یک سرور HTTP اجرا کنید. بازکردن مستقیم index.html با file:// ممکن است اجازه خواندن JSON را ندهد.</p></div>';
    }
  }
  document.addEventListener('DOMContentLoaded',start);
})();
