# Phase B — migration آزمایشی و Adapter محدود موتور

**وضعیت علمی:** فقط پژوهش و آزمون فنی. موفقیت اجرایی به معنای کشف مستقل حجیت یا بازسازی اجتهاد تاریخی نیست.

## مبنای معماری و کنترل شاخه‌ها

این شاخه از `architecture/issue-centric-multi-scholar-v1` @ `2d72aa113504f40d7cafd8114c95f75290978362` ساخته شده است. PR #2 خود بر پرونده ممیزی بیع عذره و سخت‌سازی PR #1 تکیه دارد. ادغام این PR قبل از تصویب و مرتب‌سازی وابستگی‌ها ممنوع است.

PostgreSQL 16+ پایگاه اصلی است. شِمای SQLite صرفاً مرجع قرارداد ساختار محسوب می‌شود و مقصد این انتقال نیست.

## محتوای واقعی import

- دو مسئله با شناسه‌های `khiyar.ghabn` و `sale.adhrah`، هرکدام با چند برچسب موضوعی.
- یک عالم واقعی (شیخ مرتضی انصاری) و شناسنامه آثار مکاسب، رسائل فقهیه و فرائدالاصول؛ برای فرائد، چاپ یا متن جدیدی بدون پشتوانه ایجاد نمی‌شود.
- قطعات *عین فایل‌های پیکره اولیه* در `ghabn-case/source_*.md` و `pilot/bay-udhrah/source_*.md`، همراه SHA-256 رشته و نشانی رکورد دیتابیس. **صفحه چاپی تأییدشده نداریم؛ `printed_page_label` عمداً خالی است.**
- کدگذاری مستقل A و B از غبن و U1 تا U12 بیع عذره، با ۱۲ جایگاه داده برای هر رخداد؛ جایگاه‌های استخراج‌نشده با برچسب صریح عدم احراز باقی می‌مانند. A و B دو گرانولاریتی از یک متن‌اند؛ جمع تعدادشان به معنای دو برابر بودن رخداد تاریخی نیست.
- یال‌های گراف بدون تحریف معنایی در جدول جدید `evidence_relations` با رابطه اصلی، شناسه دو گره، هش منشأ و ارزیابی `unverified` نگهداری می‌شوند. ارزیابی‌های ماشینی اولیه در `evidence_assessments` نیز هر چهار محور را `unverified` می‌گذارند.
- گره‌های گراف موجود به صورت `evidence_items` پژوهشی با `category=other` وارد می‌شوند؛ اعتبار مستقل، تعارض و ارزیابی حجیت از این انتقال حاصل نمی‌شود.
- گره‌های باز `IJ-SCOPE-BADHL`، `IJ-KHIYAR-SCOPE-BADHL` و `S-UDH-1..3` همچنان ادعاهای `unverified` هستند.
- قواعد از `rules_v4.json` و `rules_t3.json` به همراه مشخصه هسته قدیمی فقط با `execution_layer=hypothesis`، `scientific_grade=C` و `reviewer_status=pending` وارد می‌شوند. هیچ قاعده‌ای در این import به `historical` ارتقا نمی‌یابد.

## راه اجرای واقعی

از ریشه مخزن، روی پایگاه **آزمایشی خالی**:

```bash
export DATABASE_URL='postgresql://postgres:postgres@localhost:5432/feqh_phase_b'
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f architecture/migrations/001_issue_centric_multischolar.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f architecture/migrations/002_cross_scholar_integrity.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f architecture/migrations/003_phase_b_evidence_relations.sql
python -m pip install 'psycopg[binary]>=3.2,<4'
python -m phase_b.pilot
python -m phase_b.pilot  # آزمون عدم تکثیر
python -m unittest phase_b.test_phase_b -v
python -m phase_b.adapter --issue khiyar.ghabn --scholar murtada-ansari --profile ansari-development --scenario ghabn.t8.core.development
python -m phase_b.adapter --issue sale.adhrah --scholar murtada-ansari --profile ansari-development --scenario udhrah.documentary.no-rule
python engine2/run_test6.py
python engine2/run_test8.py
python engine2/run_mutations.py
```

## دامنه پاسخ Adapter

چهار شناسه `issue_id`, `scholar_id`, `methodology_profile_id`, `scenario_id` را می‌پذیرد (UUID یا کلید پایدار). اتصال مسئله، سناریو، عالم و نسخه پروفایل بررسی می‌شود. انتخاب Ruleset منجمد و هش فایل‌های قفل‌شده ضروری است.

- `safety_probe`: فقط مقدمات آشکار سناریوی توسعه اجرا می‌شوند؛ گزاره حاصل، پاسخ به سناریوی آزمایشی است، **نه فتوای تاریخی و نه حکم مستخرج از حجیت احراز‌شده**.
- `historical_reconstruction` و `hypothetical_experiment`: تا تأیید مستقل شش پشتوانه و دامنه قواعد، STOP.
- `sale.adhrah`: `STOP-OUT-OF-DOMAIN` بدون هیچ استنباط جعلی.
- مورد نامشخص به `False` تبدیل نمی‌شود. ادعاهای متعارض و ناقص برای بررسی نگهداری می‌شوند؛ Adapter حق ندارد `verified_evidence` را صرفاً از حالت `accepted` دیتابیس جعل کند.
- تابع `engine2.run_core` در نسخه فعلی ردّ تفصیلی درونی همه قواعد را منتشر نمی‌کند؛ خروجی تنها trace واقعی همان هسته و هش نسخه و مقدمات قابل ردیابی است، نه trace ساختگی.

## محدودیت‌های عمدی باقی‌مانده

۱. متن مکاسب و رساله از روی پیکره پروژه آمده و تطبیق با چاپ کاغذی هنوز نیازمند داوری انسانی است.

۲. جدول‌های `positions` و `human_reviews` بدون استناد داوری جدید پر نمی‌شوند؛ وجود عبارت یا گره تحلیلی برای ساخت موضع تاریخی کافی نیست.

۳. یال‌های `GRAPH_V2.json` و `GRAPH_UDHRAH_DOC.json` در جدول `evidence_relations` بدون تفسیر معنایی حفظ شده‌اند؛ تبدیل آنها به عملگرهای معتبر استدلال یا `reasoning_edges` نیازمند داوری مستقل است.

۴. Adapter خواندنی است؛ ابزار مستقل `python -m phase_b.record_run --issue khiyar.ghabn --scenario ghabn.t8.core.development` رد اجرای واقعی را در `engine_runs.raw_output`، همراه هش ورودی/خروجی و توقف‌های صریح در `run_steps` ثبت می‌کند. ثبت تفصیلی قواعد درونی موتور legacy بدون شواهد ممکن نیست. حاکمیت دسترسی و امضای غیرقابل‌دستکاری برای محیط عملیاتی هنوز توسعه نیافته است.

۵. استقلال علمی آزمون‌ها از موفقیت PostgreSQL و قفل آزمون‌های ۶ و ۸ حاصل نمی‌شود. گره‌های نسیان، بذل و تعارض مکاسب/فرائد باز هستند.

## فاز بعد

ابتدا شواهد شش‌گانه تک‌تک قواعد عمومی از مکاسب/فرائد/رسائل جمع‌آوری و مستقل داوری شوند؛ سپس یک `historical` Ruleset قابل ارزیابی و یک مسیر append-only حسابرسی اجرا طراحی شود. پس از اثبات پوشش روی مسائل مستقل، عالم دوم واقعی با منابع مستند و بدون اشتراک ناخواسته مبانی اضافه گردد.
